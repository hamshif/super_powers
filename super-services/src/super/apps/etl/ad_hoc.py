
import os
import json
import uuid
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
import logging

from super.core import utils
from super.apps.generate_powers.models_hero import HeroProfile

logger = logging.getLogger(__name__)

def etl_single_hero(hero_name: str, ontology: str = "generated") -> None:
    """
    Performs a lightweight, ad-hoc ETL for a single newly created hero.
    Reads the specific JSON artifacts for the hero and appends them to the 
    Parquet warehouse using Pandas, avoiding full Spark job overhead.
    
    Args:
        hero_name: The name of the hero.
        ontology: The ontology (partition) the hero belongs to.
    """
    conf = utils.get_app_conf("generate_powers")
    stage_root = Path(conf.get_string("stage_root"))
    warehouse_root = stage_root / "warehouse"
    
    logger.info(f"Starting Ad-Hoc ETL for {hero_name} ({ontology})")
    
    # 1. Load Hero Profile
    # Path: stage/hero_profiles/{ontology}/{hero_name}.json
    # Note: Filename might be sanitized? super_power_sage/tools.py line 258:
    # profile_dir = stage_root / "hero_profiles" / ontology_dir
    # filename = f"{hero_name.replace(' ', '_').lower()}.json"
    
    safe_name = hero_name.replace(" ", "_").lower()
    profile_path = stage_root / "hero_profiles" / ontology / f"{safe_name}.json"
    
    if not profile_path.exists():
        raise FileNotFoundError(f"Hero profile not found: {profile_path}")
        
    with open(profile_path, "r") as f:
        profile_data = json.load(f)
        
    # Validation/Parsing (optional but good for consistency)
    # We treat it as dict for flexibility in ETL
    
    # --- PART 1: HERO PROFILES ---
    _etl_profiles(profile_data, warehouse_root, ontology)
    
    # --- PART 2: HERO GENOMES ---
    # Gene files are in stage/hero_genomes/{ontology}/
    # They are named like {safe_name}.json, {safe_name}_1.json, etc.
    genome_dir = stage_root / "hero_genomes" / ontology
    
    import time
    
    gene_files = []
    # Identify all files for this hero
    # Pattern: safe_name.json OR safe_name_N.json
    # Retry Loop for Eventual Consistency (Docker volumes/IO lag)
    max_retries = 5
    for attempt in range(max_retries):
        if genome_dir.exists():
            for f in genome_dir.iterdir():
                if f.name == f"{safe_name}.json" or f.name.startswith(f"{safe_name}_"):
                    gene_files.append(f)
        
        if gene_files:
            break
            
        if attempt < max_retries - 1:
            logger.info(f"Waiting for gene files for {hero_name} (Attempt {attempt+1}/{max_retries})...")
            time.sleep(0.5)
                
    if gene_files:
        logger.info(f"Found {len(gene_files)} gene files for {hero_name}")
        _etl_genomes(gene_files, hero_name, warehouse_root, ontology)
    else:
        logger.warning(f"No gene files found for {hero_name} in {genome_dir}")

    logger.info(f"Ad-Hoc ETL Complete for {hero_name}")


def _etl_profiles(data: Dict, warehouse_root: Path, ontology: str):
    """Process and write Profile-related tables."""
    hero_name = data.get("hero_name")
    
    # 1. hero_profiles
    df_profile = pd.DataFrame([{
        "hero_name": hero_name,
        "ontology": ontology,
        "primary_seed": data.get("primary_seed_name"),
        "bio": data.get("bio"),
        "estimated_connectivity": data.get("estimated_connectivity")
    }])
    _append_to_partition(df_profile, warehouse_root / "hero_profiles", ontology)
    
    # 2. hero_profile_seeds
    seeds = []
    if "primary_seed_name" in data:
        seeds.append({"hero_name": hero_name, "seed_name": data["primary_seed_name"], "role": "primary"})
    for s in data.get("secondary_seed_names", []):
        seeds.append({"hero_name": hero_name, "seed_name": s, "role": "secondary"})
        
    if seeds:
        df_seeds = pd.DataFrame(seeds)
        _append_to_partition(df_seeds, warehouse_root / "hero_profile_seeds", ontology=None) # Not partitioned by default in Spark script?
        # Check logic: flatten_heroes.py: t_profile_seeds.write.mode("overwrite").parquet(...)
        # It is NOT partitioned by ontology in flatten_heroes.py. It's global.
        # But we should check if we want it partitioned. It's safer to just append to root parquet.
        # WAIT: Spark default write without partitionBy creates a single folder.
        # We need to append carefully.
        _append_to_root(df_seeds, warehouse_root / "hero_profile_seeds")

    # 3. hero_profile_side_effects
    effects = []
    for e in data.get("side_effect_names", []):
        effects.append({"hero_name": hero_name, "side_effect_name": e})
        
    if effects:
        df_effects = pd.DataFrame(effects)
        _append_to_root(df_effects, warehouse_root / "hero_profile_side_effects")


