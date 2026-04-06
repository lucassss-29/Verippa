import subprocess
import os
from agent_config import openlane_dir, model, design_name, ol_designname_folder, design_path, ol_source_mount, ol_target_mount
import shutil

def run_openlane_flow():
    print("Running OpenLane flow")

    ol_design_folder = os.path.join(openlane_dir, model, design_name)

    if not os.path.exists(ol_design_folder):
        #  Create folder with name followed by LLM model
        os.mkdir(ol_design_folder)

    try:
        path = shutil.copy(design_path, ol_designname_folder)
        print(f"Copied design files to {path}")

    except Exception as e:
        print(f"Error copying design files: {e}")
        return False, None

    init_cmd = f"./flow.tcl -design {design_name} -init_design_config -add_to_designs -src {ol_designname_folder}"

    flow_cmd = f"./flow.tcl -design {design_name}"

    try:
        inner_command = f"{init_cmd}\n{flow_cmd}\nexit\n"

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

        process.stdout.close()  # Close the stdout to signal that we're done reading
        return_code = process.wait()  # Wait for the process to finish

        if return_code == 0:
            print("\nFlow completed successfully.\n")
            return True, None

        else:
            print("\nFlow failed with code")
            err_msg = process.stderr.read()
            return False, err_msg
        
    except Exception as e:
        print(f"Failed to run OpenLane flow: {e}")
        return False, None
    
def symlink_folder():

    if not os.path.islink(ol_target_mount):
        try:
            os.symlink(ol_source_mount, ol_target_mount)
            print(f"Created symlink from {ol_source_mount} to {ol_target_mount}")

        except Exception as e:
            print(f"Error creating symlink: {e}")


run_openlane_flow()
# print(os.path.normpath(openlane_dir))