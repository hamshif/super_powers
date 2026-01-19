
import os
import zipfile
from pathlib import Path

def unzip_data_if_missing():
    # 1. Setup Paths
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    zip_path = project_root / "data.zip"
    
    # 2. Conditional Check
    if data_dir.exists():
        print(f"Skipping unzip: 'data' directory already exists at {data_dir}")
        return

    # 3. Check for Zip
    if not zip_path.exists():
        print("Error: data.zip not found in project root.")
        return
        
    print(f"Data directory missing. Restoring from: {zip_path.name}")
    
    # 4. Unzip
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(project_root)
        print("Unzip successful.")
        
        # Log metadata if available
        conf_path = project_root / "data_change_log.conf"
        if conf_path.exists():
            with open(conf_path, "r") as f:
                print("--- Metadata ---")
                print(f.read().strip())
                print("----------------")
                
    except Exception as e:
        print(f"Error unzipping file: {e}")

if __name__ == "__main__":
    unzip_data_if_missing()
