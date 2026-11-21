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

    # Read minimum standard from successful OpenLane
    done_csv = os.path.join(ac.openlane_dir, "designs", globals.design_name, "runs", globals.timestamp_tag, "reports", "metrics.csv")

    try:

        done_df = pd.read_csv(done_csv)

        if done_df.loc[0, 'design_name'] == globals.design_name:

            minimum_power = done_df.loc[0, 'power_typical_internal_uW'] + done_df.loc[0, 'power_typical_leakage_uW'] + done_df.loc[0, 'power_typical_switching_uW']

            minimum_area = done_df.loc[0, 'DIEAREA_mm^2']

            TARGET_POWER = {'max': 0.5, 'min': minimum_power}

            TARGET_AREA = {'max': 0.2, 'min': minimum_area}

        else:

            print('[CSV] Design name not found in the OpenLane report')

    except KeyError as e:

        print(f"Exception: Could not find column {e} in the CSV file.")

    MIN_CLOCK = globals.EXPLORATION_PARAMS_DT.get('min_clock')
    MAX_CLOCK = globals.EXPLORATION_PARAMS_DT.get('max_clock')

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

        norm_power = (power - TARGET_POWER.get('min')) / (TARGET_POWER.get('max') - TARGET_POWER.get('min'))

        norm_clock = (clock - MIN_CLOCK) / (MAX_CLOCK - MIN_CLOCK)

        norm_area = (area - TARGET_AREA.get('min')) / (TARGET_AREA.get('max') - TARGET_AREA.get('min'))

        return wns, norm_power, norm_clock, norm_area, cp_ns, flow_sts
    
    else:
        # Fallback values if files are missing or incomplete
        return -9, 9, 9, 9, 9, flow_sts
    

def apply_second_norm(power_value, perf_value, area_value):

    SECOND_MIN = min(power_value, perf_value, area_value)

    SECOND_MAX = max(power_value, perf_value, area_value)

    # Scale to 0.1 - 0.9
    power_normed_apply = 0.1 + ((power_value - SECOND_MIN) * 0.8)/(SECOND_MAX - SECOND_MIN)

    perf_normed_apply = 0.1 + ((perf_value - SECOND_MIN) * 0.8)/(SECOND_MAX - SECOND_MIN)

    area_normed_apply = 0.1 + ((area_value - SECOND_MIN) * 0.8)/(SECOND_MAX - SECOND_MIN)

    return power_normed_apply, perf_normed_apply, area_normed_apply

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

        # APPLY SECOND NORMALIZATION
        # power_metric, perform_metric, area_metric = apply_second_norm(power_metric, perform_metric, area_metric)

        if globals.PPA_strategy == ac.PPA_Strategy_Dt.get('B'):

            # version 1: 0.3, 0.3, 0.3
            # version 2: 0.1, 0.55, 0.35
            w_perf  = 1
            w_area  = 1
            w_power = 1

            param_set = [w_perf, w_area, w_power]

        if globals.PPA_strategy == ac.PPA_Strategy_Dt.get('P1'):

            power_metric, perform_metric, area_metric = apply_second_norm(power_metric, perform_metric, area_metric)

            w_perf = 0.1
            w_area = 0.2
            w_power = 0.7

            param_set = [w_perf, w_area, w_power]

        if globals.PPA_strategy == ac.PPA_Strategy_Dt.get('A1'):

            power_metric, perform_metric, area_metric = apply_second_norm(power_metric, perform_metric, area_metric)

            w_perf = 0.1
            w_area = 0.8
            w_power = 0.1

            param_set = [w_perf, w_area, w_power]

        elif globals.PPA_strategy == ac.PPA_Strategy_Dt.get('P2'):

            power_metric, perform_metric, area_metric = apply_second_norm(power_metric, perform_metric, area_metric)

            w_perf = 0.7
            w_area = 0.1
            w_power = 0.2

            param_set = [w_perf, w_area, w_power]

        base_ppa_loss = (param_set[0] * perform_metric) + (param_set[1] * area_metric) + (param_set[2] * power_metric)

        if wns < 0:

            loss_score = 6 + abs(wns)

        else:

            loss_score = base_ppa_loss

        print(f"[BO EVALUATION] Calculated Parameter Loss Score: {round(loss_score, 4)}")

        perform_metric = round(param_set[0] * perform_metric, 4)

        area_metric = round(param_set[1] * area_metric, 4)

        power_metric = round(param_set[2] * power_metric, 4)

    else:

        loss_score =  15

        perform_metric = 'NA'

        area_metric = 'NA'

        power_metric = 'NA'
    
    loss_score = round(loss_score, 4)

    globals.exploration_count += 1

    print(f"\nEXPLORATION COUNT =======: {globals.exploration_count} / {ac.MAX_OL_EXPLORATION}" )

    if globals.exploration_count > ac.MAX_OL_EXPLORATION:
        globals.exploration_count = 0

    log_run_metadata(globals.exploration_tag, CLOCK_PERIOD, FP_CORE_UTIL, PL_TARGET_DENSITY, SYNTH_STRATEGY, loss_score, globals.exploration_count, result, perform_metric, area_metric, power_metric)

    return loss_score

def log_run_metadata(timestamp, clk, util, density, strategy, loss_score, count, sts, clklss, arealss, powerlss):

    log_file = os.path.join(globals.local_folder, globals.design_name, f"optimization_history_manifest_ppa_{globals.timestamp_tag}.csv")
    
    file_exists = os.path.exists(log_file)
    
    with open(log_file, mode="a", newline="") as f:
        writer = csv.writer(f)
        # Write headers if it's a fresh file
        if not file_exists:
            writer.writerow(["Timestamp", "Clock_Period", "Core_Util", "Density", "Strategy", "Loss_Score", "Count", "Status", "clk_loss", "area_loss", "power_loss"])

            # Write range afterward headers

            param_range = [
                'Default range',
                f'{ac.dimensions[0].low}--{ac.dimensions[0].high}',
                f'{ac.dimensions[1].low}--{ac.dimensions[1].high}',
                f'{ac.dimensions[2].low}--{ac.dimensions[2].high}',
                f'{ac.dimensions[3].categories[0]}--{ac.dimensions[3].categories[1]}--{ac.dimensions[3].categories[2]}--{ac.dimensions[3].categories[3]}'
            ]

            writer.writerow(param_range)
        
        # Log the current run's profile
        writer.writerow([timestamp, clk, util, density, strategy, loss_score, count, sts, clklss, arealss, powerlss])

    print("LOG Exploration successfully.")

def openlane_plot_ex():

    ds_name = ac.design_list[0]

    # 1. Define the filename of your saved checkpoint
    checkpoint_filename = os.path.join(globals.local_folder, ds_name, "openlane_bo_result.pkl")

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
        plt.savefig(os.path.join(globals.local_folder, ds_name,"optimization_convergence_map.pdf"), bbox_inches='tight')
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

        # plt.savefig(os.path.join(globals.local_folder, ds_name,"optimization_search_space_map.pdf"), bbox_inches=pdf_crop_box)
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
    
