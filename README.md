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

## 🚀 Quick Start (Docker / Reviewers)
For a **one-click** setup (Data Packing + Build + Run + Browser Launch):

```bash
./start_demo.sh
```
*Requirements: Docker, Python 3 installed.*

---
## 📦 Quick Setup (Local Dev)

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

## 🤖 Super Power Sage (Agent)

**Super Power Sage** is an intelligent LangGraph agent that can query, analyze, and expand the super power universe through natural language.

### Capabilities
- **Universal Knowledge**: It has access to the entire Data Warehouse (Parquet files) and Graph Database.
- **Creative Generation**: Can invent new heroes from scratch, generating full "Mytho-Toon" genetics and regulatory networks on the fly.
- **Graph Traversal**: Can explore relationships between heroes, genes, power sources, and side effects.

### Tools
The Agent is equipped with the following tools:

| Tool | Description |
| :--- | :--- |
| `search_heroes(query)` | Finds heroes by name, alias, or bio keywords using fuzzy matching and LLM expansion. |
| `get_hero_details(name)` | Retrieves full profile, engineered genome, and power source data. |
| `get_connected_entities(name)` | Traverses the knowledge graph to find friends, enemies, or shared genetic traits. |
| `find_heroes_by_ability(power)` | Locates all heroes possessing a specific capability (e.g. "Flight"). |
| `create_new_hero(name, ...)` | **Agentic Creation**: Generates a new hero profile, synthesizes their genome via LLM, and instantly performs Ad-Hoc ETL to add them to the warehouse. |
| `list_ontologies()` | Lists available universes (e.g., "generated", "marvel", "lotr"). |
