import pandas as pd
from agent_config import show_log, prj_dir, gs_title
import gspread


# Reads the OpenLane metrics CSV and exports specific PPA columns to gsheet.
def extract_ppa_to_excel(path_csv, syn_attempt, sim_attempt, ol_attempt):

    # Define the target PPA columns
    ppa_columns = [
        'design_name',
        'config', 
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
    worksheet = sh.worksheet("Sheet1")
    
    try:
        # Load the raw metrics
        df = pd.read_csv(path_csv)
        
        # Filter for the requested columns
        ppa_df = df[ppa_columns].copy()

        ppa_df['Syntax attempt'] = syn_attempt

        ppa_df['Simulation attempt'] = sim_attempt

        ppa_df['OpenLane attempt'] = ol_attempt

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

        ppa_log = f"\nSuccess! PPA report saved to Report/{gs_title}"

        show_log(ppa_log)

        return True

        
    except KeyError as e:

        print(f"Exception: Could not find column {e} in the CSV file.")

        return False

    except Exception as e:

        print(f"Exception: An unexpected error occurred: {e}")
        
        return False
    