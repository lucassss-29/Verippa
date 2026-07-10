from itertools import combinations
from json import load
from tkinter import font
from weakref import ref
import gspread
import pandas as pd
from agent_config import authen_gsheet
import matplotlib.pyplot as plt
import numpy as np
import os
from agent_config import prj_dir, design_list
import math
import matplotlib.gridspec as gridspec
import matplotlib.font_manager as fm

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman"]


def plot_gsheet_to_csv(sheet_title, sheet_name):

    sheet = authen_gsheet(sheet_title, sheet_name)

    df = pd.DataFrame(sheet.get_all_records())

    df.to_csv(os.path.join(database_path, f'{sheet_name}.csv'), index=False)

    print(f"\nSave gsheet {sheet_name} to csv done.")


def plot_spider_one(org_sh, com_sh, candidate):

    angles = np.linspace(0, 2 * np.pi, len(indicators), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))

    csv_path1 = os.path.join(database_path, f"{org_sh}.csv")

    if not os.path.exists(csv_path1):

        plot_gsheet_to_csv(sh_title, org_sh)

    csv_path2 = os.path.join(database_path, f"{com_sh}.csv")

    if not os.path.exists(csv_path2):

        plot_gsheet_to_csv(sh_title, com_sh)

    # Create combined df
    df1 = pd.read_csv(csv_path1)
    df2 = pd.read_csv(csv_path2)

    row_data1 = df1[df1['design_name'] == candidate]
    row_data2 = df2[df2['design_name'] == candidate]

    combined_df = pd.concat([row_data1, row_data2], ignore_index=True)

    combined_df = combined_df.apply(pd.to_numeric, errors='ignore') 

    # combined_df.to_csv(f'./Report/Diagram/Database/combined_{candidate}.csv')

    # loaded_df = pd.read_csv(f'./Report/Diagram/Database/combined_{candidate}.csv')

    normed_df = normalize_drawing_data(combined_df, indicators)

    for index, row in normed_df.iterrows():

        values = row[indicators].tolist()

        values += values[:1]
    
        ax.plot(angles, values, linewidth=2, label=row['version'])

        ax.fill(angles, values, alpha=0.25)

    ax.set_theta_offset(np.pi / 2)

    ax.set_theta_direction(-1)

    ax.set_title(f"{candidate}", y=-0.15, fontsize=26)

    ax.set_xticks(angles[:-1])

    ax.set_xticklabels(indicator_cvt, fontsize=18)

    # Adjust label padding so they don't touch the outer circle
    ax.tick_params(axis='x', pad=25)

    # Set common legend
    handles, labels = ax.get_legend_handles_labels()

    # fig.legend(handles, labels, loc='lower center', ncol=len(labels), 
    #        bbox_to_anchor=(0.5, 0.02), frameon=False)
    
    plt.tight_layout()

    plt.subplots_adjust(top=0.95, bottom=0.05, left=0.18, right=0.82)
    
    # plt.show()

    plt.savefig(f'/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/{org_sh}_{com_sh}_{candidate}.pdf')

    print("Save diagram done.")


