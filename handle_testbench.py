import os
from agent_config import design_name, prj_dir, show_log

# Return True and list of external inclusion in testbench
def check_tb_include_external():

    benchmark_folder = os.path.join(prj_dir, "Dataset", design_name)

    # Filter to get ONLY files
    files_only = [f for f in os.listdir(benchmark_folder) if os.path.isfile(os.path.join(benchmark_folder, f))]

    default_set = {'design_description.txt', 'makefile', 'testbench.v', f'verified_{design_name}.v'}

    files_set = set(files_only)

    # default set is smaller or equal file set
    diff_set = files_set - default_set

    if len(diff_set) != 0:

        show_log(f"\nThe testbench inclusion is found {len(diff_set)} different files: {diff_set}")

        return True, diff_set
    
    else:

        show_log("\nNo testbench inclusion is found.")

        return False, None
    
# res, file = check_tb_include_external()

# print(res, file)
