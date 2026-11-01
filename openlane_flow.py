from dis import show_code
import subprocess
import os
import agent_config as ac
import shutil
import re
import json
from enum import Enum, auto
import globals
from auto_code_generation import openlane_generation
import shutil
import glob
from agent_config import fetch_workflow_variables

ADJUST_CLOCK_PED = 10

# Class to category Openlane during correct flow phase.
class OpenLaneIssue(Enum):
    PDN_0175_SMALL = auto()
    REGEN_DESIGN = auto()
    CLOCK_PED = auto()

# Run OpenLane and return True: successful, False: failure
def openlane_flow_run(is_init: bool, run_tag):

    # Mount the OpenLane designs folder to current workspace
    openlane_symlink_folder()

    with open(globals.app_usage_dict['log_path'], 'a') as file:
        file.write(f"LOG {run_tag}\n")

    # Initialize output_log content
    output_log = ""

    # Specific folder in OpenLane directory
    ol_designname_folder = os.path.join(ac.openlane_dir, ac.model, globals.design_name)

    if not os.path.exists(ol_designname_folder):
        #  Create folder with name followed by LLM model
        os.makedirs(ol_designname_folder)

    try:
        print(ac.design_path)

        print(ol_designname_folder)

        path = shutil.copy(ac.design_path, ac.ol_designname_folder)
        
        ac.show_log(f"\n[OL] Copied design files to {path}\n")

    except Exception as e:

        print(f"Error copying design files: {e}\n")

        return False

    flow_cmd = f"./flow.tcl -design {globals.design_name} -tag {run_tag}"

    if is_init:

        init_cmd = f"./flow.tcl -design {globals.design_name} -init_design_config -add_to_designs -src {ac.ol_designname_folder}"

        inner_command = f"{init_cmd}\n{flow_cmd}\nexit\n"

    else:

        inner_command = f"{flow_cmd}\nexit\n"

    try:
        # Execute the container and run the inner command non-interactively
        process = subprocess.Popen(
            ["make", "mount"],
            cwd=ac.openlane_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        process.stdin.write(inner_command)

        process.stdin.flush()

        for line in iter(process.stdout.readline, ''):
            # Print each line to your terminal as it's generated
            print(line, end='') 

            output_log += line

        # Close the stdout to signal that we're done reading
        process.stdout.close()  

        # Wait for the process to finish
        return_code = process.wait()

        if not os.path.exists(os.path.dirname(ac.ol_raw_log)):

            os.mkdir(os.path.dirname(ac.ol_raw_log))

        with open(ac.ol_raw_log, 'w') as log_file:

            ac.show_log(f"[OL] Writing OpenLane flow output_log to {ac.ol_raw_log}\n")

            log_file.write(output_log)

        globals.app_usage_dict['openlane_trace_path'] = ac.ol_raw_log

        if return_code == 0:

            ac.show_log("\n[OL] OpenLane flow completed.\n")

            return True

        else:

            # Filter ERROR pattern in raw output_log
            err_extract, path_extr = openlane_parse_error()

            # log_file = result['output_log']

            # Internal brief output_log

            if err_extract:

                with open(globals.app_usage_dict['ol_log_path'], 'w') as file:

                    file.write(err_extract)

                print(f"Flow failed with code:\n{err_extract}\n")

            if path_extr:

                # Write log path to file for further processing
                with open(ac.ol_path_extracted, 'w') as f:

                    f.write(path_extr)

            return False
        
    except Exception as e:

        print(f"Exception failed to run OpenLane flow: {e}\n")

        return False
    
def openlane_run_exploration():

    openlane_extract_json_update_matrix()

    expl_log = ""

    expl_command = f"python3 ./run_designs.py --matrix ./explore_matrix.json --threads 6 {globals.design_name} --tag {globals.timestamp_tag} --disable_timestamp"

    inner_command = f"{expl_command}\nexit\n"

    try:

        if not os.path.exists(ac.openlane_dir):
            print(f"ERROR: The directory '{ac.openlane_dir}' does not exist!")

        # Execute the container and run the inner command non-interactively
        process = subprocess.Popen(
            ["make", "mount"],
            cwd=ac.openlane_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        process.stdin.write(inner_command)
        process.stdin.flush()
        # process.stdin.close()

        # for line in iter(process.stdout.readline, ''):
        for line in process.stdout:
            # Print each line to your terminal as it's generated
            print(line, end='') 

            expl_log += line

        # process.stdout.close()  
        # return_code = process.wait()

        if not os.path.exists(os.path.dirname(ac.ol_expl_log)):

            os.mkdir(os.path.dirname(ac.ol_expl_log))

        with open(ac.ol_expl_log, 'w') as log_file:

            ac.show_log(f"[OL] Writing OpenLane exploration log to {ac.ol_expl_log}\n")

            log_file.write(expl_log)


        ac.show_log("\n[OL] OpenLane exploration completed.\n")

        delete_path = os.path.join(ac.openlane_dir, "designs", globals.design_name)

        openlane_delete_temp_items(delete_path)
        
    except Exception as e:

        print(f"Exception failed to run OpenLane flow: {e}\n")

    
# Purpose: extract error keyword by re and its path (if any)
def openlane_parse_error():

    err_reason = ""

    path_reason = ""

    with open(ac.ol_raw_log, 'r') as log_file:

        output_text = log_file.read()

    try:
        # step_match = re.findall(r"\[STEP (\d+)\]", output_text)
        # failed_step = step_match[-1] if step_match else "Unknown"

        # Extract [ERROR] pattern
        pattern = r"^\[ERROR\]:.*$"

        matches = re.findall(pattern, output_text, re.MULTILINE)

        if matches:

            for error in matches:

                err_reason += error + "\n"

            # Extract paths from the error reason (if any)
            paths_list = openlane_extract_paths(err_reason)

            if paths_list:
                
                ac.show_log(f"Openlane failed extracted number of paths: {len(paths_list)}\n")

                for path in paths_list:

                    path_reason = path + "\n"

                    print(f"Detected paths: {path_reason}\n")
                
    except Exception as e:

        print(f"Exception error parsing output_log file path: {e}\n")

    return err_reason, path_reason

def openlane_extract_paths(text):

    # This regex is specifically tuned for the paths seen in OpenLane
    path_pattern = r"[\w\.\-\/]+\/[\w\.\-\/]+"
    
    # findall returns a list of all strings that look like paths
    paths = re.findall(path_pattern, text)

    return paths


def openlane_symlink_folder():

    if not os.path.islink(ac.ol_target_mount):
        
        try:
            os.symlink(ac.ol_source_mount, ac.ol_target_mount)

            print(f"Created symlink from {ac.ol_source_mount} to {ac.ol_target_mount}\n")

        except Exception as e:

            print(f"Exception error creating symlink: {e}\n")

def openlane_update_json():

    global ADJUST_CLOCK_PED

    ADJUST_CLOCK_PED += 10

    with open(ac.ol_json_path, "r") as f:
        data = json.load(f)

    data["CLOCK_PERIOD"] = ADJUST_CLOCK_PED

    with open(ac.ol_json_path, "w") as f:

        json.dump(data, f, indent=4)

    ac.show_log(f"Updated successfully with CLOCK_PERIOD: {ADJUST_CLOCK_PED}\n")


def openlane_extract_json_update_matrix():


    with open(ac.ol_json_path, "r") as f:
        data = json.load(f)

    current_period = data.get("CLOCK_PERIOD")

    # Optional configuration in default file
    current_util = data.get("FP_CORE_UTIL")

    matrix_config = {
        "preload": {
            "DESIGN_NAME": globals.design_name,
            "RUN_KLAYOUT": False,
            "GLB_RESIZER_TIMING_OPTIMIZATIONS": True
        }
    }

    type = "Performance"

    match type:

        case "Performance":

            list_clk = [current_period - 6, current_period - 5, current_period - 4, current_period - 2]

            matrix_config["CLOCK_PERIOD"] = list_clk
            matrix_config["SYNTH_STRATEGY"] = ["DELAY 0", "DELAY 2", "DELAY 4"]

            if current_util is not None:

                list_util = [current_util - 10, current_util - 5, current_util]
                matrix_config["FP_CORE_UTIL"] = list_util

            else:
                # Default core util 50
                matrix_config["FP_CORE_UTIL"] = [35, 40, 45]

            matrix_config["PL_TARGET_DENSITY"] = [0.40, 0.55]

            # matrix_config["CLOCK_PERIOD"] = [8]

            # matrix_config["SYNTH_STRATEGY"] = ["DELAY 0"]

            # matrix_config["FP_CORE_UTIL"] = [40]

            # matrix_config["PL_TARGET_DENSITY"] = [0.40]

        case "Power":
            pass

        case "Area":
            pass

        case _:
            pass

    with open(ac.ol_json_matrix, "w", encoding="utf-8") as f:
        json.dump(matrix_config, f, indent=4)

    ac.show_log("Update exploration .json file done\n")


# Find in raw log step number of failed setup.
def openlane_error_find_step():

    # Dummy step number
    step_number = 255

    if os.path.exists(ac.ol_path_extracted):

        with open(ac.ol_path_extracted, 'r') as log_file:

            log_data = log_file.read()

        # Pattern to find 'Step' followed by a number
        step_pattern = r"\/(\d+)-"

        match = re.search(step_pattern, log_data)

        if match:
            step_number = match.group(1)
    
    else:

        with open(globals.app_usage_dict['ol_log_path'], 'r') as log_file:

            log_data = log_file.read()

        step_pattern = r"Step\s+(\d+)"

        match = re.search(step_pattern, log_data)

        if match:
            step_number = match.group(1)

    ac.show_log(f"Openlane failed step: {step_number}\n")

    return int(step_number) 


def openlane_error_linter():

    error_count = 0

    log_path = ""

    with open(ac.ol_raw_log, 'r') as log_file:

        log_data = log_file.read()

    match = re.search(r"(\d+)\s+errors found by linter", log_data)

    if match:

        error_count = match.group(1)

        print(f"Found {error_count} errors by linter.\n")

        if int(error_count) > 0:

            pattern = r"Running linter \(Verilator\) \(log: ([\w\/\.\-]+)\)"

            log_match = re.search(pattern, log_data)

            if log_match:

                log_path = log_match.group(1)

                # Convert to absolute path
                log_path = os.path.join(ac.openlane_dir, log_path)

                print(f"Log File Path: {log_path}\n")
    else:
        print("No errors found by linter.")

    return int(error_count), log_path

def openlane_correct(msg, attempt):

    primary_detailed_log_path = ""

    # First mainly log path from error parsing
    if os.path.exists(ac.ol_path_extracted):

        with open(ac.ol_path_extracted, 'r') as f:
        
            extracted_path = f.readline().strip()

            primary_detailed_log_path = os.path.join(ac.openlane_dir, extracted_path)

    issue = "unknown issue"

    found_step = openlane_error_find_step()

    match found_step:

        case 0:
            # STEP 0
            lt_cnt, lt_log = openlane_error_linter()

            if lt_cnt > 0:

                issue = OpenLaneIssue.REGEN_DESIGN

                primary_detailed_log_path = lt_log

        case 1:
            # STEP 1
            with open(ac.ol_raw_log, 'r') as f:

                output_log = f.read()

                pattern = r'Running Synthesis.*?log:\s*([^)]+)'

                match = re.search(pattern, output_log)

                if match:
                    synthesis_path = match.group(1)

                    primary_detailed_log_path = os.path.join(ac.openlane_dir,synthesis_path)

            issue = OpenLaneIssue.REGEN_DESIGN

            pass

        case 31:
            # STEP 31
            issue = OpenLaneIssue.CLOCK_PED

        case _:
            # STEP 6
            issue = OpenLaneIssue.PDN_0175_SMALL
        
    phase = "phase_3"

    # Save in file error.log 
    ac.save_failure_int_log(f"{phase} attempt {attempt}: {issue}")

    match issue:

        case OpenLaneIssue.PDN_0175_SMALL:

            # Manually update json ac
            with open(ac.ol_json_path, "r") as f:
                data = json.load(f)

            if data.get("FP_CORE_UTIL") is None:

                # Default is 50, offset minus 5 for each time.
                data["FP_CORE_UTIL"] = 45

            elif data.get("FP_CORE_UTIL") > 5:

                data["FP_CORE_UTIL"] = data.get("FP_CORE_UTIL") - 5
            else:
                data["FP_CORE_UTIL"] = 2

            with open(ac.ol_json_path, "w") as f:

                json.dump(data, f, indent=4)

            ac.show_log(f"Updated successfully with FP_CORE_UTIL: {data['FP_CORE_UTIL']}\n")

            # No need init Openlane container again
            globals.olis_init = False

            return True

        case OpenLaneIssue.REGEN_DESIGN:

            openlane_generation(msg, primary_detailed_log_path, attempt, phase)

            globals.ol_redirect = True

        case OpenLaneIssue.CLOCK_PED:
            
            openlane_update_json()

            globals.olis_init = False
        
        case _:
            return "Unknown status"


def openlane_delete_temp_items(path):

    search_pattern = os.path.join(path, "runs", "RUN_EX_*")

    # Remove folders
    for folder_path in glob.glob(search_pattern):
        if os.path.isdir(folder_path):
            current_folder_name = os.path.basename(folder_path)

            if current_folder_name == globals.exploration_tag:
                print(f"Skipping (Preserving): {folder_path}")
                continue

            print(f"Deleting folder: {folder_path}")
            shutil.rmtree(folder_path)

    # Remove files
    # json_pattern = os.path.join(path, f"{globals.timestamp_tag}_config_*.json")
    
    # for file_path in glob.glob(json_pattern):
    #     # Ensure it is a file, not a folder
    #     if os.path.isfile(file_path):  
    #         print(f"Deleting file: {file_path}")
    #         os.remove(file_path)

    
