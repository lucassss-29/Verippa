import os
from auto_code_generation import read_description, simulation_correct, llm_generation, compilation_correct
from project_prompt import get_performance_prompt
from check_syntax_and_functional import check_syntax_only, run_testbench

from agent_config import show_log, out_conversation_path, save_log, agent_gen_timestamp, openlane_dir, State, prompt_version
import time
from extract_PPA_csv import extract_ppa_to_excel
from agent_config import max_attempts, design_name, benchmark_design_path, design_path
from openlane_flow import openlane_flow_run, openlane_correct
import globals


class FlowManager:
    def __init__(self):
        self.design_name = design_name
        self.current_state = globals.agent_step
        self.previous_state = State.INITIAL
        self.retry_count = 0
        self.loop_count = 0
        self.max_retries = max_attempts
        self.error_reason = None
        self.msg = []
        self.ol_entry = 0


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

            print(f"\n[STATUS] Current State: {self.current_state.name}")
            
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
            elif self.current_state == State.ERROR:
                self.handle_error()
                break
            
            time.sleep(1) # Small delay for readability


    
    def handle_initial(self):

        print("-> Starting the workflow...\n")

        self.transition_to(State.GENERATE_DESIGN)



    def handle_generate_design(self):

        design_log = f"-> Calling LLM to generate {self.design_name}.v...\n"

        show_log(design_log)
        
        if self.previous_state == State.INITIAL:

            # Append system prompt with first attempt
            
            system_pt = get_performance_prompt(prompt_version)

            # Description will be the user prompt
            self.msg.append({"role": "system", "content": system_pt})

            user_pt = read_description(benchmark_design_path)

            self.msg.append({"role": "user", "content": user_pt})

            result = llm_generation("design", self.msg, 1, "phase_1")

        if result:

            self.transition_to(State.VERIFY_SYNTAX)

        else:
            print("Error state: Design generation failed.\n")

            self.transition_to(State.ERROR)

            return


    def handle_verify_syntax(self):

        verify_log = f"-> Running iverilog syntax check...\nAttempt {self.retry_count} of {self.max_retries} for design: {self.design_name}\n"

        show_log(verify_log)

        result, verify_err = check_syntax_only()

        if result:

            show_log("\nThe design is syntaxcally correct.\n")
            
            show_log(f"\nNo of attempts successful syntax: {self.retry_count + 1}\n")

            # Recore successful syntax attempt
            globals.record_syntax_attempt = self.retry_count + 1

            self.retry_count = 0 # Reset retry count for the next phase
            
            self.transition_to(State.RUN_SIMULATION)

        else:
            self.error_reason = verify_err

            self.correct_design_int()



    def handle_run_simulation(self):

        show_log("\n-> Running simulation with testbench\n")

        result, sim_err = run_testbench()

        if result:

            show_log("\nThe design is simulated with no errors.\n")

            show_log(f"\nNo of attempts successful simulation: {self.retry_count + 1}\n")

            # Record successful simulation attempt
            globals.record_simulation_attempt = self.retry_count + 1

            self.transition_to(State.RUN_OPENLANE)

        else:
            self.error_reason = sim_err

            self.correct_testbench_int()



    def correct_design_int(self):

        self.retry_count += 1

        if self.retry_count <= self.max_retries:

            print(f"-> Attempting design correction {self.retry_count}/{self.max_retries}...\n")

            compilation_correct(self.msg, self.error_reason, design_path, self.retry_count)

            self.transition_to(State.VERIFY_SYNTAX)
            
        else:

            print("Error state: Correct design with max retries reached.\n")

            self.transition_to(State.ERROR)


        
    def correct_testbench_int(self):

        # Start entry with 1, end with max (e.g., 5)
        offset_entry = 0

        self.retry_count += 1

        if self.retry_count <= self.max_retries:
            
            print(f"-> Attempting testbench correction {self.retry_count}/{self.max_retries}...\n")

            simulation_correct(self.msg, self.error_reason, (self.retry_count + offset_entry))

            self.transition_to(State.RUN_SIMULATION)
        else:
            print("Error state: Correct testbench with max retries reached.\n")

            self.transition_to(State.ERROR)



    def handle_run_openlane(self):

        show_log("\n-> Running OpenLane flow...\n")

        # Newly created the tag
        tag = agent_gen_timestamp()

        # log_info and log_dir in case failure
        result = openlane_flow_run(globals.olis_init, tag)

        if result:

            show_log(f"\nNo of attempts successful OpenLane: {self.ol_entry + 1}\n")

            globals.timestamp_tag = tag

            globals.record_openlane_attempt = self.ol_entry + 1

            self.transition_to(State.WRITE_CSV)

        else:

            self.transition_to(State.CORRECT_OPENLANE)


    def handle_correct_openlane(self):

        self.ol_entry += 1

        if self.ol_entry <= self.max_retries:

            print(f"-> Attempting Openlane correction {self.ol_entry}/{self.max_retries}...\n")

            openlane_correct(self.msg, self.ol_entry)

            if globals.ol_redirect:

                self.transition_to(State.VERIFY_SYNTAX)
            else:
                self.transition_to(State.RUN_OPENLANE)

        else:

            print("Error state: Correct Openlane with max retries reached.\n")

            self.transition_to(State.ERROR)


    def handle_write_csv(self):

        # Get the csv path base on timestamp tag
        path_csv = os.path.join(openlane_dir, "designs", design_name, "runs", globals.timestamp_tag, "reports", "metrics.csv")

        result = extract_ppa_to_excel(path_csv, globals.record_syntax_attempt, globals.record_simulation_attempt, globals.record_openlane_attempt)

        if result:

            self.transition_to(State.DONE)

        else:

            self.transition_to(State.ERROR)


    def handle_done(self):

        show_log("\n-> Workflow completed successfully!\n")

        # Additional success handling can be added here
        with open(out_conversation_path, 'w') as f:

            for message in self.msg:

                f.write(f"{message}\n")


    def handle_error(self):
        
        print("-> Workflow terminated with errors.\n")

        # Write the conversation
        with open(out_conversation_path, 'w') as f:

            for message in self.msg:

                f.write(f"{message}\n")


if __name__ == "__main__":

    # Start the workflow
    if __name__ == "__main__":

        flow = FlowManager()

        flow.run()

        save_log()




