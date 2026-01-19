import os
import shutil
import json
import pytest
import asyncio
from pathlib import Path
import pandas as pd

from super.apps.generate_powers import generate_heroes
from super.apps.etl import flatten_heroes
from super.core.utils import get_stage_root, get_app_conf
from super.apps.generate_powers.models_hero import HeroProfile

# Integration Test
# Run with: pytest tests/test_hero_creation.py -s

@pytest.fixture(scope="module")
def setup_environment():
    """
    Setup a clean environment for the test.
    We want to ensure we are using the 'mighty mouse' target.
    """
    conf = get_app_conf(app="generate_powers")
    targets = conf.get_list("generate_powers.targets")
    if not targets:
        hero_name = "Mighty Mouse"
    else:
        hero_name = targets[0]
        
    print(f"Test Configured for Target: {hero_name}")
    stage_root = get_stage_root()
    
    # 1. Clean previous run for repeatability
    # We specifically look for "Mighty Mouse" artifacts
    ontology = "generated"
    # hero_name is determined dynamically above
    safe_name = hero_name.replace(" ", "_").replace("'", "") # Basic sanitization match
    genome_safe_name = safe_name.lower()
    
    profile_path = stage_root / "hero_profiles" / ontology / f"{safe_name}.json"
    genome_path = stage_root / "hero_genomes" / ontology / f"{genome_safe_name}.json"
    
    # Ensure directories exist
    (stage_root / "hero_profiles" / ontology).mkdir(parents=True, exist_ok=True)
    
    # Clean files if exist
    if profile_path.exists(): os.remove(profile_path)
    if genome_path.exists(): os.remove(genome_path)
    # Also clean potential duplicates from retry logic
    if (stage_root / "hero_genomes" / ontology / f"{genome_safe_name}_1.json").exists():
        os.remove(stage_root / "hero_genomes" / ontology / f"{genome_safe_name}_1.json")
    
    # Clean warehouse for this hero? 
    # Warehouse is append-only usually or overwrite per partition.
    # We will check if data appears *after* run.
    
    yield {
        "stage_root": stage_root,
        "hero_name": hero_name,
        "safe_name": safe_name,
        "ontology": ontology,
        "profile_path": profile_path,
        "genome_path": genome_path
    }

