import os
import time
import globals
from enum import Enum, auto
import globals
import gspread
import json
from skopt.space import Real, Integer, Categorical


# System configuration
# This forces the output to be unbuffered
os.environ['PYTHONUNBUFFERED'] = '1'

class State(Enum):
    INITIAL = auto()
    GENERATE_DESIGN = auto()
    VERIFY_SYNTAX = auto()
    CORRECT_SYNTAX = auto()
    RUN_SIMULATION = auto()
    RUN_OPENLANE = auto()
    CORRECT_OPENLANE = auto()
    EXPLORATION_OPENLANE = auto()
    WRITE_CSV = auto()
    DONE = auto()
    ERROR = auto()

class BenchmarkType(Enum):
    RTLLM = auto()
    CHIPGPTV = auto()
    VERILOGEVAL = auto()

# Global variables
max_attempts = 5

# ///// WORKING SESSION /////

globals.agent_step = State.VERIFY_SYNTAX

# Constant
PPA_type = 'Performance'

gs_title = "ppa_metrics_enhance"

gs_sheet = "App_user_demo"

globals.timestamp_tag = ""

globals.exploration_tag = ""

# Represent as the parent folder for holding artifacts.
model = gs_sheet

benchmark = BenchmarkType.RTLLM
# ///// WORKING SESSION /////

design_list = [
    "accu",
    "adder_16bit",
    "adder_32bit",
    "adder_8bit",
    "adder_pipe_64bit",
    "alu",
    "asyn_fifo",
    "calendar",
    "counter_12", #8
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
    "radix2_div", #21
    "RAM",
    "right_shifter",
    "serial2parallel",
    "signal_generator",
    "synchronizer",
    "traffic_light",
    "width_8to16"] #28

# Verilog-Eval
# design_list = [
# "always_case2",
# "always_casez",
# "always_if2",
# "bugs_case",
# "circuit10", #4
# "circuit8",
# "count_clock",
# "dff16e",
# "ece241_2013_q2", #8
# "ece241_2013_q4",
# "ece241_2014_q3",
# "fsm_hdlc",
# "fsm_onehot",
# "fsm_ps2data",
# "fsm_serialdata",
# "fsm2", #15
# "fsm2s",
# "fsm3comb",
# "fsm3s",
# "gatesv",
# "gatesv100",
# "gshare", #21
# "kmap4",
# "lemmings2",
# "lemmings3",
# "lemmings4",
# "lfsr32",
# "m2014_q4k", #27
# "review2015_fancytimer",
# "review2015_fsm",
# "review2015_fsmonehot",
# "rule110",
# "thermostat",
# "timer"] #33

dimensions = []

log = []

prj_dir = os.getcwd()

openlane_dir = os.path.join(os.path.dirname(prj_dir), "OpenLane")

ol_source_mount = os.path.join(openlane_dir, "designs")

ol_target_mount = os.path.join(prj_dir, "designs_mounted")

benchmark_design_path = ""
design_folder_path = ""
design_path = ""
tb_path = ""
ol_path_extracted = ""
ol_summary_path = ""
ol_designname_folder = ""
ol_json_path = ""
ol_json_matrix = ""
ol_raw_log = ""
benchmark_folder = ""
system_role = ""
ol_expl_log = ""

