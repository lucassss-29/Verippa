from operator import le
import os

from auto_code_generation import read_description, simulation_correct, llm_generation, compilation_correct
from project_prompt import get_performance_prompt, get_area_prompt
from check_syntax_and_functional import check_syntax_only, run_testbench
from agent_config import show_log, save_log, agent_gen_timestamp, fetch_workflow_variables, reset_log, State, prompt_version, max_attempts, design_list, openlane_dir
import agent_config as ac
import time
from extract_PPA_csv import extract_ppa_to_excel, extract_failure_data
from openlane_flow import openlane_flow_run, openlane_correct
import globals
from run_benchmark import copy_benchmark_design
import run_benchmark


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

            elif self.current_state == State.RUN_SIMULATION:
                self.handle_run_simulation()

            elif self.current_state == State.RUN_OPENLANE:
                self.handle_run_openlane()

            elif self.current_state == State.CORRECT_OPENLANE:
                self.handle_correct_openlane()

            elif self.current_state == State.WRITE_CSV:
                self.handle_write_csv()

            elif self.current_state == State.DONE:
                self.handle_done()
                break
            
            time.sleep(1) # Small delay for readability


    
    def handle_initial(self):

        print("-> Starting the workflow...\n")

        self.transition_to(State.GENERATE_DESIGN)

        globals.start_time = time.time()



    def handle_generate_design(self):

        design_log = f"-> Calling LLM to generate {self.design_name}.v...\n"

        show_log(design_log)
        
        if self.previous_state == State.INITIAL:

            # Append system prompt with first attempt

            if ac.PPA_type == 'Performance':
            
                system_pt = get_performance_prompt(prompt_version)
            
            elif ac.PPA_type == 'Area':

                system_pt = get_area_prompt(prompt_version)

            # Description will be the user prompt
            self.msg.append({"role": "developer", "content": system_pt})

            user_pt = read_description(ac.benchmark_design_path)

            self.msg.append({"role": "user", "content": user_pt})

            result = llm_generation("design", self.msg, 1, "phase_1")

        if result:

            self.transition_to(State.VERIFY_SYNTAX)

        else:
            print("Error state: Design generation failed.\n")

            self.transition_to(State.ERROR)

            return


    def handle_verify_syntax(self):
        
        ############## Only applied when running benchmark
        copy_benchmark_design()

        globals.start_time = time.time()
        ############## Only applied when running benchmark

        self.synt_count += 1

        verify_log = f"[SYNTX] Running iverilog syntax check...\n[SYNTX]Attempt {self.synt_count} of {self.max_retries} for design: {self.design_name}\n"

        show_log(verify_log)

        result, verify_err = check_syntax_only()

        if result:

            show_log("\n[SYNTX] The design is syntaxcally correct.\n")
            
            show_log(f"[SYNTX] No of attempts successful syntax: {self.synt_count}\n")

            # Record successful syntax attempt
            globals.record_syntax_attempt = self.synt_count
            
            self.transition_to(State.RUN_SIMULATION)

        else:
            self.error_reason = verify_err

            self.correct_design_syntax()



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


    def correct_design_syntax(self):

        if self.synt_count <= self.max_retries:

            print(f"[SYNTX] Attempting design syntax correction {self.synt_count}/{self.max_retries}...\n")

            compilation_correct(self.msg, self.error_reason, ac.design_path, self.synt_count)

            self.transition_to(State.VERIFY_SYNTAX)
            
        else:

            print("Error state: Correct syntax with max retries reached.\n")

            self.error_reason = "Correct syntax with max retries"

            globals.record_syntax_attempt = self.synt_count

            self.transition_to(State.WRITE_CSV)


        
    def correct_design_simulation(self):

        if self.sim_count <= self.max_retries:
            
            print(f"[SIM] Attempting design simulation correction {self.sim_count}/{self.max_retries}...\n")

            simulation_correct(self.msg, self.error_reason, self.sim_count)

            self.transition_to(State.RUN_SIMULATION)
        else:
            print("Error state: Correct simulation with max retries reached.\n")

            self.error_reason = "Correct simulation with max retries"

            globals.record_simulation_attempt = self.sim_count

            self.transition_to(State.WRITE_CSV)



    def handle_run_openlane(self):
        
        self.ol_entry += 1

        show_log("\n[OL] Running OpenLane flow...")

        # Newly created the tag
        tag = agent_gen_timestamp()

        # Debug
        # globals.olis_init = False

        # log_info and log_dir in case failure
        result = openlane_flow_run(globals.olis_init, tag)

        if result:

            show_log(f"[OL] No of attempts successful OpenLane: {self.ol_entry}\n")

            globals.timestamp_tag = tag

            self.transition_to(State.WRITE_CSV)

        else:

            self.transition_to(State.CORRECT_OPENLANE)

        globals.record_openlane_attempt = self.ol_entry


    def handle_correct_openlane(self):

        if self.ol_entry <= self.max_retries:

            print(f"\n[OL] Attempting Openlane correction {self.ol_entry}/{self.max_retries}...\n")

            openlane_correct(self.msg, self.ol_entry)

            if globals.ol_redirect:

                self.transition_to(State.VERIFY_SYNTAX)
            else:
                self.transition_to(State.RUN_OPENLANE)

        else:

            show_log("Error state: Correct Openlane with max retries reached.\n")

            self.error_reason = "Correct Openlane with max retries"

            self.transition_to(State.WRITE_CSV)


    def handle_write_csv(self):

        if globals.start_time is not None:
        
            globals.end_time = time.time()

            globals.duration_minutes = round((globals.end_time - globals.start_time) / 60, 2)
        
        else:
            globals.duration_minutes = 255

        # Only success in OpenLane flow
        if globals.timestamp_tag:

            path_csv = os.path.join(openlane_dir, "designs", self.design_name, "runs", globals.timestamp_tag, "reports", "metrics.csv")

            extract_ppa_to_excel(path_csv, globals.record_syntax_attempt, globals.record_simulation_attempt, globals.record_openlane_attempt, globals.duration_minutes)

        else:

            extract_failure_data(self.error_reason, globals.record_syntax_attempt, globals.record_simulation_attempt, globals.record_openlane_attempt, globals.duration_minutes, ac.prompt_version)

        self.transition_to(State.DONE)


    def handle_done(self):

        # Additional success handling can be added here
        with open(ac.out_conversation_path, 'w') as f:

            for message in self.msg:

                f.write(f"{message}\n")

        show_log("\n[DONE] Workflow completed!\n")
        
        # Save data in 'flow.log'
        save_log()

        reset_log()

        # Reset tag
        globals.timestamp_tag = ""

        # Reset config.json
        globals.olis_init = True

        globals.running_total_tokens = 0


if __name__ == "__main__":

    for i in range(10, 20):

        globals.design_name = design_list[i]

        print("\nProcessing design number: ", i)

        fetch_workflow_variables()
        
        flow = FlowManager()

        flow.run()





