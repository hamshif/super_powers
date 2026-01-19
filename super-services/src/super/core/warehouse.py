
import os
import pandas as pd
# Lazy import pyspark inside function to avoid heavy import at top level?
# No, standard practice is top level, but let's guard it if we want pure Pandas usage?
# For now, just import it. The env has spark.
import pyspark.sql.functions as F

def get_hero_genome_summary(spark, warehouse_root):
    """
    Generates a unified view of Hero Profiles joined with their Master Regulator Gene
    and a summary of their Regulation Cluster.
    
    Returns a DataFrame with [hero_name, ontology, bio, master_regulator_id, mutation_class, cluster_size, cluster_network_summary]
    """
    # Load Tables
    hero_profiles = spark.read.parquet(os.path.join(warehouse_root, "hero_profiles"))
    # Use recursive lookup for robustness, though direct read usually works for flattened parquet
    hero_genes = spark.read.parquet(os.path.join(warehouse_root, "hero_genes"))
    hero_reg = spark.read.parquet(os.path.join(warehouse_root, "hero_gene_regulation"))

    # 1. Aggregate Cluster: Create a summary string of regulated genes
    # Format: "GeneID(Effect:Strength)"
    reg_summary = hero_reg.withColumn(
        "link_desc", 
        F.format_string("%s(%s:%.2f)", F.col("target_gene_id"), F.col("effect"), F.col("strength"))
    ).groupBy("hero_name").agg(
        F.count("target_gene_id").alias("cluster_size"),
        F.concat_ws(", ", F.collect_list("link_desc")).alias("cluster_network_summary")
    )

    # 2. Join Everything
    # Alias to prevent ambiguity (e.g. 'ontology' in multiple tables)
    p = hero_profiles.alias("p")
    g = hero_genes.alias("g")
    r = reg_summary.alias("r")

    full_report = p.join(g, "hero_name", "left") \
        .join(r, "hero_name", "left") \
        .select(
            F.col("p.hero_name"),
            F.col("p.ontology"),
            F.col("p.bio"),
            F.col("g.gene_id").alias("master_regulator_id"),
            F.col("g.mutation_class"),
            F.col("r.cluster_size"),
            F.col("r.cluster_network_summary")
        )
    
    return full_report

def get_hero_data(hero_name, ontology=None, warehouse_root=None):
    """
    Retrieves full hero profile and genome data using Pandas for low-latency access.
    Leverages partitions if 'ontology' is provided.
    
    Args:
        hero_name (str): Name of the hero (e.g., "Bugs Bunny")
        ontology (str, optional): Ontology partition to optimize read (e.g., "looney_tunes")
        warehouse_root (str): Path to warehouse directory.
        
    Returns:
        dict: Fully enriched hero object or None if not found.
    """
    if not warehouse_root:
        # Fallback to default relative location (assuming running from source root)
        # In prod, this should be passed explicitly.
        # This is compatible with local dev structure.
        warehouse_root = os.path.abspath(os.path.join(os.getcwd(), "../../data/warehouse"))

    # Define filtering strategy (Partition Pruning)
    # If ontology is known, we only read that partition.
    filters = []
    if ontology:
        filters.append(('ontology', '=', ontology))
    
    # Pass None if no filters, otherwise PyArrow complains "Malformed filters"
    filters = filters if filters else None

    # 1. Load Profile
    # Profiles are partitioned by ontology
    try:
        profiles_df = pd.read_parquet(
            os.path.join(warehouse_root, "hero_profiles"), 
            filters=filters,
            engine='pyarrow'
        )
    except FileNotFoundError:
        print(f"Warehouse not found at {warehouse_root}")
        return None

    # Filter by name in memory (small partition)
    hero_profile = profiles_df[profiles_df['hero_name'] == hero_name]
    
    if hero_profile.empty:
        return None
        
    # Extract scalar profile data
    profile_data = hero_profile.iloc[0].to_dict()
    
    # 2. Load Master Gene
    # Genes are partitioned by ontology
    genes_df = pd.read_parquet(
        os.path.join(warehouse_root, "hero_genes"),
        filters=filters,
        engine='pyarrow'
    )
    hero_gene = genes_df[genes_df['hero_name'] == hero_name]
    
    if not hero_gene.empty:
        master_gene_data = hero_gene.iloc[0].to_dict()
        profile_data['master_gene'] = master_gene_data
    else:
        profile_data['master_gene'] = None

    # 3. Load Regulation Cluster
    # Regulation IS now partitioned by ontology (after ETL update)
    reg_df = pd.read_parquet(
        os.path.join(warehouse_root, "hero_gene_regulation"),
        filters=filters,
        engine='pyarrow'
    )
    hero_cluster = reg_df[reg_df['hero_name'] == hero_name]
    
    # Enriched Cluster Summary
    # List of {target, effect, strength}
    if not hero_cluster.empty:
        cluster_list = hero_cluster[['target_gene_id', 'effect', 'strength']].to_dict('records')
        profile_data['genome_cluster'] = cluster_list
        profile_data['cluster_size'] = len(cluster_list)
    else:
        profile_data['genome_cluster'] = []
        profile_data['cluster_size'] = 0

    return profile_data

