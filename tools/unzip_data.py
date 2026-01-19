
import os
import shutil
import zipfile
from pathlib import Path

def unzip_data_if_missing():
    # 1. Setup Paths
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    
    # 2. Conditional Check
    if data_dir.exists():
        print(f"Skipping unzip: 'data' directory already exists at {data_dir}")
        return

    # 3. Find latest Zip
    # Pattern: data_*.zip
    zips = list(project_root.glob("data_*kb_*.zip"))
    if not zips:
        print("Error: No data zip files found in project root (expected pattern: data_*.zip)")
        return
        
    # Sort by modification time (newest first)
    zips.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_zip = zips[0]
    
    print(f"Data directory missing. Restoring from: {latest_zip.name}")
    
    # 4. Unzip
    try:
        with zipfile.ZipFile(latest_zip, 'r') as zip_ref:
            zip_ref.extractall(project_root)
        print("Unzip successful.")
    except Exception as e:
        print(f"Error unzipping file: {e}")

if __name__ == "__main__":
    unzip_data_if_missing()
