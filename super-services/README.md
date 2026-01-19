# Super Services

The core Python backend for the Super Powers project. It handles data generation, LLM interaction, and ETL processing.

## Modules

### 1. Power Generation (`src/super/apps/generate_powers`)
*   **`generate_genome.py`**: The main orchestration script. Generates the "Mytho-Toon Genome" by intelligently mixing seeds, applying mutations, and regulating genes.
*   **`models.py`**: Pydantic definitions for Genes, Powers, and Linkage.
*   **Robustness**: Includes a retry loop to ensure all generated genes meet connectivity filters (>=12 connections) and use canonical side effects.

### 2. ETL Pipeline (`src/super/apps/etl`)
*   **`flatten.py`**: A PySpark job that transforms the complex, nested JSON output from the generation step into a flat, star-schema Parquet warehouse.
*   **Features**:
    *   Flattens `secondary_seeds` and `mixed_seeds` into link tables.
    *   Cleans side effect names (Typo fixing, Deduplication).
    *   Generates deterministic IDs for powers.

### 3. Core Runtime (`src/super/core`)
*   **`runtime.py`**: Bootstraps the Spark environment (Java/Spark Home).
*   **`utils.py`**: Configuration loading (HOCON) and path resolution.

## Configuration
Configuration is managed via HOCON files in `conf/`.
*   `apps/generate_powers/app.conf`: Default generation settings.
*   `developer/developer.conf`: Developer overrides (e.g., `selection_count`, `stage_root`).

## Running
To run the generation pipeline:
```bash
python src/super/apps/generate_powers/generate_genome.py
```

To run the ETL pipeline:
```bash
python src/super/apps/etl/flatten.py
```
