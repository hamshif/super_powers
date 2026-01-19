# Super Explore

This directory contains Jupyter notebooks and scripts for exploring, analyzing, and visualizing the generated superpower data.

## Notebooks

### 1. `analyze_warehouse.ipynb` (Primary)
The main entry point for analyzing the flattened Parquet warehouse.
*   **Data Source:** `super_powers/data/warehouse/`
*   **Features:**
    *   Loads all 6 tables (`genes`, `powers`, `gene_seeds`, `power_seeds`, `gene_regulation`, `gene_side_effects`) using PySpark.
    *   Displays scrollable DataFrames for easy inspection.
    *   **Sanity Export:** Includes a block to export the top 10 rows of every table to an Excel file (`data/sanity/warehouse_top10.xlsx`).

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
