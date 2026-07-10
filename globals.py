# Store successful Openlan tag
timestamp_tag = ""

# Handle init of OpenLane flow whether true or false
olis_init = True

# Handle flow system
ol_redirect = False

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