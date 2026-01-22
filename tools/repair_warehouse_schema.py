import os
import sys
import pandas as pd
from pathlib import Path
import logging

# Ensure super-services/src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../super-services/src")))

from super.core import utils
from super.core.warehouse_schema import load_schema, enforce_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("warehouse_repair")

def repair_warehouse():
    conf = utils.get_app_conf("generate_powers")
    stage_root = Path(conf.get_string("stage_root"))
    warehouse_root = stage_root / "warehouse"
    
    tables = conf.get_list("generate_powers.warehouse_tables")
    
    for table in tables:
        logger.info(f"Checking table: {table}")
        table_path = warehouse_root / table
        if not table_path.exists():
            continue
            
        schema = load_schema(str(warehouse_root), table)
        if not schema:
            logger.warning(f"No schema found for {table}, skipping.")
            continue
            
        # Recursive glob for all parquet files
        # Includes partitioned folders
        for parquet_file in table_path.glob("**/*.parquet"):
            if parquet_file.name.startswith("."): continue
            
            try:
                # Read
                df = pd.read_parquet(parquet_file)
                if df.empty: continue
                
                # Check types (naive check or just enforce)
                # Enforce is cheap enough for small data
                new_df = enforce_schema(df, schema)
                
                # Check if changes happened? (Optimization: compare dtypes)
                # For now, just rewrite to be safe.
                
                # Write back
                new_df.to_parquet(parquet_file, engine="pyarrow", index=False)
                logger.info(f"Fixed/Verified {parquet_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to process {parquet_file}: {e}")

if __name__ == "__main__":
    repair_warehouse()
