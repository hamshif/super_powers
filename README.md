# Super Powers

**Super Powers** is a system for generating, analyzing, and visualizing a complex "Mytho-Toon" genome of superpowers using LLMs and Data Engineering pipelines.

## Project Structure

This repository is organized into three main components:

### 1. [Super Services](super-services/README.md)
**The Backend Core.**
*   Generates novel superpowers and gene regulatory networks using LLMs.
*   Runs the ETL pipeline (`flatten.py`) to convert raw JSON generation logs into a structured Parquet Data Warehouse.
*   Manages configuration and Spark runtime.

### 2. [Super Explore](super-explore/README.md)
**Analysis & Notebooks.**
*   Contains Jupyter notebooks for auditing and exploring the data.
*   **`analyze_warehouse.ipynb`**: The primary tool for querying the flattened Parquet data (Genes, Powers, Regulation Graph) and exporting sanity checks to Excel.

### 3. [Super Web](super-web/README.md)
**Frontend Visualization.**
*   A React/Vite application for visualizing the generated powers and genes.
*   Provide an immersive, "Bio-DNA" aesthetic interface.

---

## Quick Setup

### Python (Backend & Analysis)
Run this once to set up the Python environment (using `pyenv-virtualenv`):

```bash
source tools/create_pyenv.sh
```
This installs dependencies, sets up the `super` environment, and configures your shell.

### Node.js (Frontend)
To set up the web interface:

```bash
cd super-web
npm install
npm run dev
```

## Data Workflow
1.  **Generate**: Run `generate_genome.py` (in `super-services`) to create raw JSON data in `data/generated_genome`.
2.  **ETL**: Run `flatten.py` (in `super-services`) to clean and flatten data into `data/warehouse`.
3.  **Analyze**: Use `analyze_warehouse.ipynb` (in `super-explore`) to query the warehouse or export to Excel.
