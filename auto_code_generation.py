# Please install OpenAI SDK first: `pip3 install openai`
import os

import test
from openai import OpenAI

import os
from dotenv import load_dotenv
from project_prompt import get_performance_prompt, get_sys_testbench_prompt, get_testbench_requirements
from text_processing import clean_testbench_file, clean_verilog_file
from agent_config import design_name, model, design_path, tb_path

load_dotenv()  # takes environment variables from .env.

client = OpenAI(api_key=os.getenv('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

def llm_generation(is_design: str, msg, attempt: int, phase: str):

    stream = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=msg,
        stream=True
    )
    full_answer =[]
    for chunk in stream:
        delta = chunk.choices[0].delta
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            print(delta.reasoning_content, end="", flush=True)
        if delta.content:
            answer_piece = delta.content
            print(answer_piece, end="", flush=True)
            full_answer.append(answer_piece)  

    complete_text = "".join(full_answer)
    msg.append({"role": "assistant", "content": complete_text})

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
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error message during correct simulation: {e}")
        
    correct_sys = "Please act as an expert in synthesis design."

    correct_pt = err + "\nBased on the error(s) shown above" + "Here is the Verilog design: \n" + content + "\nProvide only one solution to fix the issue directly without any explanation, just provide the solution. Your answer will be input for an another process, so please package it into a code block file, start file with \'module\'."

    msg.append({"role": "system", "content": correct_sys})
    msg.append({"role": "user", "content": correct_pt})


    result = llm_generation("design", msg, attempt, "phase_1")

    return result

def simulation_correct(msg, err, attempt):
    try:
        with open(tb_path, 'r') as f:
            tb_content = f.read()
        with open(design_path, 'r') as f:
            ds_content = f.read()
    except Exception as e:
        print(f"Error message during correct simulation: {e}")

    # Update new solution
    system_role = "Please act as expert in Digital Verification Engineer. Your task is to generate testbench only based on error and reference RTL design. Please investigate the root cause and provide a solution to fix the issue. Your task is to only correct the testbench code, do not change the RTL design. The testbench name should be: " + design_name + "_tb.v. While generating the testbench, please comply with the following requirements:" + get_testbench_requirements()

    correct_pt = "\nHere is the error description:\n" + err + "\nPrevious testbench content:\n" + tb_content + "\n Here is the reference RTL design content:\n" + ds_content
    msg.append({"role": "system", "content": system_role})
    msg.append({"role": "user", "content": correct_pt})

    llm_generation("testbench", msg, attempt, "phase_2")

