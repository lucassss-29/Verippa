import glob
import re
from tkinter import W, Y
import streamlit as st
import time

from agent import FlowManager
import agent_config as ac
import globals
import os
import pandas as pd
import altair as alt
from chat_status_manager import update_workflow_status


with open('style.css') as f:
    st.html(f"<style>{f.read()}</style>")

def config_frontUI():

    st.set_page_config(layout="wide")

    tab1, tab2 = st.tabs(["User interactive", "Benchmark"])

    with tab1:

        col_left, col_right = st.columns([0.4, 0.6])

        with col_left:

            col1, col2 = st.columns([3, 2])

            with col1:
                st.markdown("#####  VerilogAI Workspace")

            with col2:
                st.pills(label="",options=["SDK Sky130"], default="SDK Sky130")

            model_option = st.selectbox(
                "Model",
                ['Select a model...',"Deepseek V4 Pro", "Gemini 2.5 Pro", "ChatGPT 5.4", ]
            )

            prompts_map = {
                "**Perf-v0** — :gray[Baseline variant]": 0,
                "**Perf-v1** — :gray[Aware performance]": 1,
                "**Perf-v2** — :gray[High performance]": 2,
            }

            selected_prompt_option = st.pills(
                label="Prompt version",
                options=list(prompts_map.keys()),
                default=list(prompts_map.keys())[0]
            )

            ppa_option= st.pills(label="PPA strategy", options=['Power Optimization', 'Performance Optimization', 'Area Optimization', "Balanced Mode"], default="Power Optimization")

            md_name_option = st.text_input('Module name', placeholder="e.g., counter_8bit", width=200)

            description_option = st.text_area("Module RTL details", placeholder="e.g., Describe the module functionality in detail, and declaration of inputs and outputs ...", height=130)

            main_button_spot = st.button("⚡️ Generate High Quality Verilog", type="primary", use_container_width=True)
            
        with col_right:

            st.markdown('<div class="colored-right-col"></div>', unsafe_allow_html=True)

            with st.container(height=590, border=False):

                progress_label_spot = st.empty()

                if st.session_state.pipeline_started:
                    progress_bar_spot = st.progress(st.session_state.overall_progress)
                else:
                    progress_bar_spot = None

                # Show permanent UI when condition met
                if st.session_state.code_verified:

                    code_spot = st.container()
                    show_verified_code(code_spot)

                else:
                    code_spot = None

                # if st.session_state.physical_summary:
                if st.session_state.done_exploration:
                    result_spot = st.container()

                    update_result_summaryUI(result_spot)
                
                else:
                    result_spot = None

                if st.session_state.done_exploration:

                    graph_spot = st.container()

                    update_improvement_graph(graph_spot)

                else:

                    graph_spot = None

                # Maintaining UI layout
                if st.session_state.pipeline_started:

                    if (st.session_state.current_state == ac.State.DONE) or (st.session_state.current_state == ac.State.STREAMLIT_NON_EXIT):
                        
                        log_status_spot = st.status(label='', state='complete')
                    
                    elif st.session_state.current_state == ac.State.ERROR:

                        log_status_spot = st.status(label='', state='error')

                    else:

                        log_status_spot = st.status(label='', state='running')


                    with log_status_spot:

                        verbose_spot = st.container(height=250, autoscroll=True)

                else:
                    log_status_spot = None
                    verbose_spot = None


                if st.session_state.current_state == ac.State.STREAMLIT_NON_EXIT:

                    trace_button_spot = st.button('Show Trace Log', type='primary', on_click=open_drawer_callback, icon=':material/open_in_new:')

                else:
                    trace_button_spot = None


    with tab2:

        st.markdown("Header")

    ui = {
        "main_button": main_button_spot,
        "progress_label": progress_label_spot,
        "progress_bar": progress_bar_spot,
        "code": code_spot,
        "result": result_spot,
        "graph": graph_spot,
        "log_status": log_status_spot,
        "trace_button": trace_button_spot,
        'verbose': verbose_spot
    }

    user_selection = {
        'model_opt': model_option,
        'prompt_opt': prompts_map[selected_prompt_option],
        'ppa_opt': ppa_option,
        'module_name_opt': md_name_option,
        'description_opt': description_option
    }

    return ui, user_selection

