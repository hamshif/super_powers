import os
import json
import logging
import pandas as pd
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

def load_schema(warehouse_root: str, table_name: str) -> dict:
    """
    Loads the Spark schema (JSON) for a given table.
    """
    schema_path = os.path.join(warehouse_root, "_schemas", f"{table_name}.json")
    if not os.path.exists(schema_path):
        logger.warning(f"Schema not found for {table_name} at {schema_path}")
        return None
        
    with open(schema_path, "r") as f:
        return json.load(f)

def enforce_schema(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """
    Casts DataFrame columns to match the Spark schema.
    Only handles primitive types relevant to this issue (Float, Integer, String).
    """
    if not schema or 'fields' not in schema:
        return df
        
    out_df = df.copy()
    
    for field in schema['fields']:
        col_name = field['name']
        spark_type = field['type']
        
        # Skip if column not in DF (Pandas usually handles missing cols by not writing them, 
        # or we might want to fill NaNs if stricter)
        if col_name not in out_df.columns:
            continue
            
        # Map Spark Types to Pandas/Numpy
        try:
            if spark_type == 'float':
                out_df[col_name] = out_df[col_name].astype('float32')
            elif spark_type == 'double':
                out_df[col_name] = out_df[col_name].astype('float64')
            elif spark_type == 'integer':
                out_df[col_name] = out_df[col_name].astype('int32')
            elif spark_type == 'long':
                out_df[col_name] = out_df[col_name].astype('int64')
            elif spark_type == 'string':
                out_df[col_name] = out_df[col_name].astype('object') # or 'string' in newer pandas
            elif spark_type == 'boolean':
                out_df[col_name] = out_df[col_name].astype('bool')
        except Exception as e:
            logger.warning(f"Failed to cast column {col_name} to {spark_type}: {e}")
            
    return out_df