def plot_spider_diagram(compare_sh1, compare_sh2, list_draws, ch_title):

    # Generate spider angles
    angles = np.linspace(0, 2 * np.pi, len(indicators), endpoint=False).tolist()
    angles += angles[:1]

    fig, axes = plt.subplots(rows, cols, figsize=(20, rows * 5), subplot_kw=dict(polar=True))

    axes_flat = axes.flatten()

    # Create combined df by extract from each sheet
    csv_path1 = os.path.join(database_path, f"{compare_sh1}.csv")

    if not os.path.exists(csv_path1):

        plot_gsheet_to_csv(sh_title, compare_sh1)

    csv_path2 = os.path.join(database_path, f"{compare_sh2}.csv")

    if not os.path.exists(csv_path2):

        plot_gsheet_to_csv(sh_title, compare_sh2)

    # Create combined df
    df1 = pd.read_csv(csv_path1)
    df2 = pd.read_csv(csv_path2)

    # Start plotting, i equal to design name
    for i in range(total_charts):

        row_data1 = df1[df1['design_name'] == list_draws[i]]
        row_data2 = df2[df2['design_name'] == list_draws[i]]

        combined_df = pd.concat([row_data1, row_data2], ignore_index=True)

        normed_df = normalize_drawing_data(combined_df, indicators)

        # normed_df.to_csv(f'./Report/Diagram/Database/{ch_title}.csv')

        ax = axes_flat[i]

        one_of_design_fail = False

        for index, row in normed_df.iterrows():

            values = row[indicators].tolist()

            values += values[:1]

            # Plot each row
            if row['critical_path_ns'] == -1:

                ax.plot(angles, values, linewidth=2, label=row['version'], color='red')

            else:
                ax.plot(angles, values, linewidth=2, label=row['version'])

            ax.fill(angles, values, alpha=0.25)

            if (row['flow_status'] != 'flow completed'):

                one_of_design_fail = True

        # Rotate labels to be upright
        ax.set_theta_offset(np.pi / 2)

        ax.set_theta_direction(-1)

        if one_of_design_fail:
            # Add aesterisk to demonstate failure chart
            ax.set_title(f"{list_draws[i]}(*)", y=-0.1)
        
        else:
            ax.set_title(f"{list_draws[i]}", y=-0.1)

        ax.set_xticks(angles[:-1])

        ax.set_xticklabels(indicator_cvt, fontsize=10)

        # Adjust label padding so they don't touch the outer circle
        ax.tick_params(axis='x', pad=15)
    
    # This removes the 3 blank circles in the last row
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    # Set common legend
    handles, labels = axes_flat[0].get_legend_handles_labels()

    fig.legend(handles, labels, loc='lower center', ncol=len(labels), 
           bbox_to_anchor=(0.5, 0.02), frameon=False)

    fig.suptitle('Compare enhance performance metrics', fontsize=16)

    # add extra margin at the top
    plt.subplots_adjust(top=0.85)

    plt.tight_layout(rect=[0, 0.1, 1, 1], h_pad=3.0)

    plt.savefig(f'./Report/Diagram/Image/{ch_title}.png')

    print(f"Save diagram {ch_title} done.")

