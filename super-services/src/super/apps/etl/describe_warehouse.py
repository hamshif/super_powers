
import os
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow as pa
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

def describe_warehouse(warehouse_root: Path, output_file: Path = None):
    # Enable recording to capture output for file export
    console = Console(record=True, width=120)
    console.print(Panel(f"[bold blue]Warehouse Inspector[/bold blue]\nPath: {warehouse_root}", expand=False))

    if not warehouse_root.exists():
        console.print("[bold red]Warehouse directory does not exist![/bold red]")
        return

    # List strict directories (tables)
    tables = [d for d in warehouse_root.iterdir() if d.is_dir() and not d.name.startswith(".")]
    tables.sort(key=lambda x: x.name)

    for table_path in tables:
        table_name = table_path.name
        try:
            # Load dataset using PyArrow
            dataset = pq.ParquetDataset(table_path)
            schema = dataset.schema
            
            # Identify columns
            cols = schema.names
            
            # Row count (efficient scan if metadata exists)
            # metadata=True allows reading total row count from file footers
            full_table = dataset.read()
            row_count = len(full_table)
            
            # Create Schema Table
            schema_table = Table(title=f"Table: [bold green]{table_name}[/bold green] (Rows: {row_count})", show_header=True, header_style="bold magenta")
            schema_table.add_column("Column", style="cyan")
            schema_table.add_column("Type", style="yellow")
            schema_table.add_column("Partition?", style="red")

            # Let's inspect the first file to see 'physical' columns vs 'virtual' partition columns
            fragments = dataset.fragments
            try:
                first_frag = next(iter(fragments))
                phys_schema = first_frag.physical_schema
                phys_cols = set(phys_schema.names)
            except StopIteration:
                phys_cols = set()

            for field in schema:
                # If we want to be strict about partitions we'd analyze directory structure.
                # For now, listing the full schema is "describing" it sufficient for the user.
                
                schema_table.add_row(field.name, str(field.type), "")

            console.print(schema_table)
            console.print()

        except Exception as e:
            console.print(f"[bold red]Failed to read {table_name}:[/bold red] {e}")

    # Export to file if requested
    if output_file:
        console.save_text(str(output_file))
        console.print(f"[bold green]Schema saved to: {output_file}[/bold green]")

if __name__ == "__main__":
    import sys
    # Default to standard path or arg
    root = Path(__file__).parents[5] / "data" / "warehouse"
    output = None
    
    if len(sys.argv) > 1:
        # If first arg is a file path (doesn't start with /data/warehouse unless explicit), 
        # check if it looks like an output file or input dir.
        arg1 = Path(sys.argv[1])
        if arg1.name.endswith(".txt") or arg1.name.endswith(".md") or "warehouse_schema" in arg1.name:
            output = arg1
        else:
            root = arg1
            
    if len(sys.argv) > 2:
        output = Path(sys.argv[2])
    
    describe_warehouse(root, output)
