
import os
import pyspark.sql.functions as F
from pyspark.sql import SparkSession
from super.core import utils
from super.core.runtime import bootstrap_spark_env

bootstrap_spark_env()
spark = SparkSession.builder.appName("JoinCheck").getOrCreate()
conf = utils.get_app_conf("generate_powers")
warehouse_root = os.path.join(conf.get_string("stage_root"), "warehouse")

hero_profiles = spark.read.parquet(os.path.join(warehouse_root, "hero_profiles"))
hero_genes = spark.read.parquet(os.path.join(warehouse_root, "hero_genes"))
reg = spark.read.parquet(os.path.join(warehouse_root, "hero_gene_regulation"))

network_size = reg.groupBy("hero_name").count().withColumnRenamed("count", "network_size")

p = hero_profiles.alias("p")
g = hero_genes.alias("g")
n = network_size.alias("n")

full_view = p.join(g, "hero_name", "left") \
    .join(n, "hero_name", "left") \
    .select(
        F.col("hero_name"), 
        F.col("p.ontology"),
        F.col("p.primary_seed"), 
        F.col("g.gene_id"), 
        F.col("g.mutation_class"),
        F.col("n.network_size"),
        F.col("g.confidence")
    )

print("Join successful. Sample:")
full_view.show(5)
