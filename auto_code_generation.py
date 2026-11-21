import logging
import os
from socket import timeout
from sqlite3 import connect
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
import itertools
import time
from chat_status_manager import update_workflow_status
import streamlit as st

load_dotenv()  # takes environment variables from .env.

set_temper = 0.2

## DEBUG
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

# Return client

class ChatgptAdapter:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('CHATGPT_API_KEY'))

    def generate(self, msg):
        return self.client.responses.create(
            model="gpt-5.4",
            reasoning={
                "effort": "medium",
                "summary": "auto"},
            input=msg,
            stream=True
        )


class DeepseekAdapter:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('DEEPSEEK_API_KEY'), base_url='https://api.deepseek.com',
        timeout=10.0)

    def generate(self, msg):
        
        try:
            stream = self.client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=msg,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}},
                stream=True,
                stream_options={"include_usage": True},
                max_tokens=393216 # 384k output
            )

            return stream
        
        except Exception as e:
            if hasattr(e, "response") and e.response is not None:
                print("Status:", e.response.status_code)
                print("Body:", e.response.text)   
            raise
    
class GeminiAdapter:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

        instruction = get_performance_prompt(globals.prompt_version)

        self.chat = self.client.chats.create(
            model='gemini-2.5-pro',
            config=types.GenerateContentConfig(
                system_instruction=instruction,
                thinking_config=types.ThinkingConfig(include_thoughts=True)
            )
        )

    def generate(self, prompt):

        return self.chat.send_message_stream(prompt)


LLM_CLIENTS = {
    'chatgpt': ChatgptAdapter(),
    'deepseek': DeepseekAdapter(),
    'gemini': GeminiAdapter()
}

ext_content = ""

TB_INCLUSION = True

def llm_generation(is_design: str, msg, attempt: int, phase: str):

    # auto_temper_increasement(attempt)
    try:
        complete_text = auto_call_provider(msg, globals.AI_provider)

    except InternalServerError:
        print("Exception: Server overloaded. Reasoning models are busy.")

    except RateLimitError:
        return "Exception: You are being rate-limited. (Wait a bit or check your credits)"
    
    except Exception as e:

        return f"Exception error during thinking phase: {e}"

    model_folder = os.path.join(ac.prj_dir, globals.local_folder)

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

    if provider.lower() == "gemini 2.5 pro":
        
        full_answer = []
        
        info_dict = {'last_chunk_info': None}
        last_chunk = info_dict['last_chunk_info']

        stream_response = LLM_CLIENTS['gemini'].generate(msg[-1]['content'])

        try:
            
            stream_instance = stream_reasoning_streamlitApp(stream_response, globals.AI_provider, full_answer, info_dict)

            ui_agent = st.session_state.ui_elements

            update_workflow_status(ui_agent, label='Reasoning...', message=stream_instance)

            full_response_text = "".join(full_answer)

            last_chunk = info_dict['last_chunk_info']

            print('\nFull response: \n', full_response_text)

            msg.append({"role": "model", "content": full_response_text})
                
        except Exception as e:
            print("Exception error during streaming:", e)

        if last_chunk and last_chunk.usage_metadata:

            turn_total = last_chunk.usage_metadata.total_token_count

            print(f'\nConsumed design generation prompt: {turn_total}\n')

            globals.running_total_tokens += turn_total


    elif provider.lower() == 'deepseek v4 pro':

        stream_response = LLM_CLIENTS['deepseek'].generate(msg)

        full_answer = []

        stream_instance = stream_reasoning_streamlitApp(stream_response, globals.AI_provider, full_answer)

        ui_agent = st.session_state.ui_elements

        update_workflow_status(ui_agent, label='Reasoning...', message=stream_instance)

        print("\n--- END OF RESPONSE ---\n")

        full_response_text = "".join(full_answer)

        msg.append({"role": "assistant", "content": full_response_text})


    elif provider.lower() == "chatgpt 5.4":

        full_answer = []

        stream_response = LLM_CLIENTS["chatgpt"].generate(msg)

        yield_stream, token_stream = itertools.tee(stream_response, 2)

        stream_instance = stream_reasoning_streamlitApp(yield_stream, globals.AI_provider, full_answer)

        ui_agent = st.session_state.ui_elements

        update_workflow_status(ui_agent, label='Reasoning...', message=stream_instance)

        full_response_text = "".join(full_answer)

        msg.append({"role": "assistant", "content": full_response_text})

        for chunk in token_stream:
            if hasattr(chunk, 'usage') and chunk.usage is not None:
                globals.running_total_tokens += chunk.usage.total_tokens


    else:
        return "Invalid provider selected."

    return full_response_text