def test_hero_creation_pipeline(setup_environment):
    env = setup_environment
    stage_root = env["stage_root"]
    hero_name = env["hero_name"]
    profile_path = env["profile_path"]
    
    # Verify Ontology Usage
    ontology = "generated" # Default for this test, but let's be explicit
    assert env["ontology"] == ontology
    
    print(f"\n[BEFORE] --- 1. Creating Hero Profile for Target: {hero_name} ---")
    print(f"[INFO] Target retrieved from configuration: {hero_name}")
    
    # Smart Seed Selection based on Name
    if "Panther" in hero_name or "Toon" in hero_name:
        primary_seed = "Toon Force"
        secondary = ["Invisibility"]
        side_effect = ["Irony Backfire"]
        bio = "A suave, silent feline with an uncanny ability to bend reality for comedic effect."
        print(f"[INFO] Detected '{hero_name}'. Using themed seed: {primary_seed}")
    else:
        primary_seed = "Heroic Strength"
        secondary = ["Flight"]
        side_effect = ["Hubris"]
        bio = "A hero with the strength of a titan."
        print(f"[INFO] Using default seed: {primary_seed}")

    # Create valid profile
    profile = HeroProfile(
        hero_name=hero_name,
        ontology=env["ontology"],
        primary_seed_name=primary_seed, 
        secondary_seed_names=secondary,
        side_effect_names=side_effect,
        bio=bio,
        estimated_connectivity="Low"
    )
    
    with open(profile_path, "w") as f:
        f.write(profile.model_dump_json(indent=2))
        
    assert profile_path.exists()
    assert profile_path.exists()
    print(f"[SUCCESS] Profile saved to disk at: {profile_path}")
    print(f"[DEBUG] Profile Content: {profile.model_dump_json()}")
    
    print(f"\n[DURING] --- 2. Running Generation Pipeline for {hero_name} ---")
    print("[INFO] Initializing Mocked LLM environment...")
    # The user wants an integration test. Real LLM call is expensive and slow.
    # But usually "integration test" implies real components.
    # However, to be deterministic and safe in CI, we usually mock the LLM.
    # BUT the user said "make the super hero names configurable ... integration test checks json powers".
    # If I mock the LLM, I must mock the JSON output. 
    # I will patch ChatOpenAI to return a valid JSON structure for the gene.
    
    # Mock Response data
    # Mock Response data using actual Pydantic models
    from super.apps.generate_powers.models import MutatedGene, PrimarySeed, RegulatedGeneLink, SideEffectEntry
    
    # Needs to match generate_single_gene validation rules (e.g. min 12 links)
    mock_gene = MutatedGene(
        gene_id="MIGHTY-001",
        mutation_class="Canonical",
        gene_role="Active",
        stability_index="Stable",
        confidence=0.95,
        failure_mode="None",
        primary_seeds=[PrimarySeed(seed=primary_seed, weight=1.0)],
        secondary_seeds=[],
        # Generate 12 dummy links to satisfy min_items=2 and the code's validation <12 check
        regulated_genes=[
            RegulatedGeneLink(gene_id=f"LINK-{i}", effect="Boost", strength=0.5) 
            for i in range(15)
        ],
        description=f"Genetically encoded ability: {primary_seed}",
        side_effect_profile=[
            SideEffectEntry(side_effect=side_effect[0], probability=0.8, severity=3, trigger_condition="Success")
        ]
    )
    
    from unittest.mock import patch, AsyncMock, MagicMock
    from unittest.mock import patch, AsyncMock, MagicMock
    # Patch get_valid_llm since generate_heroes uses that now
    with patch("super.core.utils.get_valid_llm") as MockGetLLM:
        # User MagicMock for the main model (methods are synchronous by default unless specified)
        mock_model_instance = MagicMock()
        
        # Create mock for the structured LLM runnable
        mock_structured_llm = MagicMock()
        
        # The ainvoke method on the structured LLM IS async 
        # so we set it to an AsyncMock that returns our gene
        mock_structured_llm.ainvoke = AsyncMock(return_value=mock_gene)
        
        # with_structured_output is synchronous and returns the structured_llm
        mock_model_instance.with_structured_output.return_value = mock_structured_llm
        
        # Also mock normal ainvoke just in case
        mock_model_instance.ainvoke = AsyncMock(return_value=type('obj', (object,), {"content": "{}"}))
        
        # Make get_valid_llm return our mock instance
        MockGetLLM.return_value = mock_model_instance

        # Run Generation
        # We need to run the async main
        from super.apps.generate_powers import generate_heroes
        asyncio.run(generate_heroes.main())
    
    # Check Genome
    genome_path = env["genome_path"]
    assert genome_path.exists(), "Genome file was not generated!"
    
    with open(genome_path, "r") as f:
        genome = json.load(f)
        
    print(f"Genome verified at {genome_path}")
    assert genome["hero_name"] == hero_name, "Genome hero name mismatch"
    # It's a single gene file, not a list of genes
    assert genome["gene_id"] == "MIGHTY-001", "Gene ID mismatch"
    assert genome["mutation_class"] == "Canonical"
    
    print(f"\n[AFTER] --- 3. running ETL (Flattening) ---")
    print("[INFO] Invoking Spark/Pandas ETL process to update Warehouse...")
    try:
        from super.apps.etl import flatten_heroes
        flatten_heroes.main()
        print("[SUCCESS] ETL Complete.")
    except Exception as e:
        print(f"[ERROR] ETL Failed: {e}")
        pytest.fail(f"ETL failed: {e}")
        
    print(f"\n[VERIFICATION] --- 4. Verifying Warehouse (Parquet) for {hero_name} ---")
    warehouse_root = stage_root / "warehouse"
    
    # Check hero_profiles.parquet
    profiles_pq = warehouse_root / "hero_profiles"
    assert profiles_pq.exists()
    df_profiles = pd.read_parquet(profiles_pq)
    
    print(f"Warehouse Profiles:\n{df_profiles.head()}")
    
    # Verify Mighty Mouse is in there
    mm = df_profiles[df_profiles['hero_name'] == hero_name]
    assert not mm.empty, f"{hero_name} not found in hero_profiles parquet"
    assert mm.iloc[0]['bio'] == profile.bio
    
    # Check hero_genes.parquet
    genes_pq = warehouse_root / "hero_genes"
    assert genes_pq.exists()
    df_genes = pd.read_parquet(genes_pq)
    
    mm_genes = df_genes[df_genes['hero_name'] == hero_name]
    assert not mm_genes.empty, f"{hero_name} genes not found in parquet"
    assert "MIGHTY-001" in mm_genes['gene_id'].values
    
    print("Integration Test Complete: Profile -> Genome -> Warehouse success.")

    # Check hero_gene_regulation.parquet
    reg_pq = warehouse_root / "hero_gene_regulation"
    assert reg_pq.exists(), "Regulation table not found"
    df_reg = pd.read_parquet(reg_pq)
    
    mm_reg = df_reg[df_reg['hero_name'] == hero_name]
    assert not mm_reg.empty, f"{hero_name} regulation not found in parquet"
    print(f"Regulation entries found: {len(mm_reg)}")
    assert len(mm_reg) >= 12, "Expected at least 12 links (from mock)"

    print("Integration Test Complete: Profile -> Genome -> Regulation -> Warehouse success.")
