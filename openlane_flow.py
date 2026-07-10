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

    with open(ac.log_path, 'a') as file:
        file.write(f"LOG {run_tag}\n")

    # Initialize output_log content
    output_log = ""

    ol_designname_folder = os.path.join(ac.openlane_dir, ac.model, globals.design_name)

    if not os.path.exists(ol_designname_folder):
        #  Create folder with name followed by LLM model
        os.makedirs(ol_designname_folder)

    try:
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

        if return_code == 0:

            ac.show_log("\n[OL] OpenLane flow completed.\n")

            return True

        else:

            # Filter ERROR pattern in raw output_log
            err_extract, path_extr = openlane_parse_error()

            # log_file = result['output_log']

            # Internal brief output_log

            if err_extract:

                with open(ac.ol_log_path, 'w') as file:

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

        with open(ac.ol_log_path, 'r') as log_file:

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

    # First mainly log path from error parsing
    primary_detailed_log_path = ac.ol_summary_path

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

            data["FP_CORE_UTIL"] = 0.4

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


