import os
import sys

from openai import OpenAI, RateLimitError, InternalServerError

from dotenv import load_dotenv
from project_prompt import get_performance_prompt, get_sys_testbench_prompt, get_usr_design_requirements, get_area_prompt
from text_processing import clean_testbench_file, clean_verilog_file
import agent_config as ac
from handle_testbench import check_tb_include_external
import globals
from google import genai
from google.genai import types


load_dotenv()  # takes environment variables from .env.

set_temper = 0.2

# Return client

# When using Gemini
# cli = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# # System_instruction can be only added once
# # Extract system prompt, #0 system, #1 user
# instruction = get_performance_prompt(3)

# client = cli.chats.create(model='gemini-2.5-pro', config=types.GenerateContentConfig(
#         # 1. System Instruction: Define model behavior
#         system_instruction=instruction,
#         temperature=set_temper,
#         # 2. Thinking Config: Enable internal thought retrieval
#         thinking_config=types.ThinkingConfig(
#             include_thoughts=True
#         )
#     )
# )

# When using Deepseek
# client = OpenAI(api_key=os.getenv('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

# When using ChatGPT
client = OpenAI(api_key=os.getenv('CHATGPT_API_KEY'))

ext_content = ""

TB_INCLUSION = True

def llm_generation(is_design: str, msg, attempt: int, phase: str):

    # auto_temper_increasement(attempt)
    try:
        complete_text = auto_call_provider(msg, ac.AI_provider)

    except InternalServerError:
        print("Exception: Server overloaded. Reasoning models are busy.")

    except RateLimitError:
        return "Exception: You are being rate-limited. (Wait a bit or check your credits)"
    
    except Exception as e:

        return f"Exception error during thinking phase: {e}"

    model_folder = os.path.join(ac.prj_dir, ac.model)

    if not os.path.exists(model_folder):

        #  Create folder with name followed by LLM model
        os.mkdir(model_folder)

    design_folder = os.path.join(model_folder, globals.design_name)

    prefix = f"{phase}_attempt_{attempt}"

    if is_design == "design":

        if ac.benchmark == ac.BenchmarkType.RTLLM:
            at_filename = f"generated_{globals.design_name}_{prefix}.v" 

            extracted_filename = os.path.join(design_folder, f"{globals.design_name}.v")
        elif ac.benchmark == ac.BenchmarkType.VERILOGEVAL:
            at_filename = f"generated_{globals.design_name}_{prefix}.sv" 

            extracted_filename = os.path.join(design_folder, f"{globals.design_name}.sv")


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


# Return full response, this function will add user message (no system message) and call server to generate response
def auto_call_provider(msg, provider):

    full_response_text = ""

    if provider.lower() == "gemini":

        has_started_content = False
        has_started_reasoning = False
        full_response_text = ""
        last_chunk = None

        # Use send_message_stream instead of send_message
        response_stream = client.send_message_stream(msg[-1]['content'])

        try:
            for chunk in response_stream:

                for part in chunk.candidates[0].content.parts:

                    if part.text:
                        if part.thought:

                            if not has_started_reasoning:
                                print("\n--- BEGIN REASONING ---\n")

                                has_started_reasoning = True

                            print(part.text, end="", flush=True)

                        else:

                            if not has_started_content:
                                print("\n\n--- BEGIN FINAL ANSWER ---\n")

                                has_started_content = True

                            # When it switches to final text, reset or add a separator
                            print(part.text, end="", flush=True)

                            full_response_text += part.text

                # The very last 'chunk' will contain the metadata        #    
                last_chunk = chunk

            msg.append({"role": "model", "content": full_response_text})
                
        except Exception as e:
            print("Exception error during streaming:", e)

        if last_chunk and last_chunk.usage_metadata:

            turn_total = last_chunk.usage_metadata.total_token_count

            print(f'\nConsumed design generation prompt: {turn_total}\n')

            globals.running_total_tokens += turn_total


    elif provider.lower() == "deepseek":

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
                    print("\n--- BEGIN REASONING ---\n")
                    has_started_reasoning = True

                print(delta.reasoning_content, end="", flush=True)

            if delta.content:
                if not has_started_content:
                    print("\n\n--- BEGIN FINAL ANSWER ---\n")
                    has_started_content = True

                answer_piece = delta.content

                print(answer_piece, end="", flush=True)
                full_answer.append(answer_piece)

        print("\n--- END OF RESPONSE ---\n")

        full_response_text = "".join(full_answer)

        msg.append({"role": "assistant", "content": full_response_text})

    elif provider.lower() == "chatgpt":

        full_answer = []

        with client.responses.stream(
            model="gpt-5.4",
            input=msg,
            reasoning={"effort": "medium"}
            # stream=True
            # temperature=set_temper # Gpt5.4 not support temperature
        ) as stream:

            # GPT5 not support showing 
            for event in stream:

                if event.type == "response.output_item.added" and event.item.type == "reasoning":
                    print("\nModel is initializing deep reasoning...\n")

                elif event.type == "response.output_text.delta":
                    print(event.delta, end="", flush=True)
                    full_answer.append(event.delta)

        response = stream.get_final_response()

        globals.running_total_tokens += response.usage.total_tokens

        full_response_text = "".join(full_answer)

        msg.append({"role": "assistant", "content": full_response_text})

    else:
        return "Invalid provider selected."

    return full_response_text


