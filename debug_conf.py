
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append("super-services/src")

from super.core.utils import get_app_conf, get_stage_root

print("--- Sanity Check ---")
try:
    conf = get_app_conf(app="super_power_sage")
    print("\n[App Config]")
    print(conf)
except Exception as e:
    print(f"\n[App Config Error] {e}")

try:
    stage = get_stage_root()
    print(f"\n[Stage Root] {stage}")
    print(f"[Warehouse Path] {stage / 'warehouse'}")
    print(f"[Warehouse Exists?] {(stage / 'warehouse').exists()}")
except Exception as e:
    print(f"\n[Stage Root Error] {e}")
