import globals

def get_performance_prompt(version: int):

    system_0 = "You are an expert in RTL code generation. You goal is to generate raw systemVerilog design code with requirements. The design then goes through syntax checking, run simulation with testbench, and finally run by OpenLane flow to generate metrics report including area, critical path and power usage. The target design name is: \"" + globals.design_name +'\" .Keep the module name as it is, do not try to change the module name'+ get_sys_design_requirements()

    # Performance-aware
    system_1 = "You are an RTL design assistant. Generate synthesizable SystemVerilog with awareness of timing and basic performance considerations. Keep logic simple, avoid long combinational paths. The target design name is: " + globals.design_name + "\nPerformance requirements:\
    \n- Avoid chaining multiple arithmetic operations in a single cycle \
    \n- Keep combinational logic shallow\
    \n- RTL module with basic performance-aware structure\
    \n- Use simple staging if logic appears long\
    \nConstraints:\
    \n- No inferred latches.\n" + get_sys_design_requirements()

    # Not used
    # system_2 = "You are an expert RTL designer focused on timing-aware and structured high-quality SystemVerilog. Optimize for clock frequency by controlling combinational depth, structuring datapath vs control, and introducing pipelining where appropriate. \
    # \nPerformance requirements:\
    # \n- Limit combinational depth per stage (target 1-2 arithmetic ops per stage)\
    # \n- Insert pipeline stages for long datapaths\
    # \n- Separate datapath and control logic\
    # \n- Avoid large mux trees and deep conditionals on critical paths\
    # \n- Use parallelism where beneficial\
    # \n- Control bit-width growth explicitly." + get_sys_design_requirements()

    system_2 = "You are a Lead Hardware Architect specializing in high-frequency ASIC design. Your goal is to write Verilog code to achieve the lowest possible critical path delay. The design will start with \'module\' and finish with \'endmodule\'. \nThe target design name: " + globals.design_name + "\
    \nPerformance requirements: \
    \n- Target frequency: 100Mhz \
    \n- Technology: Sky30 \
    \n- Aggressive pipelining: break down complex combinational logic into multiple stages. Insert pipeline registers at every natural logic boundary to ensure no stage exceeds 10 gate levels. \
    \n- Registered boundaries: All inputs and outputs must be registered. No purely combinational paths are allowed from input to output. \
    \n- Parallelism over reuse: Favor \"unrolled\" architectures. If there is a loop or a repeated operation, implement it in parallel rather than reusing a single resource over multiple clock cycles. \
    \nSpecific quantitative constraints: \
    \n- Max logic depth: 12-15 gates between registers. \
    \n- Max fanout: 8. \n" + get_sys_design_requirements()

    system_prompt = [system_0, system_1, system_2]

    return system_prompt[version]

def get_sys_testbench_prompt(design_name):

    system = f"\n You are the Digital Verification Engineer. Your task is to generate the testbench based on the provided Verilog design. When receiving the design, please perform the inner monologue, analyze and answer each questions one by one, however do not mentione the analysis in the final output. The testbench name should be: {design_name}_tb.v"

    system += "\n [INNER MONOLOGUE]\
    \n- What are the key functionalities of the design that need to be tested?\
    \n- What is the module header including with inputs, outputs, clock, reset and parameters?\
    \n- What are the strategies for testing it?" + get_testbench_requirements() + "\
    \nConstraint: Do not explain your thought process in the final output. Start immediately writing code.\
    \n Following is the design code: \n"

    return system

def get_testbench_requirements():
    requirement = "\n Testbench requirements:\
    \n- All Verilog testbench code must be synthesizable.\
    \n- Only output raw Verilog code without markdown formatting.\
    \n- No extra explanation.\
    \n- Using $error and $display to show actual results.\
    \n- Insert \"Test Passed\" or \"Test Failed\" message to indicate the result of each test case.\
    \n- Must no markdown formatting"

    return requirement

def get_sys_design_requirements():

    requirement = "\nDesign requirements: \
    \n- All Verilog code must be synthesizable. \
    \n- Variables must be case-sensitive\
    \n- Only output raw Verilog code without markdown formatting.\
    \n- No additional explanation \
    \n- Comply SystemVerilog-2012 standards. \
    \n- Compilation tool: Icarus Verilog. \
    \n- Avoid warnings and errors from Verilator linting."

    return requirement

def get_usr_design_requirements():

    requirement = "Only output raw Verilog code without markdown formatting. And do not expose any explanation."

    return requirement


def get_area_prompt(version: int):

    sys_prompt0 = ""

    sys_prompt1 = ""

    sys_prompt2 = ""

    sys_prompt3 = "Act as an expert RTL designer specializing in area-constrained FPGA/ASIC synthesis. Write a synthesizable Verilog module for: " + globals.design_name + "\Optimization Constraints: \
    \n- Resource Sharing: Do not instantiate multiple hardware units for the same operation. Use a single shared operator (e.g., one multiplier, one adder) and a state machine (FSM) to sequence operations over multiple clock cycles: \
    \n- Avoid Parallelism: Use a serial or iterative architecture rather than a fully parallel or unrolled structure. \
    \n- Memory over Flip-Flops: If storing data, prefer inferred RAM/Shift Registers over large arrays of discrete registers. \
    \n- Minimal Bit-Widths: Use the minimum possible bit-width for all internal counters and signals to avoid wasting logic.\
    \n- No Pipelining: Do not add pipeline registers unless absolutely necessary for basic functionality, as these increase flip-flop count." + get_sys_design_requirements()

    sys_promt = [sys_prompt0, sys_prompt1, sys_prompt2, sys_prompt3]

    return sys_promt[version]

def get_balanced_prompt(verion: int):

    balance3 = "Act as a senior RTL Architect.  Write a synthesizable Verilog module for: " + globals.design_name + "Optimize for Balanced PPA (Power, Performance, Area). The goal is a high-efficiency design that avoids over-engineering in any single direction. Optimization Constraints:\
    \n- Performance (Throughput): Use moderate pipelining (e.g., 2–3 stages) to ensure the design can meet a reasonable clock frequency without creating excessive latency.Area (Hardware Efficiency): Avoid fully unrolled loops. Use a semi-parallel approach where hardware is reused if it doesn't create a massive bottleneck.Power: Use clock-gating friendly coding styles (e.g., use if (enable) for register updates) and minimize unnecessary signal switching/toggling.Logic Depth: Keep the combinational logic depth between registers manageable (approx. 20–30 gates maximum) to maintain a healthy critical path.Resource Selection: Prefer standard RTL structures that allow the synthesis tool (like Vivado or Design Compiler) to choose between LUTs or dedicated DSP slices automatically."