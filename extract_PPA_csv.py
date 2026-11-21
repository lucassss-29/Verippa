import pandas as pd
from agent_config import show_log, prj_dir, benchmark, openlane_dir
import gspread
import globals
import re
from agent_config import BenchmarkType
import os

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
    sh = gc.open(globals.gs_title)

    sheet_names = [sheet.title for sheet in sh.worksheets()]

    if globals.gs_sheet in sheet_names:
        print(f"\n'{globals.gs_sheet}' already exists. Opening it...")
        worksheet = sh.worksheet(globals.gs_sheet)
        
    else:
        print(f"\n'{globals.gs_sheet}' not found. Creating it...")
        worksheet = sh.add_worksheet(title=globals.gs_sheet, rows=100, cols=20)

    print('path_csv: ', path_csv)

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

        write_improvement_data(ppa_df)

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
            try:

                sh_response = worksheet.append_rows(data_values)

                sh_row_added = sh_response.get('updates', {}).get('updatedRows', 0)

                if sh_row_added > 0:

                    show_log(f"\nSuccess! PPA report saved to {sh_row_added} rows at Report/{globals.gs_title}\n")

                else:

                    show_log('Google API 0 rows were updated.')

            except Exception as e:

                print(f'[CSV] Network or API Error occurred: {e}')
            

    except KeyError as e:

        print(f"Exception: Could not find column {e} in the CSV file.")

        return False

    except Exception as e:

        print(f"Exception: An unexpected error occurred: {e}")


def write_improvement_data(pf):

    # Success OpenLane path
    first_csv = os.path.join(openlane_dir, "designs", globals.design_name, "runs", globals.timestamp_tag, "reports", "metrics.csv")

    try:

        first_df = pd.read_csv(first_csv)

        if first_df.loc[0, 'design_name'] == globals.design_name:

            bm_frequency = first_df.loc[0, 'suggested_clock_frequency']

            bm_power = first_df.loc[0, 'power_typical_internal_uW'] + first_df.loc[0, 'power_typical_leakage_uW'] + first_df.loc[0, 'power_typical_switching_uW']

            bm_area = first_df.loc[0, 'DIEAREA_mm^2']

            print(bm_frequency, bm_power, bm_area)

        else:

            print('[CSV] Design name not found in the OpenLane report')

    except KeyError as e:

        print(f"Exception: Could not find column {e} in the CSV file.")

    pf['Impr_frequency'] = round(((pf['suggested_clock_frequency'] - bm_frequency)/bm_frequency * 100), 2)

    pf['Impr_power'] = round(((pf['power_typical_internal_uW'] + pf['power_typical_leakage_uW'] + pf['power_typical_switching_uW'] - bm_power)/bm_power * 100), 2)

    pf['Impr_area'] = round(((pf['DIEAREA_mm^2'] - bm_area) / bm_area * 100), 2)




def extract_failure_data(fail_reason, syn_attempt, sim_attempt, ol_attempt, mins, prompt_version):

    # Auth and open the sheet
    gc = gspread.service_account(filename=f'{prj_dir}/Gsheet/credentials.json')
    sh = gc.open(globals.gs_title)

    sheet_names = [sheet.title for sheet in sh.worksheets()]

    if globals.gs_sheet in sheet_names:
        print(f"'{globals.gs_sheet}' already exists. Opening it...")
        worksheet = sh.worksheet(globals.gs_sheet)
        
    else:
        print(f"'{globals.gs_sheet}' not found. Creating it...")
        worksheet = sh.add_worksheet(title=globals.gs_sheet, rows=100, cols=20)

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

    show_log(f"\nFailure data for {globals.design_name} saved to Report/{globals.gs_title}\n")