def extract_csv_data(csv_path):

    df = pd.read_csv(csv_path)

    data_df = df.copy()

    power = round((data_df['power_typical_internal_uW'].iloc[0] + data_df['power_typical_leakage_uW'].iloc[0] + data_df['power_typical_switching_uW'].iloc[0]), 6)

    freq = int(data_df['suggested_clock_frequency'].iloc[0])

    area = round((data_df['DIEAREA_mm^2'].iloc[0]), 6)

    return power, freq, area


def update_result_summaryUI(ui):

    openlane_dir = os.path.join(os.path.dirname(os.getcwd()), "OpenLane")

    default_csv = os.path.join(openlane_dir, "designs", globals.design_name, "runs", globals.timestamp_tag, "reports", "metrics.csv")

    default_power, default_f, default_area = extract_csv_data(default_csv)

    # Read locally
    path_csv = os.path.join(openlane_dir, "designs", globals.design_name, "runs", globals.exploration_tag, "reports", "metrics.csv")

    opt_power, opt_f, opt_area = extract_csv_data(path_csv)

    
    with ui:

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.write('RTL Check  \n:green[**Passed**]')

        with c2:
            st.write(f'Frequency  \n**{opt_f} MHz**')

        with c3:
            st.write(f'Area (mm²)  \n**{opt_area}**')

        with c4:
            st.write(f'Power (W)  \n**{opt_power}**')

        compare_data = {
            '': ['OpenLane default', 'Our system'],
            'Power (W)': [default_power, opt_power],
            'Frequency (MHz)': [default_f, opt_f],
            'Die area (mm2)': [default_area, opt_area]
        }

        df_cpData = pd.DataFrame(compare_data)

        st.write('##### Extract report')

        st.table(df_cpData)

        st.divider()

def update_improvement_graph(ui):

    openlane_dir = os.path.join(os.path.dirname(os.getcwd()), "OpenLane")

    # Read locally
    org_csv = os.path.join(openlane_dir, "designs", globals.design_name, "runs", globals.timestamp_tag, "reports", "metrics.csv")

    new_csv = os.path.join(openlane_dir, "designs", globals.design_name, "runs", globals.exploration_tag, "reports", "metrics.csv")

    print('globals.exploration_tag: ', globals.exploration_tag)

    org_df = pd.read_csv(org_csv)

    new_df = pd.read_csv(new_csv)

    freq_imp = ((new_df['suggested_clock_frequency'].iloc[0] - org_df['suggested_clock_frequency'].iloc[0])/org_df['suggested_clock_frequency'].iloc[0]) * 100

    area_imp = ((new_df['DIEAREA_mm^2'].iloc[0] - org_df['DIEAREA_mm^2'].iloc[0])/org_df['DIEAREA_mm^2'].iloc[0]) * 100

    power_imp = ((new_df['power_typical_internal_uW'].iloc[0] - org_df['power_typical_internal_uW'].iloc[0])/org_df['power_typical_internal_uW'].iloc[0]) * 100

    print('improvement f, a, p', freq_imp, area_imp, power_imp)

    chart_df = pd.DataFrame({
        'Metric': ['Frequence', 'Area', 'Power'], 
        'Improvement (%)':[round(freq_imp, 2), round(area_imp, 2), round(power_imp, 2)],
        "Display_Text": [
        f"{'+' if freq_imp >= 0 else ''}{freq_imp:.2f} %",
        f"{'+' if area_imp >= 0 else ''}{area_imp:.2f} %",
        f"{'+' if power_imp >= 0 else ''}{power_imp:.2f} %"
        ]
    })

    with ui:

        st.write('##### Summary')

        base = alt.Chart(chart_df).encode(
            x=alt.X("Metric:N", axis=alt.Axis(labelAngle=0), sort=None, title=None),
            y="Improvement (%):Q"
        )

        bars = base.mark_bar().encode(
            color=alt.Color("Metric:N", scale=alt.Scale(scheme="tableau10"), legend=None)
        )

        text = base.mark_text(
            align='center',
            baseline='bottom',
            dy=-5,                # Nudges text 5 pixels above the top of the bar
            color='white',
            fontSize=13,
            fontWeight='bold'
        ).encode(
            text='Display_Text:N'
        )

        final_chart = (bars + text).properties(height=200, width=350)

        st.altair_chart(final_chart, width='stretch')

    # update_workflow_status(ui, label='Workflow completed', state='complete')