def get_all_heroes_data(warehouse_root=None, ontology=None):
    """
    Retrieves a unified Pandas DataFrame for multiple heroes.
    Supports filtering by ontology.
    
    Args:
        warehouse_root (str): Path to warehouse directory.
        ontology (str, optional): Specific ontology to filter by.
        
    Returns:
        pd.DataFrame: DataFrame containing unified hero view.
    """
    if not warehouse_root:
        warehouse_root = os.path.abspath(os.path.join(os.getcwd(), "../../data/warehouse"))
        
    filters = []
    if ontology:
        filters.append(('ontology', '=', ontology))
    filters = filters if filters else None
        
    try:
        # 1. Load Profiles
        profiles_df = pd.read_parquet(
            os.path.join(warehouse_root, "hero_profiles"),
            filters=filters,
            engine='pyarrow'
        )
        
        # 2. Load Genes
        genes_df = pd.read_parquet(
            os.path.join(warehouse_root, "hero_genes"),
            filters=filters,
            engine='pyarrow'
        )
        
        # 3. Load Regulation
        reg_df = pd.read_parquet(
            os.path.join(warehouse_root, "hero_gene_regulation"),
            filters=filters,
            engine='pyarrow'
        )
    except FileNotFoundError:
        print(f"Warehouse data missing in {warehouse_root}")
        return pd.DataFrame()

    # Aggregate Regulation Cluster
    # Format: "GENE(effect:strength)" same as Spark version
    reg_df['link_desc'] = reg_df.apply(
        lambda x: f"{x['target_gene_id']}({x['effect']}:{x['strength']:.2f})", axis=1
    )
    
    cluster_summary = reg_df.groupby('hero_name').agg(
        cluster_size=('target_gene_id', 'count'),
        cluster_network_summary=('link_desc', lambda x: ', '.join(x))
    ).reset_index()

    # Join everything
    # Profile Left Join Genes Left Join Cluster
    merged = pd.merge(profiles_df, genes_df, on=["hero_name", "ontology"], how="left", suffixes=('', '_gene'))
    merged = pd.merge(merged, cluster_summary, on="hero_name", how="left")
    
    # Fill NaN values for heroes without clusters
    merged['cluster_size'] = merged['cluster_size'].fillna(0).astype(int)
    merged['cluster_network_summary'] = merged['cluster_network_summary'].fillna("")
    
    # Rename columns to match the Unified View format
    # Genes might overwrite profile columns if names collide, but we partitioned by ontology so it's a join key.
    # gene_id -> master_regulator_id
    if 'gene_id' in merged.columns:
        merged = merged.rename(columns={'gene_id': 'master_regulator_id'})
        
    # Select final columns
    cols = [
        'hero_name', 'ontology', 'bio', 'master_regulator_id', 
        'mutation_class', 'cluster_size', 'cluster_network_summary'
    ]
    # Ensure cols exist given left joins
    final_cols = [c for c in cols if c in merged.columns]
    
    return merged[final_cols]
