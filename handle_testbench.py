import os
from agent_config import prj_dir, show_log
import globals
import agent_config as ac

# Return True and list of external inclusion in testbench
def check_tb_include_external():

    benchmark_folder = os.path.join(prj_dir, ac.benchmark_folder, globals.design_name)

    # Filter to get ONLY files
    files_only = [f for f in os.listdir(benchmark_folder) if os.path.isfile(os.path.join(benchmark_folder, f))]

    if ac.benchmark == ac.BenchmarkType.RTLLM:
        default_set = {'design_description.txt', 'makefile', 'testbench.v', f'verified_{globals.design_name}.v'}
    
    elif ac.benchmark == ac.BenchmarkType.VERILOGEVAL:
        default_set = {'design_description.txt', 'testbench.sv', f'verified_{globals.design_name}.sv'}

    files_set = set(files_only)

    # default set is smaller or equal file set
    diff_set = files_set - default_set

    if len(diff_set) != 0:

        show_log(f"The testbench inclusion is found {len(diff_set)} different files: {diff_set}\n")

        return True, diff_set
    
    else:

        show_log("No testbench inclusion is found.\n")

        return False, None
    
# res, file = check_tb_include_external()

# print(res, file)
