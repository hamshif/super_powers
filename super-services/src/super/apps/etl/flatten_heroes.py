
import os
import sys
import pyspark.sql.functions as F
from pyspark.sql import SparkSession
from pyspark.sql.types import StringType

from super.core import utils
from super.core.runtime import bootstrap_spark_env

def main():
    # 0. Bootstrap Spark
    bootstrap_spark_env()

    # 1. Config
    conf = utils.get_app_conf("generate_powers")
    stage_root = conf.get_string("stage_root")
    warehouse_root = os.path.join(stage_root, "warehouse")
    
    print(f"Hero ETL Starting. Reading from: {stage_root}")
    
    spark = (SparkSession.builder
             .appName("SuperPowers-ETL-Heroes")
             .config("spark.driver.memory", "4g")
             .getOrCreate())

    # --- PART 1: HERO PROFILES ---
    profiles_path = os.path.join(stage_root, "hero_profiles")
    if os.path.exists(profiles_path):
        print(f"Reading Profiles from: {profiles_path}")
        profiles_df = (spark.read
                       .option("multiline", "true")
                       .option("recursiveFileLookup", "true")
                       .option("pathGlobFilter", "*.json")
                       .json(profiles_path))
        
        # 1. hero_profiles.parquet
        print("Building 'hero_profiles' table...")
        t_profiles = profiles_df.select(
            F.col("hero_name"),
            F.col("ontology"),
            F.col("primary_seed_name").alias("primary_seed"),
            F.col("bio"),
            F.col("estimated_connectivity")
        )
        t_profiles.write.mode("overwrite").parquet(os.path.join(warehouse_root, "hero_profiles"))
        
        # 2. hero_profile_seeds.parquet
        print("Building 'hero_profile_seeds' table...")
        # Explicitly select primary as a row too? 
        # Plan said "Exploded seeds". Let's verify if primary is in secondary list. Usually not.
        
        p_primary = profiles_df.select(
            F.col("hero_name"),
            F.col("primary_seed_name").alias("seed_name"),
            F.lit("primary").alias("role")
        )
        
        p_secondary = profiles_df.select(
            F.col("hero_name"),
            F.explode("secondary_seed_names").alias("seed_name"),
            F.lit("secondary").alias("role")
        )
        
        t_profile_seeds = p_primary.unionByName(p_secondary)
        t_profile_seeds.write.mode("overwrite").parquet(os.path.join(warehouse_root, "hero_profile_seeds"))
        
        # 3. hero_profile_side_effects.parquet
        print("Building 'hero_profile_side_effects' table...")
        t_profile_effects = profiles_df.select(
            F.col("hero_name"),
            F.explode("side_effect_names").alias("side_effect_name")
        )
        t_profile_effects.write.mode("overwrite").parquet(os.path.join(warehouse_root, "hero_profile_side_effects"))
        
    else:
        print("No hero_profiles directory found. Skipping.")

    # --- PART 2: HERO GENOMES ---
    genomes_path = os.path.join(stage_root, "hero_genomes")
    if os.path.exists(genomes_path):
        print(f"Reading Genome from: {genomes_path}")
        genomes_df = (spark.read
                      .option("multiline", "true")
                      .option("recursiveFileLookup", "true")
                      .option("pathGlobFilter", "*.json")
                      .json(genomes_path))
                      
        # 4. hero_genes.parquet
        print("Building 'hero_genes' table...")
        # Ensure hero_name exists (it should now)
        t_hero_genes = genomes_df.select(
            F.col("gene_id"),
            F.col("hero_name"),
            F.col("ontology"),
            F.col("mutation_class"),
            F.col("gene_role"),
            F.col("stability_index"),
            F.col("confidence").cast("float"),
            F.col("failure_mode")
        )
        t_hero_genes.write.mode("overwrite").parquet(os.path.join(warehouse_root, "hero_genes"))
        
        # 5. hero_gene_regulation.parquet
        print("Building 'hero_gene_regulation' table...")
        t_hero_reg = genomes_df.select(
            F.col("gene_id").alias("source_gene_id"),
            F.col("hero_name"),
            F.explode("regulated_genes").alias("reg")
        ).select(
            F.col("source_gene_id"),
            F.col("hero_name"), # Denormalization useful for partitioning/querying
            F.col("reg.gene_id").alias("target_gene_id"),
            F.col("reg.effect").alias("effect"),
            F.col("reg.strength").alias("strength").cast("float")
        )
        t_hero_reg.write.mode("overwrite").parquet(os.path.join(warehouse_root, "hero_gene_regulation"))
        
        # 6. hero_gene_seeds.parquet
        print("Building 'hero_gene_seeds' table...")
        g_primary = genomes_df.select(
            F.col("gene_id"),
            F.col("hero_name"),
            F.explode("primary_seeds").alias("seed_obj")
        ).select(
            F.col("gene_id"),
            F.col("hero_name"),
            F.col("seed_obj.seed").alias("seed_name"),
            F.lit("primary").alias("role"),
            F.col("seed_obj.weight").alias("weight").cast("float")
        )
        
        g_secondary = genomes_df.select(
            F.col("gene_id"),
            F.col("hero_name"),
            F.explode_outer("secondary_seeds").alias("seed_obj")
        ).where(F.col("seed_obj").isNotNull()).select(
            F.col("gene_id"),
            F.col("hero_name"),
            F.col("seed_obj.seed").alias("seed_name"),
            F.lit("secondary").alias("role"),
            F.col("seed_obj.weight").alias("weight").cast("float")
        )
        
        t_hero_gene_seeds = g_primary.unionByName(g_secondary)
        t_hero_gene_seeds.write.mode("overwrite").parquet(os.path.join(warehouse_root, "hero_gene_seeds"))

    else:
        print("No hero_genomes directory found. Skipping.")

    print("Hero ETL Complete.")
    spark.stop()

if __name__ == "__main__":
    main()
