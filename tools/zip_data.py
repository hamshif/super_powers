
import os
import shutil
import subprocess
from pathlib import Path
import zipfile
import datetime

def zip_data_dir():
    # 1. Setup Paths
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    output_zip = project_root / "data.zip"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        return

    # 2. Get Metadata
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], 
            cwd=project_root, 
            text=True
        ).strip()
    except subprocess.CalledProcessError:
        commit_hash = "unknown"

    # Calculate dir size
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(data_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    
    size_mb = total_size / (1024 * 1024)
    date_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print(f"Zipping data directory: {data_dir}")
    print(f"Metadata: Commit={commit_hash}, Size={size_mb:.2f}MB, Date={date_str}")

    # 3. Create Config File
    conf_content = f"""data_change_log {{
    date = "{date_str}"
    size = "{size_mb:.2f}MB"
    commit = "{commit_hash}"
}}
"""
    conf_path = project_root / "data_change_log.conf"
    with open(conf_path, "w") as f:
        f.write(conf_content)

    # 4. Create Zip
    # We use 'zipfile' to add both the directory and the config file at root
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add Config
            zf.write(conf_path, arcname="data_change_log.conf")
            
            # Add Data Directory
            # arcname should be relative to project root, e.g. "data/foo.txt"
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    file_path = Path(root) / file
                    # Relative path for archive
                    arcname = file_path.relative_to(project_root)
                    zf.write(file_path, arcname=arcname)
                    
        print("-" * 40)
        print(f"SUCCESS")
        print("-" * 40)
        print(f"Archive created: {output_zip.name}")
        print(f"Location:        {output_zip}")
        print("-" * 40)
        
    finally:
        # Cleanup config file from root (it's inside the zip now)
        if conf_path.exists():
            os.remove(conf_path)

if __name__ == "__main__":
    zip_data_dir()
