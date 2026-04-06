import os
import subprocess
import time
import logging
from auto_code_generation import llm_generation
from kill_process import kill_process_by_name
from agent_config import design_path, tb_path, design_name

std_cmd = "iverilog -Wall -Winfloop -Wno-timescale -g2012 -gsupported-assertions"

# Configure logging to include timestamps and log level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

def check_syntax_only():
    """
    Checks the syntax of a Verilog file using the Icarus Verilog compiler (iverilog).
    This function only performs a syntax check without generating an executable.
    """
    if not os.path.exists(design_path):
        err_msg = "File not found"
        return False, err_msg
    else:
        # -t null tells iverilog to check syntax without generating output code
        cmd = f"{std_cmd} -o ./compilation_out/temp {design_path}"

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                # logging.info(result.stdout)
                return True, None
            else:
                logging.error(result.stderr)
                err_msg = result.stderr
                return False, result.stderr
            
        except Exception as e:
            print(f"Command failed with return code {e}")
            return False, e

def run_testbench():
    """
    Compiles and runs a Verilog testbench using iverilog and vvp.
    Returns the simulation output and error messages.
    """
    output_vvp_path = os.path.join("./simulation_out", f"{design_name}_test.vvp")

    # Compilation command
    compl_cmd = f"{std_cmd} -o {output_vvp_path} {design_path} {tb_path}"
    sim_cmd = f"vvp {output_vvp_path}"
    run_cmd = compl_cmd + " && " + sim_cmd
    error_match = False
    
    #  start_new_session=True ensures that the process is started in a new session, allowing us to kill the entire process group if needed
    process = subprocess.Popen(run_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        #  Wait for the process to complete with a timeout
        stdout, stderr = process.communicate(timeout=20)

        #  TODO: what if the output not contains "Failed" or "Error"
        if "failed" in stdout.lower() or "failed" in stderr.lower() or "error" in stdout.lower() or "error" in stderr.lower():
            error_match = True

        if process.returncode != 0 or error_match:
            error_msg = f"Simulation failed: {stdout}\n{stderr}\nReproducing command: {run_cmd}"
            logging.error(error_msg)
            return False, error_msg
        else:
            logging.info(stdout)
            logging.info("Simulation completed successfully.")
            return True, None
        
    except subprocess.TimeoutExpired as te:
        #  Kill the entire process group to ensure all child processes are terminated
        kill_process_by_name("vvp")
        # os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        
        # # Clean up any remaining processes
        # process.communicate()

        # Check if the process is still running
        while process.poll() is None:
            print("Process is still running...")
            time.sleep(1) # Add a small delay to avoid using too much CPU

        print(f"Process finished with return code: {process.returncode}")

        error_msg = f"Simulation process killed due to timeout: {te}."
        logging.error(error_msg)
        return False, error_msg
    
    except Exception as e:
        error_msg = f"Unexpected error occurred: {e}"
        logging.error(error_msg)
        return False, error_msg

if __name__ == "__main__":

    design_name = 'accu'

    model = "deepseek-rs-v3.2"

    file_path = './Deepseek_model/accu/accu.v'
    tb_file_path = "./Deepseek_model/accu/accu_tb.v"

    result, err_reason = check_syntax_only(file_path)

    if result:
        print("The design is syntaxcally correct.")
        tb_result, err_ms = run_testbench(file_path, tb_file_path, "id_01")
        if tb_result:
            print("The design is simulated with no errors.")
        else:
            logging.info("Simulation failed with error")
            # simulation_correct(err_ms, tb_file_path, file_path)
    else:
        logging.info("Syntax checking failed.")
        # compilation_correct(err_reason, file_path)
