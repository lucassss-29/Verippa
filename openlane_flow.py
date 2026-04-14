import subprocess
import os
from agent_config import openlane_dir, model, design_name, ol_designname_folder, design_path, ol_source_mount, ol_target_mount, ol_log_file, custom_run_tag
import shutil
import re

def openlane_flow_run(is_init: bool):
    print("Running OpenLane flow")

    # Mount the OpenLane designs folder to current workspace
    openlane_symlink_folder()

    # Initialize log content
    log = ""

    ol_design_folder = os.path.join(openlane_dir, model, design_name)

    if not os.path.exists(ol_design_folder):
        #  Create folder with name followed by LLM model
        os.mkdir(ol_design_folder)

    try:
        path = shutil.copy(design_path, ol_designname_folder)
        print(f"Copied design files to {path}\n")

    except Exception as e:
        print(f"Error copying design files: {e}\n")
        return False, None
    
    flow_cmd = f"./flow.tcl -design {design_name} -tag {custom_run_tag}"

    if is_init:
        init_cmd = f"./flow.tcl -design {design_name} -init_design_config -add_to_designs -src {ol_designname_folder}"

        inner_command = f"{init_cmd}\n{flow_cmd}\nexit\n"
    else:
        inner_command = f"{flow_cmd}\nexit\n"

    try:
        # Execute the container and run the inner command non-interactively
        process = subprocess.Popen(
            ["make", "mount"],
            cwd=openlane_dir,
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
            log += line

        process.stdout.close()  # Close the stdout to signal that we're done reading
        return_code = process.wait()  # Wait for the process to finish

        with open(ol_log_file, 'w') as log_file:
            print(f"Writing OpenLane flow log to {ol_log_file}\n")
            log_file.write(log)

        if return_code == 0:
            print("\nFlow completed successfully.\n")
            return True, None

        else:
            result = openlane_parse_error()
            log_file = result['log']
            print(f"\nFlow failed with code:\n{log_file}\n")
            return False, log_file
        
    except Exception as e:
        print(f"Failed to run OpenLane flow: {e}\n")
        return False, None
    
def openlane_parse_error():

    with open(ol_log_file, 'r') as log_file:
        output_text = log_file.read()

    try:
        # step_match = re.findall(r"\[STEP (\d+)\]", output_text)
        # failed_step = step_match[-1] if step_match else "Unknown"

        pattern = r"^\[ERROR\]:.*$"

        matches = re.findall(pattern, output_text, re.MULTILINE)

        err_reason = ""

        for error in matches:
            err_reason += error + "\n"

        print(f"Found error line: {err_reason}\n")

        paths_list = openlane_extract_paths(err_reason)

        print(f"Detected paths: {paths_list}\n")

    except Exception as e:
        print(f"Error parsing log file path: {e}\n")

    return err_reason, paths_list

def openlane_extract_paths(text):
    # This regex is specifically tuned for the paths seen in OpenLane
    path_pattern = r"[\w\.\-\/]+\/[\w\.\-\/]+"
    
    # findall returns a list of all strings that look like paths
    paths = re.findall(path_pattern, text)
    return paths

def openlane_flow_correct():
    print("Correcting OpenLane flow\n")
    error_path = openlane_parse_error()
    if error_path is not None:
        log_path = os.path.join(openlane_dir, error_path)

        with open(log_path, 'r') as log_file:
            err_content = log_file.read()


def openlane_symlink_folder():

    if not os.path.islink(ol_target_mount):
        try:
            os.symlink(ol_source_mount, ol_target_mount)
            print(f"Created symlink from {ol_source_mount} to {ol_target_mount}\n")

        except Exception as e:
            print(f"Error creating symlink: {e}\n")


# openlane_flow_run(is_init=False)
# print(openlane_parse_error())
# print(os.path.normpath(openlane_dir))

