
import os
import shutil
import subprocess
from pathlib import Path
import zipfile

def zip_data_dir():
    # 1. Setup Paths
    # Script is in tools/, so project root is one level up
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        return

    # 2. Get Git Commit Hash
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], 
            cwd=project_root, 
            text=True
        ).strip()
    except subprocess.CalledProcessError:
        print("Warning: Could not get git commit hash. Using 'unknown'.")
        commit_hash = "unknown"

    print(f"Zipping data directory: {data_dir}")
    print(f"Current Commit: {commit_hash}")

    # 3. Create Zip (to temporary name first)
    # We use 'zipfile' to have control over the structure (avoiding excessive nesting if needed)
    # or shutil.make_archive. shutil is simplest.
    # It creates a zip file with the base_name + .zip
    
    temp_base = project_root / "temp_data_archive"
    archive_path = shutil.make_archive(
        base_name=str(temp_base),
        format="zip",
        root_dir=project_root,
        base_dir="data" # This keeps the 'data' folder inside the zip
    )
    
    archive_path = Path(archive_path) # Now points to temp_data_archive.zip

    # 4. Calculate Size
    size_bytes = archive_path.stat().st_size
    size_kb = int(size_bytes / 1024)
    
    # 5. Formulate New Name
    # Format: data_<kb>_<last commit>.zip
    new_name = f"data_{size_kb}kb_{commit_hash}.zip"
    final_path = project_root / new_name
    
    # 6. Rename
    if final_path.exists():
        os.remove(final_path)
        
    archive_path.rename(final_path)
    
    # 7. Log
    print("-" * 40)
    print(f"SUCCESS")
    print("-" * 40)
    print(f"Archive created: {final_path.name}")
    print(f"Location:        {final_path}")
    print(f"Size:            {size_kb:,} KB")
    print("-" * 40)

if __name__ == "__main__":
    zip_data_dir()
