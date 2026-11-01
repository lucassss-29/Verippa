# Store successful Openlan tag
timestamp_tag = ""

exploration_tag = ""

# Handle init of OpenLane flow whether true or false
olis_init = True

# Handle flow system
ol_redirect = False

#Handle update Openlane explore dimension, reason due to the json file are located in the same place.
ol_update_dimension = False

# Handle general retry attempts
record_syntax_attempt = 0
record_simulation_attempt = 0
record_openlane_attempt = 0

running_total_tokens = 0

# Handle which state is triggered first
agent_step = None

# Handle time duration for each phase
start_time = None
end_time = None
duration_minutes = None

# Handle global design name
design_name = ""

exploration_count = 0

AI_provider = ""

prompt_version = -1

PPA_strategy = "" #Balanced or High performance

design_description = "" 

app_usage_dict = {
    'error_info': '',
    'log_path': '',
    'fail_log_path': '',
    'ol_log_path': '',
    'out_conversation_path': '',
    'stream_object': None,
    'openlane_trace_path': ''
}