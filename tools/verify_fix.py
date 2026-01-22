import os
import sys

# Ensure super-services/src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../super-services/src")))

from pyspark.sql import SparkSession
from super.core import utils
from super.core.runtime import bootstrap_spark_env
from super.core.warehouse import get_hero_genome_summary

def main():
    bootstrap_spark_env()
    conf = utils.get_app_conf("generate_powers")
    stage_root = conf.get_string("stage_root")
    warehouse_root = os.path.join(stage_root, "warehouse")
    
    print(f"Verifying warehouse at: {warehouse_root}")
    
    spark = (SparkSession.builder
             .appName("Verification")
             .config("spark.driver.memory", "4g")
             .getOrCreate())
             
    try:
        # Try running the function that failed
        df = get_hero_genome_summary(spark, warehouse_root)
        print("Successfully created DataFrame")
        
        # Force a read of the confidence column by collecting a few rows
        # The error happened during task execution (action)
        df.show(5)
        print("VERIFICATION SUCCESS: Spark read the data without error.")
        
    except Exception as e:
        print(f"VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
