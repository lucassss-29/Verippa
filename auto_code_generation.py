# Please install OpenAI SDK first: `pip3 install openai`
import os

import test
from openai import OpenAI, RateLimitError, InternalServerError

import os
from dotenv import load_dotenv
from project_prompt import get_performance_prompt, get_sys_testbench_prompt, get_usr_design_requirements
from text_processing import clean_testbench_file, clean_verilog_file
from agent_config import design_name, model, design_path, tb_path, save_failure_int_log, ol_json_path, ol_path_extracted, ol_log_path, benchmark_design_path, ol_summary_path, show_log, prj_dir, prompt_version
from handle_testbench import check_tb_include_external


load_dotenv()  # takes environment variables from .env.

client = OpenAI(api_key=os.getenv('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

set_temper = 0.2

ext_content = ""

TB_INCLUSION = True

def llm_generation(is_design: str, msg, attempt: int, phase: str):

    # auto_temper_increasement(attempt)
    try:
        stream = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=msg,
            temperature=set_temper,
            stream=True
        )

        has_started_content = False
        has_started_reasoning = False

        full_answer = []

        for chunk in stream:

            delta = chunk.choices[0].delta
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:

                if not has_started_reasoning:
                    print("\n--- BEGIN REASONING ---")
                    has_started_reasoning = True

                print(delta.reasoning_content, end="", flush=True)

            if delta.content:
                if not has_started_content:
                    print("\n\n--- BEGIN FINAL ANSWER ---")
                    has_started_content = True

                answer_piece = delta.content

                print(answer_piece, end="", flush=True)
                full_answer.append(answer_piece)

        print("\n--- END OF RESPONSE ---")  

        complete_text = "".join(full_answer)

        msg.append({"role": "assistant", "content": complete_text})

    except InternalServerError:
        print("Exception: Server overloaded. Reasoning models are busy.")

    except RateLimitError:
        return "Exception: You are being rate-limited. (Wait a bit or check your credits)"
    
    except Exception as e:

        return f"Error during thinking phase: {e}"

    model_folder = os.path.join("./", model)

    if not os.path.exists(model_folder):

        #  Create folder with name followed by LLM model
        os.mkdir(model_folder)

    design_folder = os.path.join(model_folder, design_name)

    prefix = f"{phase}_attempt_{attempt}"

    if is_design == "design":

        # Only need prefix for raw data
        at_filename = f"generated_{design_name}_{prefix}.v" 

        extracted_filename = os.path.join(design_folder, f"{design_name}.v")

    else:

        at_filename = f"generated_{design_name}_tb_{prefix}.v"

        extracted_filename = os.path.join(design_folder, f"{design_name}_tb.v")

    # Create a subfolder for the design
    if not os.path.exists(design_folder):

        os.makedirs(design_folder, exist_ok=True)

    filename_folder = os.path.join(design_folder, at_filename)

    with open(filename_folder, 'w') as file:

        file.write(complete_text)

        print(f"\nNew file written at {filename_folder}.")

        print("\nModel is generated successfully.")

    # Extract the raw Verilog code
    if is_design == "design":

        result = clean_verilog_file(filename_folder, extracted_filename)

    else:
        result = clean_testbench_file(filename_folder, extracted_filename)

    return result


def auto_temper_increasement(no_try):

    global set_temper

    # Start increase temperature at third try
    if no_try >= 3:

        set_temper = round(set_temper + 0.1, 1)

    show_log(f"\nUpdate temperature to: {set_temper}\n")


def read_description(benchmark_design_path):
    try:
        with open(benchmark_design_path, 'r') as description_file:

            lines = description_file.readlines() 

            description = lines[2:]
            
            return str(description)
        
    except FileNotFoundError:

        print("File not found for folder")


def testbench_generation(msg):
    system_pt = get_sys_testbench_prompt(design_name)

    with open(design_path, 'r') as f:
        ds_content = f.read()

    msg.append({"role": "system", "content": system_pt})
    msg.append({"role": "user", "content": ds_content})

    result = llm_generation("testbench", msg, 0, "phase_2")

    return result

def compilation_correct(msg, err, file_path, attempt):

    phase = "phase_1"

    try:
        with open(file_path, 'r') as f:
            content = f.read()

    except Exception as e:
        print(f"Exception during correct compilation: {e}")

    fail_log = f"{phase} attempt {attempt}:\n{err}"

    save_failure_int_log(fail_log)

    # correct_sys = "Please act as an expert in synthesis design and correct the RTL design. Only provide raw code"

    correct_pt = "The design encountered with a syntax error. Here is the fault:\n" +  err + "\nBased on this, please investigate root cause and provide a solution to fix it." + get_usr_design_requirements()

    # msg.append({"role": "system", "content": correct_sys})
    msg.append({"role": "user", "content": correct_pt})

    result = llm_generation("design", msg, attempt, phase)

    return result

def simulation_correct(msg, err, attempt):

    phase = "phase_2"

    try:
        with open(tb_path, 'r') as f:
            tb_content = f.read()
        with open(design_path, 'r') as f:
            ds_content = f.read()
    except Exception as e:
        print(f"Exception during correct simulation: {e}")

    fail_log = f"{phase} attempt {attempt}:\n{err}"

    save_failure_int_log(fail_log)

    if attempt == 1:

        # Only check once  
        ext_rsl, ext_files = check_tb_include_external()

        system_role = "The design is going through the testbench running phase. Please act as an expert in Digital Verification Engineer."

        msg.append({"role": "system", "content": system_role})

        if ext_rsl:

            global ext_content

            ext_content = "\nHere are testbench inclusion files:\n"

            for ext_name in ext_files:
                ext_path = os.path.join(prj_dir, "Dataset", design_name, ext_name)

                with open(ext_path, 'r') as f:
                    ext_content += f"{ext_name} file:\n" + f.read()

    correct_pt = "\nThe design encountered error during simulation with testbench with error:\n" + err + "\Here is a corresponding testbench:\n" + tb_content + ext_content + "\n Here is a RTL design:\n" + ds_content + "\n Based on the errors, please provide with new RTL design code." + get_usr_design_requirements() 

    msg.append({"role": "user", "content": correct_pt})

    llm_generation("design", msg, attempt, phase)


def openlane_generation(msg, err_path, attempt, phase):

    err_detail = ""

    try:

        ds_description = read_description(benchmark_design_path)

        # Open openlane.log
        with open(ol_log_path) as f:

            err = f.read()

        # Error detail
        with open(err_path, 'r') as f:

            err_detail = f.read()

        with open(design_path, 'r') as f:

            ds_content = f.read()

        # Append system prompt at first try, then ignore
        if attempt == 1:

            sys_pt = "The design in going to Openlane running phase. Please act as expert in physical implementation, investigate thoroughly the issue and provide the solution. The RTL design then go again the syntax checking, testbench running and Openlane phase unitl all requirements satisfy."

            sys_pt += get_performance_prompt(prompt_version)

            msg.append({"role": "system", "content": sys_pt})

        
        correct_pt = "\nHere is the RTL description:\n" + ds_description +"\nThe code written based on description has encountered the error during running flow in OpenLane. Here is the error:\n" + err + "\Here is a detailed log:\n" + err_detail + "\n Here is a RTL design run by the flow:\n" + ds_content + "\n Based on errors, please investigate and provide with new RTL design code to fix issue." + get_usr_design_requirements() 

        msg.append({"role": "user", "content": correct_pt})

        llm_generation("design", msg, attempt, phase)

    except Exception as e:

        print(f"Exception during correct Openlane: {e}")