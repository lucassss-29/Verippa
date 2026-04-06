import os

# Global variables

prj_dir = "/Users/dsmac/Documents/thesis/impl/LLMVeriPPA-main/Deepseek"

openlane_dir = "/Users/dsmac/Documents/thesis/impl/OpenLane"

max_attempts = 1

design_name = 'adder_8bit'

benchmark_design_path = os.path.join("./", "Dataset", design_name, "design_description.txt")
model = 'Deepseek'

design_path = os.path.join("./", model, design_name, f"{design_name}.v")
# design_path = "/Users/dsmac/Documents/thesis/impl/LLMVeriPPA-main/Dataset/adder_8bit/verified_adder_8bit.v"

tb_path = os.path.join("./", "Dataset", design_name, "testbench.v")
# tb_path = "/Users/dsmac/Documents/thesis/impl/LLMVeriPPA-main/Dataset/adder_8bit/testbench.v"

out_conversation_path = os.path.join("./", model, design_name, f"{design_name}_conversation.txt")
error_log_path = os.path.join("./", model, design_name, f"{design_name}_error_log.txt")



ol_designname_folder = os.path.join(openlane_dir, model, design_name, f"{design_name}.v")

