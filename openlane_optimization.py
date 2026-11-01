import os
import sys
import subprocess
import csv
from skopt.utils import use_named_args
import json
import agent_config as ac
from openlane_flow import openlane_flow_run
import globals
import pandas as pd
from skopt.plots import plot_convergence, plot_objective
import matplotlib.pyplot as plt
from skopt import load
from matplotlib.transforms import Bbox
import numpy as np

# -------------------------------------------------------------------------
# 1. Define the Parameter Search Space
# -------------------------------------------------------------------------


# -------------------------------------------------------------------------
# 2. Helper Functions: Config Writing & Report Parsing
# -------------------------------------------------------------------------
def generate_config_files(clk, util, density, strategy):

    with open(ac.ol_json_path, "r") as f:
        data = json.load(f)

    data["CLOCK_PERIOD"] = clk
    data["FP_CORE_UTIL"] = util
    data["PL_TARGET_DENSITY"] = density
    data["SYNTH_STRATEGY"] = strategy
    data["RUN_KLAYOUT"] = False
    data["GLB_RESIZER_TIMING_OPTIMIZATIONS"] = True

    with open(ac.ol_json_path, "w") as f:

        json.dump(data, f, indent=4)

def parse_openlane_metrics():

    TARGET_POWER = 0.001       # Max allowed power in uW
    TARGET_CLOCK = 10.0        # Max allowed clock period in ns
    TARGET_AREA  = 0.01         # Max allowed area in mm2

    # Path inside OpenLane directory pointing to the latest run logs
    csv_dir = os.path.join(ac.openlane_dir, "designs", globals.design_name, "runs", globals.exploration_tag, "reports", "metrics.csv")
    
    df = pd.read_csv(csv_dir)
    
    flow_sts = df.loc[0, 'flow_status']

    if flow_sts == "flow completed":

        wns = df.loc[0, 'wns']
        cp_ns = df.loc[0, 'critical_path_ns']

        # return wns, cp_ns
        power = df.loc[0, 'power_typical_internal_uW'] + df.loc[0, 'power_typical_leakage_uW'] + df.loc[0, 'power_typical_switching_uW']

        area = df.loc[0, 'DIEAREA_mm^2']

        clock = df.loc[0, 'CLOCK_PERIOD']

        # Same scale

        norm_power = power / TARGET_POWER

        norm_clock = clock / TARGET_CLOCK

        norm_area = area / TARGET_AREA

        return wns, norm_power, norm_clock, norm_area, cp_ns, flow_sts
    
    else:
        # Fallback values if files are missing or incomplete
        return -9, 9, 9, 9, 9, flow_sts

# -------------------------------------------------------------------------
# 3. Define the Objective Function (The Black Box Core)
# -------------------------------------------------------------------------
def evaluate_openlane_performance(params):

    CLOCK_PERIOD, FP_CORE_UTIL, PL_TARGET_DENSITY, SYNTH_STRATEGY = params

    CLOCK_PERIOD = round(float(CLOCK_PERIOD), 3)
    FP_CORE_UTIL = int(FP_CORE_UTIL)
    PL_TARGET_DENSITY = round(float(PL_TARGET_DENSITY), 2)
    SYNTH_STRATEGY = str(SYNTH_STRATEGY)
    
    # Generate the custom run files with parameters suggested by the optimizer
    generate_config_files(CLOCK_PERIOD, FP_CORE_UTIL, PL_TARGET_DENSITY, SYNTH_STRATEGY)

    globals.exploration_tag = ac.agent_gen_timestamp(True)

    result = openlane_flow_run(False, globals.exploration_tag)

    if result:
            
        # Step B: Parse real metrics out of generated layouts
        wns, power_metric, perform_metric, area_metric, cp_ns_metric, _ = parse_openlane_metrics()

        if globals.PPA_strategy == 'Balanced':

            w_perf  = 0.40  # Give performance slightly higher priority
            w_area  = 0.30  # Keep area tight
            w_power = 0.30  # Suppress thermal/battery leak
        
            # Calculate balanced PPA Loss
            base_ppa_loss = (w_perf * perform_metric) + (w_area * area_metric) + (w_power * power_metric)

            # Step C: Run the Performance Loss Logic
            if wns < 0:
                # Timing failed. Score scales by how badly it missed the deadline
                loss_score = 1.5 + abs(wns)
            else:

                loss_score = base_ppa_loss

        elif globals.PPA_strategy == 'High frequency':
            
            if wns < 0:
                loss_score = 5.0 + (abs(wns) * 10.0)

            else:

                loss_score = (CLOCK_PERIOD * 10.0) - ((CLOCK_PERIOD - cp_ns_metric) * 5.0)

        print(f"[BO EVALUATION] Calculated Parameter Loss Score: {round(loss_score, 2)}")

    else:

        if globals.PPA_strategy == 'Balanced':

            loss_score =  3.0

        elif globals.globals.PPA_strategy == 'High frequency':

            loss_score = CLOCK_PERIOD * 15.0
    
    loss_score = round(loss_score, 2)

    globals.exploration_count += 1

    print(f"\nEXPLORATION COUNT =======: {globals.exploration_count} / 30" )

    if globals.exploration_count > 30:
        globals.exploration_count = 0

    log_run_metadata(globals.exploration_tag, CLOCK_PERIOD, FP_CORE_UTIL, PL_TARGET_DENSITY, SYNTH_STRATEGY, loss_score, globals.exploration_count, result)

    return loss_score