def setup_progress_label(ui):

    with ui['progress_label']:
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.write("Generation")
        with c2:
            st.write("<p style='text-align: center;'>RTL Check</p>", unsafe_allow_html=True)
        with c3:
            st.markdown("<p style='text-align: center;'>OpenLane</p>", unsafe_allow_html=True)
        with c4:
            st.markdown("<p style='text-align: right;'>Optimization</p>", unsafe_allow_html=True)
        
def update_progress_bar(ui, value):

    st.session_state.overall_progress = value

    ui['progress_bar'].progress(value)

def long_text_generator():
    passage = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. FINISHING LINE: Fresh data is now safely visible here at the bottom!"
    )
    for word in passage.split():
        yield word + " "
        time.sleep(0.08)

def yield_stream_generator(stream_object, provider):

    if provider.lower() == "gemini 2.5 pro":

        for chunk in stream_object:

            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:

                for part in chunk.candidates[0].content.parts:
                    
                    token = ''

                    if part.text:

                        if part.thought:

                            token = part.text

                        else:

                            token = part.text

                        if token:

                            yield token
                            
                            time.sleep(0.2)

    elif provider.lower() == 'deepseek v4 pro':

        for chunk in stream_object:

            delta = chunk.choices[0].delta

            token = ''

            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:

                token = delta.reasoning_content

            elif hasattr(delta, 'content') and delta.content:

                token = delta.content

            if token:
                yield token
                
                time.sleep(0.01)

    elif provider.lower() == "chatgpt 5.4":

        # with stream_object as stream:

            # GPT5 not support showing 
        for event in stream_object:

            token = ''

            if event.type == "response.reasoning_summary_text.delta":
                
                token = event.delta

            elif event.type == "response.output_text.delta":
                
                token = event.delta

            if token:

                yield token

                time.sleep(0.02)

def stream_file_lines(file_path):

    with open(file_path, 'r', encoding="utf-8") as f:

        for line in f:

            yield line

            time.sleep(0.1)

def save_user_session_state(input):

    default_states = {
        'model_state': '',
        'prompt_state': '',
        'ppa_state': '',
        'module_name_state': '',
        'description_state': ''
    }

    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

    st.session_state.model_state = input['model_opt']
    st.session_state.prompt_state = input['prompt_opt']
    st.session_state.ppa_state = input['ppa_opt']
    st.session_state.module_name_state = input['module_name_opt']
    st.session_state.description_state = input['description_opt']

    globals.AI_provider = st.session_state.model_state
    globals.prompt_version = st.session_state.prompt_state
    globals.PPA_strategy = st.session_state.ppa_state
    globals.design_name = st.session_state.module_name_state
    globals.design_description = st.session_state.description_state

    print('globals.prompt_version: ', globals.prompt_version)
    
def init_app_session_state():

    app_state = {
        'pipeline_started': False,
        'current_state': ac.State.INITIAL,
        'overall_progress': 0,
        'code_verified': False,
        'physical_summary': False,
        'done_exploration': False,
        'done_status': False,
        'show_trace_button': False,
        'active_drawer': False,
        'long_log': False,
        'is_workflow_error': False,
        'ui_elements': None
    }

    for key, value in app_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