# Purpose: for app streamlit
def stream_reasoning_streamlitApp(stream_object, provider, answer_ls, info_dt=None):

    if provider.lower() == "gemini 2.5 pro":

        has_started_content = False
        has_started_reasoning = False

        for chunk in stream_object:

                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:


                    for part in chunk.candidates[0].content.parts:
                        
                        token = ''

                        if part.text:
                            if part.thought:

                                if not has_started_reasoning:
                                    print("\n--- BEGIN REASONING ---\n")

                                    has_started_reasoning = True

                                print(part.text, end="", flush=True)

                                token = part.text

                            else:

                                if not has_started_content:
                                    print("\n\n--- BEGIN FINAL ANSWER ---\n")

                                    has_started_content = True

                                # When it switches to final text, reset or add a separator
                                print(part.text, end="", flush=True)

                                token = part.text

                                answer_ls.append(part.text)

                        yield token

                # The very last 'chunk' will contain the metadata
                info_dt['last_chunk_info'] = chunk


    elif provider.lower() == 'deepseek v4 pro':

        has_started_content = False
        has_started_reasoning = False

        try:

            # Network stream, not list
            for chunk in stream_object:

                last_successful_chunk = chunk
                
                token = ''

                if hasattr(chunk, 'usage') and chunk.usage is not None:

                    globals.running_total_tokens += chunk.usage.total_tokens

                if not chunk.choices:

                    print('EMPTY')
                    continue # Skip to prevent the code from hanging

                delta = chunk.choices[0].delta
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:

                    if not has_started_reasoning:
                        print("\n--- BEGIN REASONING ---\n")
                        has_started_reasoning = True

                    # Save time
                    print(delta.reasoning_content, end="", flush=True)

                    token = delta.reasoning_content

                elif delta.content:
                    if not has_started_content:
                        print("\n\n--- BEGIN FINAL ANSWER ---\n")
                        has_started_content = True

                    answer_piece = delta.content

                    token = delta.content

                    print(answer_piece, end="", flush=True)

                    answer_ls.append(answer_piece)

                if token:

                    yield token

                    # time.sleep(0.01)

        except GeneratorExit:

            print('Stream was cut off in the middle')

            if last_successful_chunk:

                print(f'Last chunk received before failure: {last_successful_chunk}')

        except Exception as e:

            print(f'[CODE] Standard networking exception: {e}')


    elif provider.lower() == "chatgpt 5.4":

        for event in stream_object:

            if event.type == "response.output_item.added" and event.item.type == "reasoning":
                print("\nModel is initializing deep reasoning...\n")

            elif event.type == "response.reasoning_summary_text.delta":
                print(event.delta, end="", flush=True)

                yield event.delta

            elif event.type == "response.output_text.delta":
                print(event.delta, end="", flush=True)

                answer_ls.append(event.delta)
                yield event.delta


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

        # ds_description = read_description(ac.benchmark_design_path)
        ds_description = globals.design_description

        # Open openlane.log
        with open(globals.app_usage_dict['ol_log_path']) as f:

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
            
                sys_pt += get_performance_prompt(globals.prompt_version)
            
            elif ac.PPA_type == 'Area':

                sys_pt += get_area_prompt(globals.prompt_version)

            msg.append({"role": ac.system_role, "content": sys_pt})

            correct_pt = "\nHere is the RTL description:\n" + ds_description +"\nThe code written based on description has encountered the error during running flow in OpenLane. Here is the error:\n" + err + "\Here is a detailed log:\n" + err_detail + "\n Here is a RTL design run by the flow:\n" + ds_content + "\n Based on errors, please investigate and provide with new RTL design code to fix issue." + get_usr_design_requirements() 

        else:
            
            correct_pt = "\n The design continue encountered issue during running OpenLane flow. Here is the error:\n" + err + "\Here is a detailed log:\n" + err_detail + "\n Here is a RTL design run by the flow:\n" + ds_content + "\n Based on errors, please investigate and provide with new RTL design code to fix issue." + get_usr_design_requirements()

        msg.append({"role": "user", "content": correct_pt})

        llm_generation("design", msg, attempt, phase)

    except Exception as e:

        print(f"Exception during Openlane generation: {e}")

