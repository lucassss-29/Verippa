from cProfile import label
from operator import le
import os
from sqlite3.dbapi2 import Timestamp

from auto_code_generation import read_description, simulation_correct, llm_generation, compilation_correct
from project_prompt import get_performance_prompt, get_area_prompt
from check_syntax_and_functional import check_syntax_only, run_testbench
from agent_config import show_log, save_log, agent_gen_timestamp, fetch_workflow_variables, reset_log, State, max_attempts, design_list, openlane_dir, update_dimensions_param
import agent_config as ac
import time
from extract_PPA_csv import extract_ppa_to_excel, extract_failure_data
from openlane_flow import openlane_flow_run, openlane_correct, openlane_run_exploration, openlane_delete_temp_items
import globals
from run_benchmark import copy_benchmark_design
import run_benchmark
from openlane_optimization import evaluate_openlane_performance
from skopt import gp_minimize
from skopt import dump, load
import pandas as pd
from skopt.callbacks import DeltaYStopper
import streamlit as st
from chat_status_manager import update_workflow_status
import shutil
import sys

class FlowManager:
    def __init__(self):
        self.design_name = globals.design_name
        self.current_state = globals.agent_step
        self.previous_state = State.INITIAL
        self.synt_count = 0
        self.sim_count = 0
        self.ol_entry = 0
        self.loop_count = 0
        self.max_retries = max_attempts
        self.error_reason = None
        self.msg = []


    def transition_to(self, next_state):

        """Safely updates states and maintains history."""
        if next_state == self.current_state:
            return # Avoid redundant transitions
            
        self.previous_state = self.current_state

        self.current_state = next_state

        trans = f"Transition: {self.previous_state.name} -> {self.current_state.name}"

        show_log(trans)


    def run(self):
        while True:

            if self.current_state == State.INITIAL:
                self.handle_initial()

            elif self.current_state == State.GENERATE_DESIGN:
                self.handle_generate_design()

            elif self.current_state == State.VERIFY_SYNTAX:
                self.handle_verify_syntax()

            elif self.current_state == State.CORRECT_SYNTAX:
                self.handle_correct_design_syntax()

            elif self.current_state == State.RUN_SIMULATION:
                self.handle_run_simulation()

            elif self.current_state == State.RUN_OPENLANE:
                self.handle_run_openlane()

            elif self.current_state == State.CORRECT_OPENLANE:
                self.handle_correct_openlane()

            elif self.current_state == State.EXPLORATION_OPENLANE:
                self.handle_run_exploration_openlane()

            elif self.current_state == State.WRITE_CSV:
                self.handle_write_csv()

            elif self.current_state == State.ERROR:
                self.handle_error()
            
            elif self.current_state == State.DONE:
                self.handle_done()
                break

            time.sleep(1) # Small delay for readability


    
    def handle_initial(self):

        print("-> Starting the workflow...\n")

        self.transition_to(State.GENERATE_DESIGN)

        # Delete all old artifacts
        if os.path.exists(ac.design_folder_path):

            shutil.rmtree(ac.design_folder_path)

            print('Deleted old folder artifacts.')

        globals.start_time = time.time()


    def handle_generate_design(self):

        design_log = f"-> Calling LLM to generate {self.design_name}.v...\n"

        show_log(design_log)

        result = False

        if globals.APP_IN_USE == True:
            if ac.PPA_type == 'Performance':
            
                system_pt = get_performance_prompt(globals.prompt_version)
            
            elif ac.PPA_type == 'Area':

                system_pt = get_area_prompt(globals.prompt_version)

            # Description will be the user prompt
            self.msg.append({"role": ac.system_role, "content": system_pt})

            # user_pt = read_description(ac.benchmark_design_path)

            user_pt = globals.design_description

            self.msg.append({"role": "user", "content": user_pt})

            result = llm_generation("design", self.msg, 1, "phase_1")

            if result:

                self.transition_to(State.VERIFY_SYNTAX)

            else:
                self.error_reason = 'Design generation failed.'

                self.transition_to(State.ERROR)

        elif globals.APP_IN_USE == False:

            copy_benchmark_design()

            self.transition_to(State.VERIFY_SYNTAX)

            result = True

        return result


    def handle_verify_syntax(self):
        
        self.synt_count += 1

        verify_log = f"[SYNTX] Running iverilog syntax check...\n[SYNTX]Attempt {self.synt_count} of {self.max_retries} for design: {globals.design_name}\n"

        show_log(verify_log)

        result, verify_err = check_syntax_only()

        if result:

            show_log("\n[SYNTX] The design is syntaxcally correct.\n")
            
            show_log(f"[SYNTX] No of attempts successful syntax: {self.synt_count}\n")

            # Record successful syntax attempt
            globals.record_syntax_attempt = self.synt_count

            if globals.APP_IN_USE == True:
                self.transition_to(State.RUN_OPENLANE)

            else:
                self.transition_to(State.RUN_SIMULATION)

        else:
            self.error_reason = verify_err

            self.transition_to(State.CORRECT_SYNTAX)

        return result
    
    
    def handle_correct_design_syntax(self):

        if self.synt_count <= self.max_retries:

            print(f"[SYNTX] Attempting design syntax correction {self.synt_count}/{self.max_retries}...\n")

            # Generate new code
            result = compilation_correct(self.msg, self.error_reason, ac.design_path, self.synt_count)

            if result:

                self.transition_to(State.VERIFY_SYNTAX)

                crt_syntax_status = State.VERIFY_SYNTAX

            else:

                self.error_reason = 'Failed due to LLM ability of  design re-generation.'

                self.transition_to(State.ERROR)

                crt_syntax_status = State.ERROR
            
        else:

            print("Error state: Correct syntax with max retries reached.\n")

            self.error_reason = "Correct syntax with max retries"

            globals.record_syntax_attempt = self.synt_count

            self.transition_to(State.ERROR)

            crt_syntax_status = State.ERROR

        return crt_syntax_status


    def handle_run_simulation(self):

        self.sim_count += 1

        show_log("\n[SIM] Running simulation with testbench\n")

        result, sim_err = run_testbench()

        if result:

            show_log(f"[SIM] No of attempts successful simulation: {self.sim_count}\n")

            # Record successful simulation attempt
            globals.record_simulation_attempt = self.sim_count

            self.transition_to(State.RUN_OPENLANE)

        else:
            self.error_reason = sim_err

            self.correct_design_simulation()

        return result

    
    def correct_design_simulation(self):

        if self.sim_count <= self.max_retries:
            
            print(f"[SIM] Attempting design simulation correction {self.sim_count}/{self.max_retries}...\n")

            simulation_correct(self.msg, self.error_reason, self.sim_count)

            self.transition_to(State.RUN_SIMULATION)
        else:
            print("Error state: Correct simulation with max retries reached.\n")

            self.error_reason = "Correct simulation with max retries"

            globals.record_simulation_attempt = self.sim_count

            self.transition_to(State.ERROR)


    def handle_run_openlane(self):

        # globals.start_time = time.time()
        globals.app_usage_dict['openlane_tries'] = self.ol_entry
        
        self.ol_entry += 1

        show_log("\n[OL] Running OpenLane flow...")

        # Newly created the tag
        tag = agent_gen_timestamp(False)

        result = openlane_flow_run(globals.olis_init, tag)

        if result:

            show_log(f"[OL] No of attempts successful OpenLane: {self.ol_entry}\n")

            globals.timestamp_tag = tag

            # self.transition_to(State.WRITE_CSV)
            self.transition_to(State.EXPLORATION_OPENLANE)

        else:

            self.transition_to(State.CORRECT_OPENLANE)

        globals.record_openlane_attempt = self.ol_entry

        return result

    def handle_run_exploration_openlane(self):

        result = False

        globals.ol_update_dimension = False # Allow update params only one

        update_dimensions_param()

        early_stopper = DeltaYStopper(delta=0.00005, n_best=5)

        search_result = gp_minimize(
            func=evaluate_openlane_performance, # The execution function object
            dimensions=ac.dimensions, # Target parameter variables
            n_calls=ac.MAX_OL_EXPLORATION, # Maximum total, 30 OpenLane executions allowed
            n_initial_points=(ac.MAX_OL_EXPLORATION//2), # Random exploratory seeds to sketch out the initial map
            # random_state=42,
            callback=[early_stopper]
        )

        if not hasattr(search_result, 'x_iters') or len(search_result.x_iters) == 0:
            print("[ERROR] Optimization stopped before completing a single run.")
            
        elif search_result.fun >= 15:
            print("[WARNING] Optimization finished, but ALL OpenLane runs failed or crashed.")

        # Check C: SUCCESS! Safe to access data
        else:

            result = True

            show_log(f"\n[SUCCESS] Optimization completed safely after {len(search_result.x_iters)} iterations!")

            checkpoint_filename = os.path.join(globals.local_folder, globals.design_name,"openlane_bo_result_ppa.pkl")
            dump(search_result, checkpoint_filename, store_objective=True)
            # search_result = load(checkpoint_filename)


            show_log(f"\n[CHECKPOINT] Optimization object successfully saved to '{checkpoint_filename}'")

            show_log("\n========================================================")
            show_log("OPTIMIZATION COMPLETE")
            show_log("========================================================")
            show_log(f"Optimal Parameter Selection Found:")
            show_log(f" -> Target Clock Period:   {search_result.x[0]:.3f} ns")
            show_log(f" -> Core Utilization Ratio: {search_result.x[1]} %")
            show_log(f" -> Target Grid Density:    {search_result.x[2]:.3f}")
            show_log(f" -> Selected Synthesis Strategy: {search_result.x[3]}")
            show_log(f"Best Achievable Loss Score: {search_result.fun:.2f}")

            df = pd.read_csv(os.path.join(globals.local_folder, globals.design_name, f"optimization_history_manifest_ppa_{globals.timestamp_tag}.csv"))

            target_score = round(search_result.fun, 4)

            # Extract the timestamp(s) matching the exact score
            globals.exploration_tag = df.loc[df['Loss_Score'] == target_score, 'Timestamp'].values[0]

            show_log(f"Found timestamp: {globals.exploration_tag}")

        self.transition_to(State.WRITE_CSV)

        return result


    def handle_correct_openlane(self):

        if self.ol_entry <= 10:

            print(f"\n[OL] Attempting Openlane correction {self.ol_entry}/10...\n")

            openlane_correct(self.msg, self.ol_entry)

            if globals.ol_redirect:

                self.transition_to(State.VERIFY_SYNTAX)

                status_state = State.VERIFY_SYNTAX

            else:
                self.transition_to(State.RUN_OPENLANE)

                status_state = State.RUN_OPENLANE

        else:

            show_log("Error state: Correct Openlane with max retries reached.\n")

            self.error_reason = "Correct Openlane with max retries"

            self.transition_to(State.ERROR)

            status_state = State.ERROR

        return status_state


    def handle_error(self):
        
        #Recore error reason
        globals.app_usage_dict['error_info'] = self.error_reason

        self.transition_to(State.WRITE_CSV)


    def handle_write_csv(self):

        # globals.exploration_tag = 'RUN_EX_2026.11.18_02.36.13'

        # globals.timestamp_tag = 'RUN_2026.11.18_02.28.24'

        result = False

        if globals.start_time is not None:
        
            globals.end_time = time.time()

            globals.duration_minutes = round((globals.end_time - globals.start_time) / 60, 2)
        
        else:
            globals.duration_minutes = 255

        # Extract after Openlane exploration
        if globals.exploration_tag:

            csv_first = os.path.join(openlane_dir, "designs", globals.design_name, "runs", globals.timestamp_tag, "reports", "metrics.csv")

            extract_ppa_to_excel(csv_first, globals.record_syntax_attempt, globals.record_simulation_attempt, globals.record_openlane_attempt, globals.duration_minutes)

            time.sleep(2)

            path_csv = os.path.join(openlane_dir, "designs", globals.design_name, "runs", globals.exploration_tag, "reports", "metrics.csv")

            extract_ppa_to_excel(path_csv, globals.record_syntax_attempt, globals.record_simulation_attempt, globals.record_openlane_attempt, globals.duration_minutes)

            result = True

        else:

            extract_failure_data(self.error_reason, globals.record_syntax_attempt, globals.record_simulation_attempt, globals.record_openlane_attempt, globals.duration_minutes, globals.prompt_version)

        self.transition_to(State.DONE)

        return result


    def handle_done(self):

        # Additional success handling can be added here
        with open(globals.app_usage_dict['out_conversation_path'], 'w') as f:

            for message in self.msg:

                f.writelines(f"{message}\n")

        show_log("\n[DONE] Workflow completed!\n")
        
        # Save data in 'flow.log'
        save_log()

        reset_log()

        openlane_delete_temp_items(os.path.join(ac.ol_source_mount, globals.design_name))

        # Reset tag
        if globals.APP_IN_USE == False:

            globals.timestamp_tag = ""

            globals.exploration_tag = ""

        globals.exploration_count = 0

        # Reset config.json
        globals.olis_init = True

        globals.running_total_tokens = 0

        globals.record_syntax_attempt = 0

        globals.record_simulation_attempt = 0

        globals.record_openlane_attempt = 0

    




if __name__ == "__main__":

    designs_indices = [int(arg) for arg in sys.argv[1:-1]]

    user_ppa = sys.argv[-1]

    for design_i in designs_indices:

        globals.design_name = design_list[design_i]

        print("\nProcessing design number: ", design_i)

        globals.PPA_strategy = ac.PPA_Strategy_Dt.get(user_ppa)

        fetch_workflow_variables()
        
        flow = FlowManager()

        flow.run()

        time.sleep(2)





