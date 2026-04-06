
from auto_code_generation import read_description, simulation_correct, llm_generation, compilation_correct, testbench_generation
from project_prompt import get_performance_prompt
from check_syntax_and_functional import check_syntax_only, run_testbench
from enum import Enum, auto
from agent_config import out_conversation_path, error_log_path
import time

from agent_config import max_attempts, design_name, benchmark_design_path, design_path, tb_path

class State(Enum):
    INITIAL = auto()
    GENERATE_DESIGN = auto()
    VERIFY_SYNTAX = auto()
    RUN_SIMULATION = auto()
    RUN_OPENLANE = auto()
    DONE = auto()
    ERROR = auto()

class FlowManager:
    def __init__(self):
        self.design_name = design_name
        self.current_state = State.GENERATE_DESIGN
        self.previous_state = State.INITIAL
        self.retry_count = 0
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
        print(f"Transition: {self.previous_state.name} -> {self.current_state.name}")

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
            elif self.current_state == State.DONE:
                self.handle_done()
                break
            elif self.current_state == State.ERROR:
                self.handle_error()
                break
            
            time.sleep(1) # Small delay for readability
    
    def handle_initial(self):
        print("-> Starting the workflow...")
        self.transition_to(State.GENERATE_DESIGN)

    def handle_generate_design(self):
        print(f"-> Calling LLM to generate {self.design_name}.v...")
        
        if self.previous_state == State.INITIAL:
            system_pt = get_performance_prompt("v1")
            # Description will be the user prompt
            self.msg.append({"role": "system", "content": system_pt})
            user_pt = read_description(benchmark_design_path)

            self.msg.append({"role": "user", "content": user_pt})
            result = llm_generation("design", self.msg, 0, "phase_1")

        if result:
            self.transition_to(State.VERIFY_SYNTAX)
        else:
            print("Error state: Design generation failed.")
            self.transition_to(State.ERROR)
            return

    def handle_verify_syntax(self):
        # Simulate a syntax error to trigger the 'Correct' state
        print("-> Running iverilog syntax check...")

        print(f"Attempt {self.retry_count} of {self.max_retries} for design: {self.design_name}")

        result, verify_err = check_syntax_only()
        if result:
            print("The design is syntaxcally correct.")
            self.retry_count = 0 # Reset retry count for the next phase
            self.transition_to(State.RUN_SIMULATION)

        else:
            self.correct_design_int()
            self.error_reason = verify_err

    def handle_run_simulation(self):
        print("-> Running simulation in Docker/OpenLane...")
        result, sim_err = run_testbench()
        if result:
            print("The design is simulated with no errors.")
            self.transition_to(State.DONE)

        else:
            self.error_reason = sim_err
            self.correct_testbench_int()

    def correct_design_int(self):
        self.retry_count += 1
        if self.retry_count < self.max_retries:
            print(f"-> Attempting design correction {self.retry_count}/{self.max_retries}...")
            compilation_correct(self.msg, self.error_reason, design_path, self.retry_count)
            self.transition_to(State.VERIFY_SYNTAX)
        else:
            print("Error state: Correct design with max retries reached.")
            self.transition_to(State.ERROR)
        
    def correct_testbench_int(self):
        self.retry_count += 1
        if self.retry_count < self.max_retries:
            print(f"-> Attempting testbench correction {self.retry_count}/{self.max_retries}...")
            simulation_correct(self.msg, self.error_reason, self.retry_count)
            self.transition_to(State.RUN_SIMULATION)
        else:
            print("Error state: Correct testbench with max retries reached.")
            self.transition_to(State.ERROR)

    def handle_run_openlane(self):
        print("-> Running OpenLane flow...")

        result = run_openlane_flow()
        

    def handle_done(self):
        print("-> Workflow completed successfully!")
        # Additional success handling can be added here
        with open(out_conversation_path, 'w') as f:
            for message in self.msg:
                f.write(f"{message}\n")

    def handle_error(self):
        print("-> Workflow terminated with errors.")
        print(f"Final error reason: {self.error_reason}")
        # Additional error handling can be added here
        with open(error_log_path, 'w') as f:
            f.writelines(self.error_reason)

        # Write the conversation
        with open(out_conversation_path, 'w') as f:
            for message in self.msg:
                f.write(f"{message}\n")


if __name__ == "__main__":

    # Start the workflow
    if __name__ == "__main__":
        flow = FlowManager()
        flow.run()



