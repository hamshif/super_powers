
import os
import sys
import pyspark.sql.functions as F
from pyspark.sql import SparkSession
from pyspark.sql.types import StringType

# Add source to path for local execution compatibility
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from super.core import utils
from super.core.runtime import bootstrap_spark_env

def main():
    # 0. Bootstrap Spark Env (Java / Spark Home)
    bootstrap_spark_env()

    # 1. Configuration & Session
    conf = utils.get_app_conf("generate_powers")
    stage_root = conf.get_string("stage_root")
    warehouse_root = os.path.join(stage_root, "warehouse")
    
    print(f"ETL Starting. Reading from: {stage_root}")
    print(f"Writing Warehouse to: {warehouse_root}")
    
    spark = (SparkSession.builder
             .appName("SuperPowers-ETL-Flatten")
             .config("spark.driver.memory", "4g")
             .getOrCreate())

    # --- PART 1: GENOME (Genes) ---
    genes_path = os.path.join(stage_root, "generated_genome")
    print(f"Reading Genes from: {genes_path}")
    
    # Load raw JSON using recursive lookup to handle empty dirs gracefully
    genes_df = (spark.read
                .option("multiline", "true")
                .option("recursiveFileLookup", "true")
                .option("pathGlobFilter", "*.json")
                .json(genes_path))
    
    # 1. genes.parquet
    print("Building 'genes' table...")
    t_genes = genes_df.select(
        F.col("gene_id"),
        F.col("mutation_class"),
        F.col("gene_role"),
        F.col("stability_index"),
        F.col("confidence").cast("float"),
        F.col("failure_mode")
    )
    t_genes.write.mode("overwrite").parquet(os.path.join(warehouse_root, "genes"))
    
    # 2. gene_seeds.parquet
    print("Building 'gene_seeds' table...")
    # Explode Primary
    primary = genes_df.select(
        F.col("gene_id"),
        F.explode("primary_seeds").alias("seed_obj")
    ).select(
        F.col("gene_id"),
        F.col("seed_obj.seed").alias("seed_name"),
        F.lit("primary").alias("role"),
        F.col("seed_obj.weight").alias("weight").cast("float")
    )
    
    # Explode Secondary (if any)
    # Schema check shows secondary_seeds is struct {seed, weight} like primary
    secondary = genes_df.select(
        F.col("gene_id"),
        F.explode_outer("secondary_seeds").alias("seed_obj")
    ).where(F.col("seed_obj").isNotNull()).select(
        F.col("gene_id"),
        F.col("seed_obj.seed").alias("seed_name"),
        F.lit("secondary").alias("role"),
        F.col("seed_obj.weight").alias("weight").cast("float")
    )
    
    t_gene_seeds = primary.unionByName(secondary)
    t_gene_seeds.write.mode("overwrite").parquet(os.path.join(warehouse_root, "gene_seeds"))

    # 3. gene_side_effects.parquet
    print("Building 'gene_side_effects' table...")
    t_side_effects = genes_df.select(
        F.col("gene_id"),
        F.explode("side_effect_profile").alias("se")
    ).select(
        F.col("gene_id"),
        F.col("se.side_effect").alias("side_effect_name"),
        F.col("se.probability").alias("probability").cast("float"),
        F.col("se.severity").alias("severity").cast("int"),
        F.col("se.trigger_condition").alias("trigger_condition")
    )
    t_side_effects.write.mode("overwrite").parquet(os.path.join(warehouse_root, "gene_side_effects"))
    
    # 4. gene_regulation.parquet
    print("Building 'gene_regulation' table...")
    t_regulation = genes_df.select(
        F.col("gene_id").alias("source_gene_id"),
        F.explode("regulated_genes").alias("reg")
    ).select(
        F.col("source_gene_id"),
        F.col("reg.gene_id").alias("target_gene_id"),
        F.col("reg.effect").alias("effect"),
        F.col("reg.strength").alias("strength").cast("float")
    )
    t_regulation.write.mode("overwrite").parquet(os.path.join(warehouse_root, "gene_regulation"))


    # --- PART 2: POWERS (ExpansionResult) ---
    powers_path = os.path.join(stage_root, "generated_powers")
    print(f"Reading Powers from: {powers_path}")
    
    powers_raw_df = (spark.read
                     .option("multiline", "true")
                     .option("recursiveFileLookup", "true")
                     .option("pathGlobFilter", "*.json")
                     .json(powers_path))
    # Schema: seed_name, gradient: List[GradientVariant]
    
    # Flatten array to get one row per variant
    exploded_powers = powers_raw_df.select(
        F.col("seed_name").alias("primary_seed"),
        F.explode("gradient").alias("variant")
    )
    
    # Generate ID: Hash(PrimarySeed + VariantName)
    # We use PrimarySeed to namespace it, avoiding collisions if "Flight" appears in multiple contexts (unlikely but safe)
    exploded_powers = exploded_powers.withColumn(
        "power_id", 
        F.sha2(F.concat(F.col("primary_seed"), F.lit("::"), F.col("variant.name")), 256).substr(1, 12)
    )

    # 5. powers.parquet
    print("Building 'powers' table...")
    t_powers = exploded_powers.select(
        F.col("power_id"),
        F.col("variant.name").alias("power_name"),
        F.col("variant.description").alias("description")
    )
    t_powers.write.mode("overwrite").parquet(os.path.join(warehouse_root, "powers"))
    
    # 6. power_seeds.parquet
    print("Building 'power_seeds' table...")
    
    # Primary Link (Seed owning the file)
    p_primary_seeds = exploded_powers.select(
        F.col("power_id"),
        F.col("primary_seed").alias("seed_name"),
        F.lit("primary").alias("role")
    )
    
    # Secondary Link (Mixed seeds in the variant)
    # mixed_seeds is List[MixedSeed] -> Struct {name, influence}
    p_secondary_seeds = exploded_powers.select(
        F.col("power_id"),
        F.explode_outer("variant.mixed_seeds").alias("seed_obj")
    ).where(F.col("seed_obj").isNotNull()).select(
        F.col("power_id"),
        F.col("seed_obj.name").alias("seed_name"),
        F.lit("secondary").alias("role")
    )
    
    t_power_seeds = p_primary_seeds.unionByName(p_secondary_seeds)
    t_power_seeds.write.mode("overwrite").parquet(os.path.join(warehouse_root, "power_seeds"))

    print("ETL Complete.")
    spark.stop()

if __name__ == "__main__":
    main()
