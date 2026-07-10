import os
from agent_config import prj_dir, model
import shutil
import re
import globals
import agent_config as ac

# Copy benchmark design folder to running folder
def copy_benchmark_design():

    if ac.benchmark == ac.BenchmarkType.VERILOGEVAL:

        bm_file = os.path.join(prj_dir, ac.benchmark_folder, globals.design_name, f"verified_{globals.design_name}.sv")

        target_file = os.path.join(prj_dir, model, globals.design_name, f"{globals.design_name}.sv")

    else:
        bm_file = os.path.join(prj_dir, ac.benchmark_folder, globals.design_name, f"verified_{globals.design_name}.v")

        target_file = os.path.join(prj_dir, model, globals.design_name, f"{globals.design_name}.v")

    if not os.path.exists(os.path.dirname(target_file)):
        os.makedirs(os.path.dirname(target_file), exist_ok=True)

    shutil.copy(bm_file, target_file)

    with open(target_file, 'r') as file:
        
        content = file.read()

        # Replace 
        pattern = r'(module\s+)verified_(\w+)'
        new_content = re.sub(pattern, r'\1\2', content)

        with open(target_file, 'w') as f:
            f.write(new_content)

    print(f"Copied benchmark design file to {target_file}\n")