def log_run_metadata(timestamp, clk, util, density, strategy, loss_score, count, sts):
    log_file = os.path.join(ac.model, globals.design_name, "optimization_history_manifest_ppa.csv")
    file_exists = os.path.exists(log_file)
    
    with open(log_file, mode="a", newline="") as f:
        writer = csv.writer(f)
        # Write headers if it's a fresh file
        if not file_exists:
            writer.writerow(["Timestamp", "Clock_Period", "Core_Util", "Density", "Strategy", "Loss_Score", "Count", "Status"])
        
        # Log the current run's profile
        writer.writerow([timestamp, clk, util, density, strategy, loss_score, count, sts])

    print("LOG Exploration successfully.")

def openlane_plot_ex():

    ds_name = ac.design_list[0]

    # 1. Define the filename of your saved checkpoint
    checkpoint_filename = os.path.join(ac.model, ds_name, "openlane_bo_result.pkl")

    print(f"⌛ Loading optimization checkpoint from '{checkpoint_filename}'...")

    try:
        # 2. Load the complete optimization history object back into memory
        res_loaded = load(checkpoint_filename)

        # y_vals = res_loaded.func_vals

        # print("Y value: ", y_vals)
        
        plt.figure(figsize=(6, 4))
        ax = plot_convergence(res_loaded)
        plt.title("")
        plt.xlabel("Số lượng vòng lặp")
        plt.ylabel("Giá trị hàm mất mát")

        optimal_step = np.argmin(res_loaded.func_vals) + 1
        best_score = res_loaded.fun
        ax.scatter(optimal_step, best_score, color='#E45756', marker='o', s=40, zorder=5)

        plt.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)
        plt.savefig(os.path.join(ac.model, ds_name,"optimization_convergence_map.pdf"), bbox_inches='tight')
        plt.close()
        

        # fig = plt.figure(figsize=(12, 12))
        # plot_objective(res_loaded, cmap='Blues', levels=10)

        # all_axes = plt.gcf().axes

        # for ax in all_axes:
        #     if ax.get_ylabel() == "Partial dependence":
        #         ax.set_visible(False)

        #     # print(f"Order: {ax}, {ax.get_ylabel()}")


        # fig_w, fig_h = fig.get_size_inches()

        # print(fig_w, fig_h)

        # pdf_crop_box = Bbox([[0.0, 0.0], [fig_w * 0.5, fig_h * 0.48]])

        # print(pdf_crop_box)

        # plt.savefig(os.path.join(ac.model, ds_name,"optimization_search_space_map.pdf"), bbox_inches=pdf_crop_box)
        # plt.close()
        
        

    except FileNotFoundError:
        print(f"Error: Could not find the checkpoint file '{checkpoint_filename}'.")
        print("Make sure your main optimization script finished running and saved the file.")
    except Exception as e:
        print(f"An error occurred while parsing the checkpoint file: {e}")

# -------------------------------------------------------------------------
# 4. Start the Optimization Loop
# -------------------------------------------------------------------------
if __name__ == "__main__":

    print("=== Launching Performance-Targeted Bayesian Optimization ===")

    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = ["Times New Roman"]
    plt.rcParams.update({'font.size': 12})

    openlane_plot_ex()
    