def _etl_genomes(files: List[Path], hero_name: str, warehouse_root: Path, ontology: str):
    """Process and write Genome-related tables."""
    genes_data = []
    for f in files:
        with open(f, "r") as fh:
            genes_data.append(json.load(fh))
            
    # 4. hero_genes
    genes_rows = []
    reg_rows = []
    seed_rows = []
    
    for g in genes_data:
        # Base Gene
        genes_rows.append({
            "gene_id": g.get("gene_id"),
            "hero_name": hero_name,
            "ontology": ontology,
            "mutation_class": g.get("mutation_class"),
            "gene_role": g.get("gene_role"),
            "stability_index": g.get("stability_index"),
            "confidence": float(g.get("confidence", 0.0)),
            "failure_mode": g.get("failure_mode")
        })
        
        # Regulation
        source_id = g.get("gene_id")
        for reg in g.get("regulated_genes", []):
            reg_rows.append({
                "source_gene_id": source_id,
                "hero_name": hero_name,
                "ontology": ontology,
                "target_gene_id": reg.get("gene_id"),
                "effect": reg.get("effect"),
                "strength": float(reg.get("strength", 0.0))
            })
            
        # Seeds (Primary & Secondary)
        for ps in g.get("primary_seeds", []):
            seed_rows.append({
                "gene_id": source_id,
                "hero_name": hero_name,
                "seed_name": ps.get("seed"),
                "role": "primary",
                "weight": float(ps.get("weight", 0.0))
            })
        for ss in g.get("secondary_seeds", []):
            seed_rows.append({
                "gene_id": source_id,
                "hero_name": hero_name,
                "seed_name": ss.get("seed"),
                "role": "secondary",
                "weight": float(ss.get("weight", 0.0))
            })

    # Write Tables
    if genes_rows:
        df_genes = pd.DataFrame(genes_rows)
        # Enforce Schema
        from super.core.warehouse_schema import load_schema, enforce_schema
        schema = load_schema(str(warehouse_root), "hero_genes")
        if schema:
            df_genes = enforce_schema(df_genes, schema)
        
        _append_to_partition(df_genes, warehouse_root / "hero_genes", ontology)
        
    if reg_rows:
        df_reg = pd.DataFrame(reg_rows)
        # Enforce Schema
        from super.core.warehouse_schema import load_schema, enforce_schema
        schema = load_schema(str(warehouse_root), "hero_gene_regulation")
        if schema:
            df_reg = enforce_schema(df_reg, schema)

        _append_to_partition(df_reg, warehouse_root / "hero_gene_regulation", ontology)
        
    if seed_rows:
        # hero_gene_seeds is NOT partitioned in flatten_heroes.py
        df_seeds = pd.DataFrame(seed_rows)
        # Enforce Schema
        from super.core.warehouse_schema import load_schema, enforce_schema
        schema = load_schema(str(warehouse_root), "hero_gene_seeds")
        if schema:
            df_seeds = enforce_schema(df_seeds, schema)

        _append_to_root(df_seeds, warehouse_root / "hero_gene_seeds")


def _append_to_partition(df: pd.DataFrame, table_path: Path, ontology: str):
    """
    Appends DataFrame to a specific partition directory.
    Emulates Spark partitioning structure: table/ontology=X/part-UUID.parquet
    """
    if df.empty: return
    
    # Ensure partition dir
    part_dir = table_path / f"ontology={ontology}"
    part_dir.mkdir(parents=True, exist_ok=True)
    
    # Drop ontology column if it exists in DF, because it's in the directory path
    # Spark usually drops partition columns from the parquet file itself
    out_df = df.copy()
    if "ontology" in out_df.columns:
        out_df = out_df.drop(columns=["ontology"])
        
    # Generate unique filename
    # Prefix "part-adhoc-" to distinguish identifying source
    filename = f"part-adhoc-{uuid.uuid4()}.parquet"
    out_path = part_dir / filename
    
    out_df.to_parquet(out_path, engine="pyarrow", index=False)
    logger.debug(f"Wrote {len(out_df)} rows to {out_path}")


def _append_to_root(df: pd.DataFrame, table_path: Path):
    """
    Appends DataFrame to the root table directory (non-partitioned).
    """
    if df.empty: return
    
    table_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"part-adhoc-{uuid.uuid4()}.parquet"
    out_path = table_path / filename
    
    df.to_parquet(out_path, engine="pyarrow", index=False)
    logger.debug(f"Wrote {len(df)} rows to {out_path}")
