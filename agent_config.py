import os
import time
import globals
from enum import Enum, auto

# System configuration
# This forces the output to be unbuffered
os.environ['PYTHONUNBUFFERED'] = '1'

class State(Enum):
    INITIAL = auto()
    GENERATE_DESIGN = auto()
    VERIFY_SYNTAX = auto()
    RUN_SIMULATION = auto()
    RUN_OPENLANE = auto()
    CORRECT_OPENLANE = auto()
    WRITE_CSV = auto()
    DONE = auto()
    ERROR = auto()

# Global variables

prj_dir = os.getcwd()

openlane_dir = os.path.join(os.path.dirname(prj_dir), "OpenLane")

max_attempts = 5

design_list = [
    "accu",
    "adder_16bit",
    "adder_32bit",
    "adder_8bit",
    "adder_pipe_64bit",
    "alu",
    "asyn_fifo",
    "calendar",
    "counter_12",
    "div_16bit",
    "edge_detect",
    "freq_div",
    "fsm",
    "JC_counter",
    "multi_16bit",
    "multi_booth_8bit",
    "multi_pipe_4bit", #16
    "multi_pipe_8bit",
    "parallel2serial",
    "pe",
    "pulse_detect",
    "radix2_div",
    "RAM",
    "right_shifter",
    "serial2parallel",
    "signal_generator",
    "synchronizer",
    "traffic_light",
    "width_8to16"]

# ///// WORKING SESSION /////
design_name = design_list[16]

globals.agent_step = State.INITIAL

gs_title = "ppa_metrics_enhance"

globals.timestamp_tag = ""

model = 'Deepseek_performance' # Represent as the parent folder for holding artifacts.

prompt_version = 1

# ///// WORKING SESSION /////

benchmark_design_path = os.path.join(prj_dir, "Dataset", design_name, "design_description.txt")

design_folder_path = os.path.join(prj_dir, model, design_name)

design_path = os.path.join(prj_dir, model, design_name, f"{design_name}.v")

tb_path = os.path.join(prj_dir, "Dataset", design_name, "testbench.v")

out_conversation_path = os.path.join(prj_dir, model, design_name, f"{design_name}_conversation.txt")

# success log after go through done state
log_path = os.path.join(design_folder_path, "flow.log")

# failure log for compilation and simulation
# For 'error' state, only record conversation
fail_log_path = os.path.join(design_folder_path, "error.log")

# Openlane log
ol_log_path = os.path.join(design_folder_path, "openlane.log")

# Ol path error extract
ol_path_extracted = os.path.join(design_folder_path, "opath_extract.log")

# Summary openlane log
ol_summary_path = os.path.join(design_folder_path, "openlane_llmaid_log_summary.log")

ol_designname_folder = os.path.join(openlane_dir, model, design_name, f"{design_name}.v")

ol_source_mount = os.path.join(openlane_dir, "designs")

ol_json_path = os.path.join(ol_source_mount, design_name, "config.json")

ol_target_mount = os.path.join(prj_dir, "designs_mounted")

ol_raw_log = os.path.join(prj_dir, "Openlane", model, f"{design_name}_raw_log.txt")


log = []

def show_log(info: str):
    log.append(info)
    print(info)


def save_log():
    
    with open(log_path, 'a') as file:
        content = "\n".join(log)
        file.write(content)

def save_failure_int_log(info: str):
    with open(fail_log_path, 'a') as file:
        file.write(f"{info}\n")


def agent_gen_timestamp():
    
    # Get the local time structure
    current_time = time.localtime()
    # Format the time structure into a string
    timestamp = time.strftime("%Y.%m.%d_%H.%M.%S", current_time)
    custom_run_tag = f"RUN_{timestamp}"
    # custom_run_tag = "RUN_2026.04.15_15.28.30"
    return custom_run_tag

