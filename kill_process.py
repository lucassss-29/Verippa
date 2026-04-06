import psutil
import os

def kill_process_by_name(process_name):
    # Iterate through all running processes
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        try:
            # Check if process name contains our search term (case-insensitive)
            if process_name.lower() in proc.info['name'].lower():
                print(f"Found {proc.info['name']} (PID: {proc.info['pid']}). Killing...")
                
                # .terminate() is like 'Quit' (Polite)
                # .kill() is like 'Force Quit' (Instant)
                proc.kill() 
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

# Example: Kill any process with "openroad" or "yosys" in the name
kill_process_by_name("vvp")