def plot_spider_layout(compare_sh1, compare_sh2, list_draws, ch_title):

    fig = plt.figure(figsize=(6, 6))

    # 1. Create the 2 "Big Columns" with a large horizontal gap (wspace)
    # Adjust wspace (e.g., 0.4 or 0.5) to make the middle gap wider
    outer_grid = gridspec.GridSpec(1, 2, wspace=0.4) 

    # 2. LEFT SIDE: 3 rows, 2 columns (6 images)
    left_inner = gridspec.GridSpecFromSubplotSpec(3, 2, subplot_spec=outer_grid[0], hspace=0.3, wspace=0.2)

    for i in range(6):
        ax = fig.add_subplot(left_inner[i // 2, i % 2], projection='polar')
        ax.set_title(f'Left {i+1}', fontsize=9)

    # 3. RIGHT SIDE: 3 rows, 2 columns (To match sizes exactly)
    right_inner = gridspec.GridSpecFromSubplotSpec(3, 2, subplot_spec=outer_grid[1], hspace=0.3, wspace=0.2)

    # Place 3 images in the right side
    # Image 1 & 2 (Row 0)
    fig.add_subplot(right_inner[0, 0], projection='polar').set_title('Right 1')
    fig.add_subplot(right_inner[0, 1], projection='polar').set_title('Right 2')

    # Image 3 (Row 1)
    fig.add_subplot(right_inner[1, 0], projection='polar').set_title('Right 3')

    # Note: We don't call fig.add_subplot for the remaining slots, 
    # so they remain empty, and the middle gap stays clean.

    plt.show()



def normalize_drawing_data(data, inds, ref_col='critical_path_ns'):

    df_scaled = data.copy()
    
    # 1. Get the average level of our reference (e.g., 2ns)
    ref_avg = data[ref_col].mean()
    
    for ind in inds:
        if ind == ref_col:
            continue
            
        # 2. Find the average of the current indicator (e.g., 0.000014)
        ind_avg = data[ind].mean()
        
        if ind_avg != 0:
            # 3. Calculate how much we need to 'boost' or 'shrink' it
            # Example: 2 / 0.000014 = ~142,857
            scale_factor = ref_avg / ind_avg
            
            # 4. Apply scale so it sits near the reference values visually
            df_scaled[ind] = data[ind] * scale_factor
        
    return df_scaled

def plot_duration_time_chart():
# Data
    data = {
        "accu": 2.12,
        "adder_16bit": 1.18,
        "adder_32bit": 6.58,
        "adder_8bit": 2.35,
        "adder_pipe_64bit": 3.5,
        "alu": 16.07,
        "asyn_fifo": 6.67,
        "calendar": 4.15,
        "counter_12": 3.31,
        "div_16bit": 12.58,
        "edge_detect": 1.78,
        "freq_div": 2.1,
        "fsm": 3.62,
        "JC_counter": 2.6,
        "multi_16bit": 4.63,
        "multi_booth_8bit": 6.69,
        "multi_pipe_4bit": 2.63,
        "multi_pipe_8bit": 4.81,
        "parallel2serial": 4.54,
        "pe": 6.95,
        "pulse_detect": 5.7,
        "radix2_div": 7.37,
        "RAM": 1.62,
        "right_shifter": 1.5,
        "serial2parallel": 14.04,
        "signal_generator": 5.31,
        "synchronizer": 1.79,
        "traffic_light": 13.17,
        "width_8to16": 6.39
    }

    # Prepare data - sort by duration
    designs = list(data.keys())
    durations = list(data.values())

    sorted_indices = np.argsort(durations)[::-1]   # This reverses the order
    sorted_designs = [designs[i] for i in sorted_indices]
    sorted_durations = [durations[i] for i in sorted_indices]

    # Calculate average
    average = np.mean(durations)
    # sum = np.sum(data.values())
    print(f"Average duration: {average:.2f} minutes")

    # Create the chart
    plt.figure(figsize=(9, 7))

    # Horizontal bar chart
    bars = plt.barh(sorted_designs, sorted_durations, color='#1e78b4', edgecolor='navy')

    # Add value labels on bars
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.2, bar.get_y() + bar.get_height()/2, 
                f'{width:.2f}', va='center', fontsize=10)

    # Add average line
    plt.axvline(x=average, color='red', linestyle='--', linewidth=2, label=f'Trung bình = {average:.2f} phút')

    # Labels and title
    plt.xlabel('Thời gian (phút)')

    plt.yticks(fontsize=10)

    plt.legend()
    # plt.grid(axis='x', alpha=0.3)

    plt.ylim(-0.6, len(sorted_designs) - 0.4)

    # Adjust layout
    plt.tight_layout()

    # Save the figure
    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/appendix/duration_time_chart.pdf')

    # plt.show()

database_path = os.path.join(prj_dir, "Report", "Diagram", "Database")

# Define PPA Indicators , 
indicators = ['critical_path_ns', 'power_typical_internal_uW', 'DIEAREA_mm^2']

indicator_cvt = ['CP(ns)', 'P_int(nW)','Die(um^2)']

sh_title = 'ppa_metrics_enhance'

# Calculate grid dimensions
total_charts = 4
cols = 4
rows = math.ceil(total_charts / cols)

sh_names = ['RTLLM_benchmark', 'Perf-v0', 'Perf-v1', 'Perf-v2', 'Perf-v3', 'Gemini-Perf-v3']

compare_1 = sh_names[0]

compare_2 = sh_names[4]

chart_title = f"scaled_{total_charts}_{compare_1}_{compare_2}_test"

# ds_list = ["synchronizer"]

# plot_spider_diagram(compare_1, compare_2, design_list, chart_title)

# plot_spider_one(compare_1, compare_2, 'multi_booth_8bit')

Perf_2_ds = ['accu', 'adder_pipe_64bit', 'fsm', 'multi_pipe_4bit', 'RAM']

Ge_2_ds = ['adder_32bit', 'adder_8bit', 'alu', 'fsm', 'pulse_detect', 'RAM', 'adder_pipe_64bit', 'multi_booth_8bit', 'serial2parallel']

# for i in range(len(Perf_2_ds)):

# plot_spider_one(compare_1, compare_2, 'alu')

# print(fm.findfont(fm.FontProperties(family='sans serif')))

# plot_duration_time_chart()

plot_duration_time_chart()