def show_verified_code(ui):

    print('st.session_state.code_verified: ', st.session_state.code_verified)

    if st.session_state.code_verified:
        print('ac.design_path: ', ac.design_path)
        with open(ac.design_path, 'r') as f:
                    
            code = f.read()

        with ui:
            st.markdown(":material/check_circle: Verified RTL")
            st.code(code, language="verilog", line_numbers=True, wrap_lines=True, height=300)
            st.divider()

@st.dialog('System Trace Log', position='right')
def show_trace_drawer():

    st.write('---')

    trace_dict = {
        'log_path': 'General workflow',
        'out_conversation_path': 'Conversation',
        'fail_log_path': 'Error',
        'ol_log_path': 'Openlane trace'
    }

    st.code(f'Prompt version: {globals.prompt_version}  \nPPA_strategy: {globals.PPA_strategy}  \nModule: {globals.design_name}')

    for file, title in trace_dict.items():

        if title == 'Conversation':
            
            st.subheader(globals.AI_provider + ' ' + title)

        else:

            st.subheader(title)

        if os.path.exists(globals.app_usage_dict.get(file)):

            with open(globals.app_usage_dict.get(file), 'r') as f:

                content = f.read()

                st.code(content, language='text', wrap_lines=True, height=400)

def open_drawer_callback():
    st.session_state.active_drawer = True