def fetch_workflow_variables():

    global benchmark_design_path, design_folder_path, design_path, tb_path, ol_path_extracted, ol_summary_path, ol_designname_folder, ol_json_path, ol_raw_log, benchmark_folder, system_role, ol_json_matrix, ol_expl_log

    if globals.AI_provider.lower() == "chatgpt 5.4":
        system_role = "developer"
    
    elif globals.AI_provider.lower() == "deepseek v4 pro" or globals.AI_provider.lower() == "gemini 2.5 pro":
        system_role = "system"

    if benchmark == BenchmarkType.RTLLM:

        benchmark_folder = "Dataset"

    elif benchmark == BenchmarkType.CHIPGPTV:

        benchmark_folder = "Dataset/chipgptv/customize"

    elif benchmark == BenchmarkType.VERILOGEVAL:

        benchmark_folder = "Dataset/verilog-eval/dataset_spec-to-rtl/customize"

    benchmark_design_path = os.path.join(prj_dir, benchmark_folder, globals.design_name, "design_description.txt")

    design_folder_path = os.path.join(prj_dir, model, globals.design_name)

    if benchmark == BenchmarkType.VERILOGEVAL:

        design_path = os.path.join(prj_dir, model, globals.design_name, f"{globals.design_name}.sv")

        tb_path = os.path.join(prj_dir, benchmark_folder, globals.design_name, "testbench.sv")
    
    else:
        design_path = os.path.join(prj_dir, model, globals.design_name, f"{globals.design_name}.v")

        tb_path = os.path.join(prj_dir, benchmark_folder, globals.design_name, "testbench.v")


    globals.app_usage_dict['out_conversation_path'] = os.path.join(prj_dir, model, globals.design_name, f"{globals.design_name}_conversation.txt")

    # success log after go through done state
    globals.app_usage_dict['log_path'] = os.path.join(design_folder_path, "flow.log")

    # failure log for compilation and simulation
    # For 'error' state, only record conversation
    globals.app_usage_dict['fail_log_path'] = os.path.join(design_folder_path, "error.log")

    # Openlane log
    globals.app_usage_dict['ol_log_path'] = os.path.join(design_folder_path, "openlane.log")

    # Ol path error extract
    ol_path_extracted = os.path.join(design_folder_path, "opath_extract.log")

    # Summary openlane log
    ol_summary_path = os.path.join(design_folder_path, "openlane_llmaid_log_summary.log")

    ol_designname_folder = os.path.join(openlane_dir, model, globals.design_name, f"{globals.design_name}.v")

    ol_json_path = os.path.join(ol_source_mount, globals.design_name, "config.json")

    ol_json_matrix = os.path.join(openlane_dir, "explore_matrix.json")

    ol_raw_log = os.path.join(prj_dir, "Openlane", model, f"{globals.design_name}_raw_log.txt")

    ol_expl_log = os.path.join(prj_dir, "Openlane", model, f"{globals.design_name}_expl_raw_log.txt")


def show_log(info: str):
    log.append(info)
    print(info)

def reset_log():
    global log
    log = []


def save_log():

    with open(globals.app_usage_dict['log_path'], 'a') as file:
        content = "\n".join(log)
        file.write(content)

def save_failure_int_log(info: str):

    if not os.path.exists(os.path.dirname(globals.app_usage_dict['fail_log_path'])):

        os.makedirs(os.path.dirname(globals.app_usage_dict['fail_log_path']))

    with open(globals.app_usage_dict['fail_log_path'], 'a') as file:
        
        file.write(f"{info}\n")


def agent_gen_timestamp(is_expl: bool):
    
    # Get the local time structure
    current_time = time.localtime()
    # Format the time structure into a string
    timestamp = time.strftime("%Y.%m.%d_%H.%M.%S", current_time)

    if is_expl:
        custom_run_tag = f"RUN_EX_{timestamp}" 
    else:
        custom_run_tag = f"RUN_{timestamp}"

    # custom_run_tag = "RUN_2026.04.15_15.28.30"
    return custom_run_tag

def authen_gsheet(title, sh_name):

    gc = gspread.service_account(filename=f'{prj_dir}/Gsheet/credentials.json')

    sh = gc.open(title)

    sheet = sh.worksheet(sh_name)

    return sheet


def update_dimensions_param():

    if globals.ol_update_dimension == False:

        global dimensions 

        show_log("Update Openlane params dimension: clock, core, pl, strategy")

        with open(ol_json_path, "r") as f:
            data = json.load(f)

        current_period = data.get("CLOCK_PERIOD")

        # Optional configuration in default file
        current_util = data.get("FP_CORE_UTIL")

        if current_util is not None:

            if current_util < 5:
                MIN_UTIL = 0
            else:
                MIN_UTIL = current_util - 5

            MAX_UTIL = current_util
        else:
            MIN_UTIL = 35
            MAX_UTIL = 45

        # dimensions = [
        #     Real(current_period - 6, current_period, name='CLOCK_PERIOD'),
        #     Integer(MIN_UTIL, MAX_UTIL, name='FP_CORE_UTIL'),
        #     Real(0.40, 0.60, name='PL_TARGET_DENSITY'),
        #     Categorical(["DELAY 0", "DELAY 2", "DELAY 4"], name='SYNTH_STRATEGY')]
        
        # Balance PPA
        dimensions = [
            Real(current_period - 2.5, current_period - 0.5, name='CLOCK_PERIOD'),
            Integer(MIN_UTIL, MAX_UTIL, name='FP_CORE_UTIL'),
            Real(0.40, 0.55, name='PL_TARGET_DENSITY'),
            Categorical(["DELAY 2", "DELAY 4", "AREA 0", "AREA 3"], name='SYNTH_STRATEGY')
        ]
        
        # Done updating
        globals.ol_update_dimension = True
    else:
        pass