def auto_temper_increasement(no_try):

    global set_temper

    # Start increase temperature at third try
    if no_try >= 3:

        set_temper = round(set_temper + 0.1, 1)

    ac.show_log(f"\nUpdate temperature to: {set_temper}\n")


def read_description(benchmark_design_path):
    try:
        with open(benchmark_design_path, 'r') as description_file:

            lines = description_file.readlines() 

            # description = lines[2:]
            description = lines[0:]
            
            return str(description)
        
    except FileNotFoundError:

        print("File not found for folder")


def compilation_correct(msg, err, file_path, attempt):

    phase = "phase_1"

    try:
        with open(file_path, 'r') as f:
            content = f.read()

    except Exception as e:
        print(f"Exception during correct compilation: {e}")

    fail_log = f"{phase} attempt {attempt}:\n{err}"

    ac.save_failure_int_log(fail_log)

    # correct_sys = "Please act as an expert in synthesis design and correct the RTL design. Only provide raw code"

    correct_pt = "The design encountered with a syntax error. Here is the fault:\n" +  err + "\nBased on this, please investigate root cause and provide a solution to fix it." + get_usr_design_requirements()

    # msg.append({"role": "system", "content": correct_sys})
    msg.append({"role": "user", "content": correct_pt})

    result = llm_generation("design", msg, attempt, phase)

    return result

def simulation_correct(msg, err, attempt):

    phase = "phase_2"

    try:
        with open(ac.tb_path, 'r') as f:
            tb_content = f.read()
        with open(ac.design_path, 'r') as f:
            ds_content = f.read()
    except Exception as e:
        print(f"Exception during correct simulation: {e}")

    fail_log = f"{phase} attempt {attempt}:\n\n{err}"

    ac.save_failure_int_log(fail_log)

    if attempt == 1:

        # Only check once  
        ext_rsl, ext_files = check_tb_include_external()

        system_role = "The design is going through the testbench running phase. Please act as an expert in Digital Verification Engineer."

        msg.append({"role": ac.system_role, "content": system_role})

        if ext_rsl:

            global ext_content

            ext_content = "\nHere are testbench inclusion files:\n"

            for ext_name in ext_files:
                ext_path = os.path.join(ac.prj_dir, ac.benchmark_folder, globals.design_name, ext_name)

                with open(ext_path, 'r') as f:
                    ext_content += f"{ext_name} file:\n" + f.read()

    correct_pt = "\nThe design encountered error during simulation with testbench with error:\n" + err + "\Here is a corresponding testbench:\n" + tb_content + ext_content + "\n Here is a RTL design:\n" + ds_content + "\n Based on the errors, please provide with new RTL design code." + get_usr_design_requirements() 

    msg.append({"role": "user", "content": correct_pt})

    llm_generation("design", msg, attempt, phase)


def openlane_generation(msg, err_path, attempt, phase):

    err_detail = ""

    try:

        ds_description = read_description(ac.benchmark_design_path)

        # Open openlane.log
        with open(ac.ol_log_path) as f:

            err = f.read()

        # Error detail
        with open(err_path, 'r') as f:

            err_detail = f.read()

        with open(ac.design_path, 'r') as f:

            ds_content = f.read()

        # Append system prompt at first try, then ignore
        if attempt == 1:

            sys_pt = "The design in going to Openlane running phase. Please act as expert in physical implementation, investigate thoroughly the issue and provide the solution. The RTL design then go again the syntax checking, testbench running and Openlane phase unitl all requirements satisfy."

            if ac.PPA_type == 'Performance':
            
                sys_pt += get_performance_prompt(ac.prompt_version)
            
            elif ac.PPA_type == 'Area':

                sys_pt += get_area_prompt(ac.prompt_version)

            msg.append({"role": ac.system_role, "content": sys_pt})

            correct_pt = "\nHere is the RTL description:\n" + ds_description +"\nThe code written based on description has encountered the error during running flow in OpenLane. Here is the error:\n" + err + "\Here is a detailed log:\n" + err_detail + "\n Here is a RTL design run by the flow:\n" + ds_content + "\n Based on errors, please investigate and provide with new RTL design code to fix issue." + get_usr_design_requirements() 

        else:
            
            correct_pt = "\n The design continue encountered issue during running OpenLane flow. Here is the error:\n" + err + "\Here is a detailed log:\n" + err_detail + "\n Here is a RTL design run by the flow:\n" + ds_content + "\n Based on errors, please investigate and provide with new RTL design code to fix issue." + get_usr_design_requirements()

        msg.append({"role": "user", "content": correct_pt})

        llm_generation("design", msg, attempt, phase)

    except Exception as e:

        print(f"Exception during Openlane generation: {e}")

# llm_generation("design", "", 1, 1)

# auto_call_provider([], ac.AI_provider)