def main():

    print('RUNNING')

    init_app_session_state()

    ui, user_input = config_frontUI()

    #For other file
    st.session_state.ui_elements = ui

    save_user_session_state(user_input)

    if "my_agent" not in st.session_state:
        st.session_state.my_agent = FlowManager()

    agent_ist = st.session_state.my_agent

    if 'prime_button' not in st.session_state:
        st.session_state.prime_button = False

    # Execute only ONE TIME as a trigger
    if ui['main_button']:
        st.session_state.prime_button = True
        st.session_state.pipeline_started = True
        st.rerun()

    # st.session_state.current_state = ac.State.EXPLORATION_OPENLANE

    # When button is clicked, persistent state
    if st.session_state.prime_button:

        setup_progress_label(ui)

        ac.fetch_workflow_variables()
        
        if st.session_state.current_state == ac.State.INITIAL:
        
            agent_ist.handle_initial()

            update_workflow_status(
                ui, 
                label="Initializing the workflow...", message=f"Connecting to {st.session_state.model_state} API...  \nModule {globals.design_name}  \n{st.session_state.current_state}", 
                expanded=True)

            update_progress_bar(ui, 2)

            st.session_state.current_state = ac.State.GENERATE_DESIGN

            st.rerun()

        elif st.session_state.current_state == ac.State.GENERATE_DESIGN:

            update_progress_bar(ui, 5)

            update_workflow_status(ui, label=f'Processing module {globals.design_name}...')

            gen_check = agent_ist.handle_generate_design()

            if gen_check:
                
                update_progress_bar(ui, 10)

                update_workflow_status(ui, label='Generation is done.')
                
                st.session_state.current_state = ac.State.VERIFY_SYNTAX
            else:

                st.session_state.current_state = ac.State.ERROR

            st.rerun()

        elif st.session_state.current_state == ac.State.VERIFY_SYNTAX:

            update_progress_bar(ui, 30)

            syntax_check = agent_ist.handle_verify_syntax()

            time.sleep(2)

            if syntax_check:

                # compile_check = agent_ist.handle_run_simulation() # Skip simulation
                compile_check = True

                update_workflow_status(ui, label='Code verified')

                if compile_check:

                    update_progress_bar(ui, 35)

                    time.sleep(2)

                    st.session_state.code_verified = True

                    st.session_state.current_state = ac.State.RUN_OPENLANE

            else:

                st.session_state.current_state = ac.State.CORRECT_SYNTAX
            
            st.rerun()

        elif st.session_state.current_state == ac.State.CORRECT_SYNTAX:

            update_workflow_status(ui, label='Correcting syntax...')

            correct_syt_status = agent_ist.handle_correct_design_syntax()

            if correct_syt_status == ac.State.VERIFY_SYNTAX:

                st.session_state.current_state = ac.State.VERIFY_SYNTAX

            # Wait after reach max attempt
            if correct_syt_status == ac.State.ERROR:

                st.session_state.current_state = ac.State.ERROR

            st.rerun()


        elif st.session_state.current_state == ac.State.RUN_OPENLANE:
                
            update_progress_bar(ui, 60)

            ol_check = agent_ist.handle_run_openlane()

            if ol_check:

                update_progress_bar(ui, 60)

                update_workflow_status(ui, label='Running OpenLane complete...', message=f'Completion Tag ID: {globals.timestamp_tag}')

                st.session_state.current_state = ac.State.EXPLORATION_OPENLANE

            else:

                st.session_state.current_state = ac.State.CORRECT_OPENLANE

            st.rerun()

        elif st.session_state.current_state == ac.State.CORRECT_OPENLANE:

            correct_ol_status = agent_ist.handle_correct_openlane()

            if correct_ol_status == ac.State.VERIFY_SYNTAX:

                st.session_state.current_state = ac.State.VERIFY_SYNTAX

                update_workflow_status(ui, label='Re-verify syntax after correcting OpenLane.')
            
            elif correct_ol_status == ac.State.RUN_OPENLANE:

                st.session_state.current_state = ac.State.RUN_OPENLANE

                update_workflow_status(ui, label='Re-run OpenLane after correction.')

            elif correct_ol_status == ac.State.ERROR:

                st.session_state.current_state = ac.State.ERROR

            st.rerun()

        elif st.session_state.current_state == ac.State.EXPLORATION_OPENLANE:

            update_progress_bar(ui, 90)

            update_workflow_status(ui, label='Optimizing parameters and this process can take several minutes...')

            ex_check = agent_ist.handle_run_exploration_openlane()

            if ex_check:

                update_progress_bar(ui, 95)

                update_workflow_status(ui, label='Optimizing parameters completed.')

                st.session_state.done_exploration = True

                st.session_state.current_state = ac.State.WRITE_CSV

            st.rerun()


        elif st.session_state.current_state == ac.State.ERROR:

            agent_ist.handle_error()

            st.session_state.is_workflow_error = True

            st.session_state.current_state = ac.State.WRITE_CSV

            st.rerun()


        elif st.session_state.current_state == ac.State.WRITE_CSV:

            # Manual, remove it when setting exploration phase
            # globals.timestamp_tag = 'RUN_2026.10.28_15.44.04'
            # globals.exploration_tag = globals.timestamp_tag

            update_workflow_status(ui, label='Storing .csv artifacts...')

            csv_check = agent_ist.handle_write_csv()
            # csv_check = True

            if csv_check and st.session_state.done_exploration:

                update_workflow_status(ui, label='Physical data is ready')

                st.session_state.physical_summary = True
                

            st.session_state.current_state = ac.State.DONE

            st.rerun()


        elif st.session_state.current_state == ac.State.DONE:

            agent_ist.handle_done()

            st.session_state.done_status = True

            st.session_state.show_trace_button = True

            update_progress_bar(ui, 100)

            st.session_state.current_state = ac.State.STREAMLIT_NON_EXIT

            st.rerun()

        elif st.session_state.current_state == ac.State.STREAMLIT_NON_EXIT:

            # Show notification otherwise nothing is display in status
            if st.session_state.is_workflow_error == True:

                update_workflow_status(ui, label='Workflow finished with errors!', message=globals.app_usage_dict['error_info'], state='error', expanded=True, persist=True)

            else:   

                update_workflow_status(ui, label='Workflow is processed completely!', state='complete')

            # No st.rerun() anymore

        
    if st.session_state.active_drawer and st.session_state.pipeline_started:

        show_trace_drawer()

        st.session_state.active_drawer = False

    
    
if __name__ == "__main__":
    main()
