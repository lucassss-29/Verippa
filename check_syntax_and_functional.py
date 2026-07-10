import os
import subprocess
import time
import logging
from kill_process import kill_process_by_name
import agent_config
import globals

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

    if not os.path.exists(agent_config.design_path):

        err_msg = "File not found"

        return False, err_msg
    
    else:
        # -t null tells iverilog to check syntax without generating output code

        arti_path = os.path.join(agent_config.prj_dir, "compilation_out")

        if not os.path.exists(arti_path):

            os.mkdir(arti_path)

        cmd = f"{std_cmd} -o ./compilation_out/temp {agent_config.design_path}"

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:

                # logging.info(result.stdout)
                return True, None
            
            else:

                logging.error(result.stderr)

                err_msg = str(result.stderr)

                return False, err_msg
            
        except Exception as e:

            print(f"Exception Command failed with return code {e}")
            
            return False, e

def run_testbench():
    """
    Compiles and runs a Verilog testbench using iverilog and vvp.
    Returns the simulation output and error messages.
    """
    sim_arti = os.path.join(agent_config.prj_dir, "simulation_out")

    if not os.path.exists(sim_arti):

        os.mkdir(sim_arti)

    output_vvp_path = os.path.join(sim_arti, f"{globals.design_name}_test.vvp")

    # Compilation command
    if agent_config.benchmark == agent_config.BenchmarkType.RTLLM:
        compl_cmd = f"{std_cmd} -o {output_vvp_path} {agent_config.design_path} {agent_config.tb_path}"
    
    elif agent_config.benchmark == agent_config.BenchmarkType.VERILOGEVAL:
        
        # Due to the testbench called 2 module to verified, so include additional verified module.
        verified_design_path = os.path.join(agent_config.prj_dir,agent_config.benchmark_folder, globals.design_name, f"verified_{globals.design_name}.sv")

        compl_cmd = f"{std_cmd} -o {output_vvp_path} {agent_config.design_path} {verified_design_path} {agent_config.tb_path}"

    sim_cmd = f"vvp {output_vvp_path}"

    run_cmd = compl_cmd + " && " + sim_cmd

    error_match = False
    
    #  start_new_session=True ensures that the process is started in a new session, allowing us to kill the entire process group if needed
    process = subprocess.Popen(run_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)

    try:

        #  Wait for the process to complete with a timeout
        stdout, stderr = process.communicate(timeout=20)

        # Check if VerilogEval benchmark is being used
        if agent_config.benchmark == agent_config.BenchmarkType.VERILOGEVAL:

            if "Mismatches: 0" in stdout:
                pass
            else:
                error_match = True

        else:

            if "failed" in stdout.lower() or "failed" in stderr.lower() or "error" in stdout.lower() or "error" in stderr.lower() or "failures" in stdout.lower() or "failures" in stderr.lower():

                error_match = True

        if process.returncode != 0 or error_match:

            error_msg = f"Simulation failed: {stdout}\n{stderr}"

            logging.error(error_msg)

            return False, error_msg
        
        else:

            logging.info(stdout)

            logging.info("Simulation completed successfully.")

            return True, None
        
    except subprocess.TimeoutExpired as te:

        #  Kill the entire process group to ensure all child processes are terminated
        kill_process_by_name("vvp")

        # Check if the process is still running
        while process.poll() is None:

            print("Process is still running...")

            time.sleep(1) # Add a small delay to avoid using too much CPU

        print(f"Exception finished with return code: {process.returncode}")

        error_msg = f"Simulation process killed due to timeout: {te}."

        logging.error(error_msg)

        return False, error_msg
    
    except Exception as e:

        error_msg = f"Unexpected error occurred: {e}"

        logging.error(error_msg)

        return False, error_msg



# run_testbench()