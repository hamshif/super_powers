"""
Sanity check script to verify configuration loading.
Prints the merged configuration for the 'generate_powers' app.
"""
import sys
import os


from super.config import get_app_conf
from pyhocon import HOCONConverter

def main():
    print("Loading configuration for app='generate_powers'...")
    conf = get_app_conf("generate_powers")
    # print(HOCONConverter.to_hocon(conf))

    #print project_root and store_root
    print("project_root: ", conf.project_root)
    print("stage_root: ", conf.stage_root)
        


if __name__ == "__main__":
    main()
