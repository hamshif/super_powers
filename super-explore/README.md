# Super Explore

This directory contains Jupyter notebooks and scripts for exploring, analyzing, and visualizing the generated superpower data.

## Notebooks

### 1. `analyze_heroes.ipynb` (Primary & New)
The advanced analytics dashboard for the "Super Power Sage" era.
*   **Data Source:** `super_powers/data/warehouse/` (Parquet) and `generated_genome` (JSON).
*   **Features:**
    *   **Pandas-Based Reporting**: Faster, lightweight analysis without full Spark sessions.
    *   **Data Integrity Checks**: Verifies that new heroes (from Ad-Hoc ETL) have valid genetics (`master_gene`, `genome_cluster`).
    *   **Single Hero Deep Dive**: Visualize the gene regulatory network for a specific hero.

### 2. `analyze_warehouse.ipynb` (Legacy Spark)
The original PySpark inspector.
*   **Features:**
    *   Loads all 6 tables using PySpark.
    *   **Sanity Export**: Exports top 10 rows to Excel (`data/sanity/warehouse_top10.xlsx`).

### 2. `analyze_genes.ipynb` (Legacy)
An earlier exploration notebook used to analyze the raw JSON genome data before the ETL pipeline was established.

## Setup

Ensure you have the project environment activated (created via `tools/create_pyenv.sh`):
```bash
pyenv activate super
```

When running the notebooks, ensure the kernel is set to **`super`**.

You can run these notebooks directly in VSCode or by launching Jupyter Lab:
```bash
jupyter lab
```
