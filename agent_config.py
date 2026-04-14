import os
import time

# Global variables


# Get the local time structure
current_time = time.localtime()

# Format the time structure into a string
timestamp = time.strftime("%Y.%m.%d_%H.%M.%S", current_time)

custom_run_tag = f"RUN_{timestamp}"
# custom_run_tag = "RUN_2026.04.14_05.02.58"

log = [f"LOG {custom_run_tag}"]

prj_dir = os.getcwd()

openlane_dir = os.path.join(prj_dir, "..", "OpenLane")

max_attempts = 5

design_name = 'adder_16bit'

benchmark_design_path = os.path.join(prj_dir, "Dataset", design_name, "design_description.txt")

model = 'Deepseek'

design_folder_path = os.path.join(prj_dir, model, design_name)

design_path = os.path.join(prj_dir, model, design_name, f"{design_name}.v")

tb_path = os.path.join(prj_dir, "Dataset", design_name, "testbench.v")

out_conversation_path = os.path.join(prj_dir, model, design_name, f"{design_name}_conversation.txt")

# success log
log_path = os.path.join(design_folder_path, "flow.log")

# failure log
fail_log_path = os.path.join(design_folder_path, "error.log")

ol_designname_folder = os.path.join(openlane_dir, model, design_name, f"{design_name}.v")

ol_source_mount = os.path.join(openlane_dir, "designs")

ol_target_mount = os.path.join(prj_dir, "designs_mounted")

ol_log_file = os.path.join(prj_dir, "Openlane", f"{design_name}_openlane_log.txt")

csv_path = os.path.join(ol_source_mount, design_name, "runs", custom_run_tag, "reports", "metrics.csv")

excel_path = os.path.join(prj_dir, "Report", "ppa_metrics.xlsx")

print(design_path)

def show_log(info: str):

    log.append(info)

    print(info)


def save_log():
    
    with open(log_path, 'w') as file:

        content = "\n".join(log)

        file.write(content)

def save_failure_int_log(info: str):

    with open(fail_log_path, 'a') as file:

        file.write(f"{info}\n")
