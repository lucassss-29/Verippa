import pandas as pd
from agent_config import csv_path, excel_path, show_log
import xlwings as xw


def extract_ppa_to_excel():
    # Reads the OpenLane metrics CSV and exports specific PPA columns to Excel.
    sheet_name='Sheet1'

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
        'DIEAREA_mm^2'                # Area: Total Die Area
    ]

    # Connect to the open Excel book
    wb = xw.Book(excel_path) 
    sheet = wb.sheets[sheet_name]
    
    try:
        # Load the raw metrics
        df = pd.read_csv(csv_path)
        
        # Filter for the requested columns
        ppa_df = df[ppa_columns]

        if sheet.range('A1').value is None:
            #  Achieve header content
            sheet.range('A1').value = ppa_df.columns.tolist()
            start_row = 2
            
        else:
            last_row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row
            start_row = last_row + 1

        sheet.range(f'A{start_row}').options(index=False, header=False).value = ppa_df
        
        ppa_log = f"Success! PPA report saved to: {excel_path}"

        show_log(ppa_log)

        return True

        
    except KeyError as e:

        print(f"Exception: Could not find column {e} in the CSV file.")

        return False

    except Exception as e:

        print(f"Exception: An unexpected error occurred: {e}")
        
        return False
    