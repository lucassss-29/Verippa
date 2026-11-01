import pandas as pd
from agent_config import show_log, prj_dir, gs_title, gs_sheet
import gspread
import globals

# Reads the OpenLane metrics CSV and exports specific PPA columns to gsheet.
def extract_ppa_to_excel(path_csv, syn_attempt, sim_attempt, ol_attempt, mins):

    # Define the target PPA columns
    ppa_columns = [
        'design_name',
        'config',
        'flow_status',
        'total_runtime', 
        'spef_wns',                   # Performance: WNS (Timing)
        'critical_path_ns',           # Performance: Critical Path Delay
        'power_typical_internal_uW',  # Power: Internal
        'power_typical_leakage_uW',   # Power: Leakage
        'power_typical_switching_uW', # Power: Switching
        'CoreArea_um^2',              # Area: Standard Cell Core Area
        'DIEAREA_mm^2',               # Area: Total Die Area
        'CLOCK_PERIOD',
        'suggested_clock_frequency',
        'FP_CORE_UTIL'
    ]

    # Auth and open the sheet
    gc = gspread.service_account(filename=f'{prj_dir}/Gsheet/credentials.json')
    sh = gc.open(gs_title)

    sheet_names = [sheet.title for sheet in sh.worksheets()]

    if gs_sheet in sheet_names:
        print(f"\n'{gs_sheet}' already exists. Opening it...")
        worksheet = sh.worksheet(gs_sheet)
        
    else:
        print(f"\n'{gs_sheet}' not found. Creating it...")
        worksheet = sh.add_worksheet(title=gs_sheet, rows=100, cols=20)

    try:
        # Load the raw metrics
        df = pd.read_csv(path_csv)
        
        # Filter for the requested columns
        ppa_df = df[ppa_columns].copy()

        ppa_df['Syntax attempt'] = syn_attempt

        ppa_df['Simulation attempt'] = sim_attempt

        ppa_df['OpenLane attempt'] = ol_attempt

        ppa_df['Duration (mins)'] = mins

        ppa_df['version'] = f"v{globals.prompt_version}"

        ppa_df['prompt_token'] = globals.running_total_tokens


        # Prepare data for GSheet
        data_values = ppa_df.values.tolist()

        # Check if A1 is empty
        a1_value = worksheet.acell('A1').value

        if not a1_value:

            header = ppa_df.columns.tolist()

            # Sheet is empty: write header and data together
            worksheet.update([header] + data_values)

        else:

            # Sheet has data: write only the new data (append to the end)
            worksheet.append_rows(data_values)

        show_log(f"\nSuccess! PPA report saved to Report/{gs_title}\n")

    except KeyError as e:

        print(f"Exception: Could not find column {e} in the CSV file.")

        return False

    except Exception as e:

        print(f"Exception: An unexpected error occurred: {e}")
        

def extract_failure_data(fail_reason, syn_attempt, sim_attempt, ol_attempt, mins, prompt_version):

    # Auth and open the sheet
    gc = gspread.service_account(filename=f'{prj_dir}/Gsheet/credentials.json')
    sh = gc.open(gs_title)

    sheet_names = [sheet.title for sheet in sh.worksheets()]

    if gs_sheet in sheet_names:
        print(f"'{gs_sheet}' already exists. Opening it...")
        worksheet = sh.worksheet(gs_sheet)
        
    else:
        print(f"'{gs_sheet}' not found. Creating it...")
        worksheet = sh.add_worksheet(title=gs_sheet, rows=100, cols=20)

    failure_dict = {
        'design_name': globals.design_name,
        'config': '',
        'flow_status': f"flow_failed. {fail_reason}",
        'total_runtime': "Failed", 
        'spef_wns': "Failed",                   
        'critical_path_ns': "Failed",           
        'power_typical_internal_uW': "Failed",  
        'power_typical_leakage_uW': "Failed",   
        'power_typical_switching_uW': "Failed", 
        'CoreArea_um^2': "Failed",              
        'DIEAREA_mm^2': "Failed",               
        'CLOCK_PERIOD': "Failed",
        'suggested_clock_frequency': "Failed",
        'FP_CORE_UTIL': "Failed",
        'Syntax attempt': syn_attempt,
        'Simulation attempt': sim_attempt,
        'OpenLane attempt': ol_attempt,
        'Duration (mins)': mins,
        'version': f"v{prompt_version}",
        'prompt_token': globals.running_total_tokens
    }

    worksheet.append_row(list(failure_dict.values()))

    show_log(f"\nFailure data for {globals.design_name} saved to Report/{gs_title}\n")