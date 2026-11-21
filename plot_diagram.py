from ast import mod
import enum
from itertools import combinations
from json import load
from tkinter import PanedWindow, font
from turtle import color
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
from matplotlib.markers import MarkerStyle
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
from scipy.interpolate import make_interp_spline
from adjustText import adjust_text
from matplotlib.ticker import StrMethodFormatter, MaxNLocator
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Patch
from matplotlib.patches import Polygon
import matplotlib.lines as mlines
import pickle
import gzip
from skopt import load

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman"]

plt.rcParams.update({'font.size': 12})

cs_colors = [
    '#4C78A8',  # Blue
    '#F58518',  # Orange
    '#54A24B',  # Green
    '#E45756',  # Red
    '#72B7B2',  # Teal
    '#B279A2'   # Purple
]

panel_blue = ["#2C4F76", "#4C78A8", "#7AA0CD", "#ABC9E9"]


plt.rcParams['axes.prop_cycle'] = plt.cycler(color=cs_colors)

def plot_gsheet_to_csv(sheet_title, sheet_name):

    sheet = authen_gsheet(sheet_title, sheet_name)

    df = pd.DataFrame(sheet.get_all_records())

    df.to_csv(os.path.join(database_path, f'{sheet_name}.csv'), index=False)

    print(f"\nSave gsheet {sheet_name} to csv done.")


def plot_spider_one(sh_file, org_sh, com_sh, candidate):

    # plt.style.use('grayscale')

    plt.rcParams['hatch.linewidth'] = 2.0


    # Define PPA Indicators , 
    indicators = ['suggested_clock_frequency', 'total_power', 'DIEAREA_mm^2']

    sh_title = sh_file

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

    power_cols = ['power_typical_internal_uW', 'power_typical_leakage_uW', 'power_typical_switching_uW']

    for col in power_cols:
        df1[col] = pd.to_numeric(df1[col], errors='coerce')
        df2[col] = pd.to_numeric(df2[col], errors='coerce')

    df1['total_power'] = df1[power_cols].sum(axis=1)
    df2['total_power'] = df2[power_cols].sum(axis=1)

    row_data1 = df1[df1['design_name'] == candidate]
    row_data2 = df2[df2['design_name'] == candidate]

    combined_df = pd.concat([row_data1, row_data2], ignore_index=True)

    combined_df = combined_df.apply(safe_to_numeric) 

    normed_df = normalize_drawing_data(combined_df, indicators)

    color = [cs_colors[0], cs_colors[1]]

    for (index, row), c in zip(normed_df.iterrows(), color):

        values = row[indicators].tolist()

        values += values[:1]
    
        ax.plot(angles, values, linewidth=3.5, label=row['version'], color=c)

        ax.fill(angles, values, alpha=0.25, color=c)


        if c == cs_colors[1]:

            ax.plot(angles, values, linewidth=2, label=row['version'], color=c)

            ax.fill(angles, values, hatch='//', facecolor=c, edgecolor='gray')

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

    plt.savefig(f'/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/radar_exploration/{org_sh}_{com_sh}_{candidate}.pdf')

    # print("Save diagram done.")

# Plot full design list between two sheets
# def plot_spider_diagram(compare_sh1, compare_sh2, list_draws, ch_title):

#     # Define PPA Indicators , 
#     indicators = ['suggested_clock_frequency', 'total_power', 'DIEAREA_mm^2']

#     # Generate spider angles
#     angles = np.linspace(0, 2 * np.pi, len(indicators), endpoint=False).tolist()
#     angles += angles[:1]

#     fig, axes = plt.subplots(rows, cols, figsize=(20, rows * 5), subplot_kw=dict(polar=True))

#     axes_flat = axes.flatten()

#     # print(len(axes_flat))

#     # # Create combined df by extract from each sheet
#     csv_path1 = os.path.join(database_path, f"{compare_sh1}.csv")

#     if not os.path.exists(csv_path1):

#         plot_gsheet_to_csv(sh_title, compare_sh1)

#     csv_path2 = os.path.join(database_path, f"{compare_sh2}.csv")

#     if not os.path.exists(csv_path2):

#         plot_gsheet_to_csv(sh_title, compare_sh2)

#     # Create combined df
#     df1 = pd.read_csv(csv_path1)
#     df2 = pd.read_csv(csv_path2)

#     # Start plotting, i equal to design name
#     for i in range(total_charts):

#         row_data1 = df1[df1['design_name'] == list_draws[i]]
#         row_data2 = df2[df2['design_name'] == list_draws[i]]

#         if row_data1['flow_status'].item() == "flow completed" and row_data2['flow_status'].item() == "flow completed":

#             combined_df = pd.concat([row_data1, row_data2], ignore_index=True)
    
#             combined_df = combined_df.apply(safe_to_numeric) 

#             normed_df = normalize_drawing_data(combined_df, indicators)

#             # normed_df.to_csv(f'./Report/Diagram/Database/{ch_title}.csv')

#             ax = axes_flat[i]

#             colors = [cs_colors[1], cs_colors[2]]

#             for (index, row), c in zip(normed_df.iterrows(), colors):

#                 values = row[indicators].tolist()

#                 values += values[:1]

#                 # Plot each row
#                 if row['critical_path_ns'] == -1:

#                     ax.plot(angles, values, linewidth=2, label=row['version'], color='red')

#                 else:
#                     ax.plot(angles, values, linewidth=2, label=row['version'], color=c)

#                     ax.fill(angles, values, alpha=0.25, color=c)

#             # Rotate labels to be upright
#             ax.set_theta_offset(np.pi / 2)

#             ax.set_theta_direction(-1)

#             ax.set_title(f"{list_draws[i]}", y=-0.1)

#             ax.set_xticks(angles[:-1])

#             ax.set_xticklabels(indicator_cvt, fontsize=10)

#             # Adjust label padding so they don't touch the outer circle
#             ax.tick_params(axis='x', pad=15)
    
#     # This removes the 3 blank circles in the last row
#     for j in range(i + 1, len(axes_flat)):
#         axes_flat[j].axis('off')

#     # # Set common legend
#     # axes_flat[1] some version failed at first design, change between 0 and 1
#     handles, labels = axes_flat[1].get_legend_handles_labels()

#     fig.legend(handles, labels, loc='lower center', ncol=len(labels), 
#         bbox_to_anchor=(0.5, 0.02), frameon=False)

#     fig.suptitle('Compare enhance performance metrics', fontsize=16)

#     # add extra margin at the top
#     plt.subplots_adjust(top=0.85)

#     plt.tight_layout(rect=[0, 0.1, 1, 1], h_pad=3.0)

#     plt.savefig(f'./Report/Diagram/Image/VerilogEval/{ch_title}.png')

#     # plt.show()

#     print(f"Save diagram {ch_title} done.") 

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



def normalize_drawing_data(data, inds, ref_col='suggested_clock_frequency'):

    df_scaled = data.copy()
    
    # 1. Get the average level of our reference (e.g., 2ns)
    ref_avg = data[ref_col].mean()

    print("ref_avg: ", ref_avg)
    
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

        
        print(f"{ind}: {df_scaled[ind]}")

    return df_scaled

def safe_to_numeric(s):
    try:
        return pd.to_numeric(s)
    except (ValueError, TypeError):
        return s

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


def rtllm_eval_general():

        # Data
    tools = ['RTLLM', 'VerilogEval']
    total = [29, 34]
    passed = [28, 34]
    failed = [1, 0]
    syntax_sim = [96.55, 100.0]   # percentages
    duration = [46.8, 79.96]      # seconds

    # Set up the figure with 3 subplots (1 row, 3 columns)
    fig, axes = plt.subplots(1, 3, figsize=(6, 4))

    # ---------------------------
    # Subplot 1: Counts (Total, Passed, Failed)
    # ---------------------------
    x = np.arange(len(tools))  # positions for groups
    widthg = 0.25
    width = 0.4              # width of each bar

    axes[0].bar(x - widthg, total, widthg, label='Total', color=panel_blue[3], hatch='\\\\\\')
    axes[0].bar(x, passed, widthg, label='Passed', color=panel_blue[2], hatch='..')
    axes[0].bar(x + widthg, failed, widthg, label='Failed', color=cs_colors[1])

    axes[0].set_ylabel('Số thiết kế')
    axes[0].set_title('Kết quả tổng quát', fontsize=12)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(tools, fontsize=9)
    axes[0].set_ylim(0, 50)
    axes[0].legend(fontsize=9)

    # Add value labels on bars (optional)
    for i, (t, p, f) in enumerate(zip(total, passed, failed)):
        axes[0].text(i - widthg, t + 0.5, str(t), ha='center', va='bottom', fontsize=9)
        axes[0].text(i, p + 0.5, str(p), ha='center', va='bottom', fontsize=9)
        axes[0].text(i + widthg, f + 0.5, str(f), ha='center', va='bottom', fontsize=9)

    # ---------------------------
    # Subplot 2: Syntax & Simulation Pass Rate (%)
    # ---------------------------

    custom_x = np.array([0.0, 0.6]) 

    axes[1].bar(tools, syntax_sim, color=panel_blue[2], width=width, hatch='\\\\\\\\')
    axes[1].set_ylim(0, 110)   # leave room for labels
    axes[1].set_xlabel('Benchmark')
    axes[1].set_ylabel('Tỉ lệ thành công (%)')
    axes[1].set_title('Tổng hợp Openlane', fontsize=12)
    axes[1].set_xlim(-0.5, 1.5)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(tools, fontsize=9)
 
    # Add percentage labels on bars
    for i, v in enumerate(syntax_sim):
        axes[1].text(i, v + 1, f'{v:.2f}%', ha='center', va='bottom', fontsize=9)

    # ---------------------------
    # Subplot 3: Duration (seconds)
    # ---------------------------
    axes[2].bar(tools, duration, color=cs_colors[1], width=width)
    axes[2].set_ylim(0, max(duration) + 10)
    axes[2].set_title('Thời gian (phút)', fontsize=12)
    axes[2].set_xlim(-0.5, 1.5)
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(tools, fontsize=9)


    # Add duration labels
    for i, v in enumerate(duration):
        axes[2].text(i, v + 0.5, f'{v:.2f}', ha='center', va='bottom', fontsize=9)

    # Adjust layout and display
    plt.tight_layout()
    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/rtllm_eval_general.pdf')

    # plt.show()


def plot_chart2():

    # ==========================
    # Data
    # ==========================
    models = ["ChatGPT", "Deepseek", "Gemini"]

    success_rate = [97.06, 91.18, 82.35]
    ppa_improvement = [41.18, 41.18, 38.24]

    # ==========================
    # Colors
    # ==========================
    background_color = "#D9D9D9"  # Gray background

    # ==========================
    # Create two small multiples
    # ==========================
    fig, axes = plt.subplots(
        1, 2,
        figsize=(5.5, 3),
        sharey=True
    )

    # Bar positions
    y = np.arange(len(models))

    # ==========================
    # Left chart: Success rate
    # ==========================
    ax1 = axes[0]

    # Full 100% gray background
    ax1.barh(
        y,
        [100] * len(models),
        height=0.68,
        color=background_color,
        edgecolor="none"
    )

    # Actual values overlaid
    bars1 = ax1.barh(
        y,
        success_rate,
        height=0.68,
        edgecolor="none",
        color=panel_blue[1]
    )

    # Add percentage labels
    for bar, value in zip(bars1, success_rate):
        ax1.text(
            value-2,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}%",
            va="center",
            ha="right"
        )

    ax1.set_title(
        "Tỉ lệ thành công",
        fontsize=13,
        # pad=12
    )

    ax1.set_yticks(y)
    ax1.set_yticklabels(models)

    # ==========================
    # Right chart: PPA improvement
    # ==========================
    ax2 = axes[1]

    # Full 100% gray background
    ax2.barh(
        y,
        [100] * len(models),
        height=0.68,
        color=background_color,
        edgecolor="none"
        
    )

    # Actual values overlaid
    bars2 = ax2.barh(
        y,
        ppa_improvement,
        height=0.68,
        color=cs_colors[1],
        edgecolor="none",
    )

    # Add percentage labels
    for bar, value in zip(bars2, ppa_improvement):
        ax2.text(
            value + 1.2,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}%",
            va="center",
            ha="left"
        )

    ax2.set_title(
        "Cải thiện PPA",
        fontsize=13,
        # pad=12
    )

    # Show model names on the second panel too
    ax2.set_yticks(y)
    ax2.set_yticklabels(models)

    # ==========================
    # Common formatting
    # ==========================
    for ax in axes:

        # X-axis range
        ax.set_xlim(0, 108)

        # Remove unnecessary borders
        ax.set_frame_on(False)

        # Remove y-axis tick marks
        ax.tick_params(
            axis="y",
            length=0
        )

        ax.set_xticks([])
        ax.set_xticklabels([])

    # Put ChatGpt at the top
    ax1.invert_yaxis()

    plt.tight_layout()

    description = ("Benchmark VerilogEval")

    fig.text(
    0.55, 0.1, description,
    wrap=True, 
    ha='center', 
    va='bottom', fontsize=12)
    
    plt.tight_layout(rect=[0, 0.12, 1, 1])

    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/chart2.pdf')

    # plt.show()
    

def plot_chart3():

    marker_size = 65

    # Data
    versions = [1, 2, 2.1]
    improvement = [47.06, 41.18, 38.24]
    improvement_draw = [47.06, 41.18, 36.24]
    labels = ["ChatGPT", "Deepseek", "Gemini"]

    wing_star = MarkerStyle((4, 1, 45))

    # V1, V3, V3
    versions_2 = [0.1, 0.2, 1.1]
    improvement_2 = [35.29, 32.35, 23.53]
    improvement_2_draw = [35.29, 29.35, 23.53]

    versions_3 = [2.1, 2.2, 2.3]
    improvement_3 = [101.89, 95.35, 98.24]
    improvement_3_draw = [101.89, 88.35, 95.24]


    # Create figure
    fig, ax = plt.subplots(figsize=(6, 4))

    # Plot 1
    # Scatter plot with star markers
    plt.scatter(
        versions,
        improvement_draw,
        marker='*',
        s=marker_size,          # Marker size
        label="Mô hình tốt nhất",
        color=panel_blue[0]
    )

    #Plot 2
    plt.scatter(
        versions_2,
        improvement_2_draw,
        marker=wing_star,
        s=marker_size,          # Marker size
        label="Mô hình thấp nhất",
        color=panel_blue[2]
    )

    #Plot 3
    plt.scatter(
        versions_3,
        improvement_3_draw,
        s=marker_size-15,          # Marker size
        label="Kết hợp*",
        color=cs_colors[1]
    )

    # Annotate each point
    for x, y, label in zip(versions, improvement, labels):
        if y == 38.24:
            plt.annotate(
            text=f"{label} {y}%",
            xy=(x, 36.24),
            xytext=(10, 0),
            textcoords="offset points",
            ha="left",
            va="center"
        )
        else:
            plt.annotate(
                text=f"{label} {y}%",
                xy=(x, y),
                xytext=(10, 0),
                textcoords="offset points",
                ha="left",
                va="center"
            )

    for x2, y2, label2 in zip(versions_2, improvement_2, labels):

        if y2 == 32.35:
            plt.annotate(
            text=f"{label2} {y2}%",
            xy=(x2, 29.35),
            xytext=(10, 0),
            textcoords="offset points",
            ha="left",
            va="center"
        )
        else:
            plt.annotate(
                text=f"{label2} {y2}%",
                xy=(x2, y2),
                xytext=(10, 0),
                textcoords="offset points",
                ha="left",
                va="center"
            )

    for x3, y3, label3 in zip(versions_3, improvement_3, labels):

        if y3 == 95.35:
            plt.annotate(
            text=f"{label3} {y3}%",
            xy=(x3, 88.35),
            xytext=(10, 0),
            textcoords="offset points",
            ha="left",
            va="center"
        )
        elif y3 == 98.24:
            plt.annotate(
            text=f"{label3} {y3}%",
            xy=(x3, 95.35),
            xytext=(10, 0),
            textcoords="offset points",
            ha="left",
            va="center"
        )
        else:
            plt.annotate(
                text=f"{label3} {y3}%",
                xy=(x3, y3),
                xytext=(10, 0),
                textcoords="offset points",
                ha="left",
                va="center"
            )

    # Labels and title
    plt.xlabel("Mức độ phức tạp của prompt", loc="center")
    plt.ylabel("Tỉ lệ cải thiện (%)",loc="top")


    # Chart 3: So sánh mức độ hiệu quả cao nhất trên benchmark VerilogEval (scatter plot)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_position('zero')
    ax.spines['bottom'].set_position('zero')
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.plot(1, 0, ">k", transform=ax.get_yaxis_transform(), clip_on=False)
    ax.plot(0, 1, "^k", transform=ax.get_xaxis_transform(), clip_on=False)

    ax.set_xticks([0.2, 2.7])
    ax.set_yticks([])

    ax.set_xticklabels(["Thấp", "Cao"])
    ax.set_yticklabels([])

    
    # plt.ylim(10, 120)
    plt.xlim(0, 3)

    plt.legend()
    plt.tight_layout()

    fig.subplots_adjust(bottom=0.2)

    description = ("(*) Kết hợp trên cả hai bộ benchmark RTLLM và VerilogEval.")

    fig.text(
    0.05, 0.005, description,
    wrap=True, 
    ha='left', 
    va='bottom', fontsize=11)

    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/chart3.pdf')

    # plt.show()

def plot_chart4():
    models = ["ChatGPT", "Deepseek", "Gemini"]
    success = [47.06, 41.18, 38.24]
    failure = [2.94, 8.82, 17.65]
    tokens = [139503, 1159712, 8147909]

    x = np.arange(len(models))
    width = 0.24

    # -------------------------
    # Figure
    # -------------------------
    fig, ax1 = plt.subplots(figsize=(6, 4))

    # -------------------------
    # Bar chart
    # -------------------------
    bars1 = ax1.bar(
        x - width/2,
        success,
        width,
        label="Hiệu quả (%)",
        color=panel_blue[0]
    )

    bars2 = ax1.bar(
        x + width/2,
        failure,
        width,
        label="Thất bại (%)",
        color=panel_blue[2]
    )

    # Left Y-axis
    ax1.set_xlim(-0.8, 2.8)
    ax1.set_ylim(0, 60)
    ax1.set_ylabel("Mức độ cải thiện critical path (%)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(models)
    ax1.set_xlabel("Mô hình LLM")
    # ax1.set_yticks(np.arange(0, 101, 20))

    # Grid
    # ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.set_axisbelow(True)

    # -------------------------
    # Secondary axis (Tokens)
    # -------------------------
    ax2 = ax1.twinx()

    line = ax2.plot(
        x,
        tokens,
        marker='o',
        linewidth=2.5,
        markersize=5,
        color = cs_colors[3],
        label="Token (số lượng)"
    )

    ax2.set_ylim(0, 10000000)
    ax2.set_ylabel("Token (đơn vị: triệu)")
    ax2.set_yticks([2000000, 4000000, 6000000, 8000000, 10000000])

    ax2.yaxis.set_major_formatter(
    FuncFormatter(lambda x, pos: f"{x/1000000:.0f}M")
    )
    #  Chart 4: Mối quan hệ giữa token và độ hiệu quả các mô hình (combine line vs group bar)

    # -------------------------
    # Labels on bars
    # -------------------------
    for bar in bars1:
        h = bar.get_height()

        if h == 38.24:
            ax1.text(
            bar.get_x() + bar.get_width()/2 + 0.2,
            h + 2,
            f"{h:.2f}%",
            ha="center",
            va="bottom",
            fontsize=10
        )
        else:
            ax1.text(
                bar.get_x() + bar.get_width()/2 + 0.05,
                h + 2,
                f"{h:.2f}%",
                ha="center",
                va="bottom",
                fontsize=10
            )

    for bar in bars2:
        h = bar.get_height()
        if h == 8.82:
            ax1.text(
            bar.get_x() + bar.get_width()/2 + 0.2,
            h + 1.5,
            f"{h:.2f}%",
            ha="center",
            va="bottom",
            fontsize=10
        )
        else:
            ax1.text(
                bar.get_x() + bar.get_width()/2 + 0.05,
                h + 1.5,
                f"{h:.2f}%",
                ha="center",
                va="bottom",
                fontsize=10
            )

    # -------------------------
    # Labels on line
    # -------------------------
    for xi, yi in zip(x, tokens):

        if yi == 8147909:
            ax2.annotate(
            f"{yi:,}",
            (xi, yi),
            xytext=(8, 10),
            textcoords="offset points",
            fontsize=10,
        )
        else:
            ax2.annotate(
                f"{yi:,}",
                (xi, yi),
                xytext=(-60, 25),
                textcoords="offset points",
                fontsize=10,
                ha="left",
                va="bottom",
                arrowprops=dict(
                    arrowstyle="-",       # straight line, no arrow head
                    linewidth=1,
                    color="gray"
            ))

    # -------------------------
    # Legend
    # -------------------------

    square1 = Line2D(
    [0], [0],
    marker='s',
    color='w',
    markerfacecolor=panel_blue[0],
    markersize=10,
    label="Hiệu quả (%)"
)

    square2 = Line2D(
        [0], [0],
        marker='s',
        color='w',
        markerfacecolor=panel_blue[1],
        markersize=10,
        label="Thất bại (%)"
    )

    legend_line = Line2D(
    [0],
    [0],
    color=cs_colors[3],
    linewidth=2,
    linestyle='-',
    marker=None,
    label="Tokens"
)

    ax1.legend(
        handles=[square1, square2, legend_line],
        labels=["Hiệu quả (%)", "Thất bại (%)", "Token (số lượng)"],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=3,
        frameon=False,
        fontsize=9
    )

    # Remove top spines for cleaner style
    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)

    plt.tight_layout()
    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/chart4.pdf')

    # plt.show()

def plot_chart5():
    # -----------------------------
    # Data
    # -----------------------------
    categories = ["Cú pháp", "Mô phỏng", "Openlane"]
    x = np.arange(len(categories))

    pass1 = {
        "ChatGPT": [87.93, 55.18, 50.00],
        "Deepseek": [75.86, 29.31, 36.21],
        "Gemini": [84.48, 43.11, 32.76]
    }

    pass5 = {
        "ChatGPT": [100.00, 98.28, 98.28],
        "Deepseek": [98.28, 84.48, 86.21],
        "Gemini": [98.28, 86.21, 84.48]
    }

    # -----------------------------
    # Figure
    # -----------------------------
    fig, ax = plt.subplots(figsize=(6, 4))

    reset_color = [
    panel_blue[0],
    panel_blue[1],
    '#F58518',  # Orange
    ]

    marker_ls = ['s', '^', 'o']

    # Plot pass@1 (solid)
    for i,model in enumerate(pass1):
        ax.plot(
            x,
            pass1[model],
            color=reset_color[i],
            marker=marker_ls[i],
            linewidth=1.5,
            label=f"{model} pass@1"
        )


    # Plot pass@5 (dashed)
    for i, model in enumerate(pass5):
        ax.plot(
            x,
            pass5[model],
            marker=marker_ls[i],
            linewidth=1.5,
            linestyle='--',
            color=reset_color[i],
            label=f"{model} pass@5"
        )

    # -----------------------------
    # Value labels
    # -----------------------------
    # for model in pass1:
    for xi, yi in zip(x, pass1['Deepseek']):

        if yi == 29.31:
            ax.text(
            xi,
            yi - 5,
            f"{yi:.2f}%",
            ha='center',
            fontsize=9
        )
        else:
            ax.text(
                xi,
                yi + 3,
                f"{yi:.2f}%",
                ha='center',
                fontsize=9
            )

    for xi, yi in zip(x, pass1['ChatGPT']):

        if yi == 55.18:
            ax.text(
            xi+0.05,
            yi + 3,
            f"{yi:.2f}%",
            ha='center',
            fontsize=9
        )
        else:
            ax.text(
                xi,
                yi + 3,
                f"{yi:.2f}%",
                ha='center',
                fontsize=9
            )

    for xi, yi in zip(x, pass5['ChatGPT']):
        ax.text(
            xi,
            yi + 5,
            f"{yi:.2f}%",
            ha='center',
            fontsize=9
        )

    # -----------------------------
    # Formatting
    # -----------------------------
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize = 11)

    ax.set_ylim(0, 110)
    ax.set_xlim(-0.2, 2.2)
    ax.set_ylabel("Tỉ lệ thành công (%)")
    ax.set_xlabel("Giá trị pass@k qua các giai đoạn")

    # Biểu đồ so sánh pass@1 và pass@5 giữa các mô hình

    ax.grid(axis='y', linestyle='--', alpha=0.4)

    # ==========================
    # Legend 1: Models (Colors)
    # ==========================
    model_handles = [
        Line2D([0], [0], marker=marker_ls[0], color=reset_color[0]),
        Line2D([0], [0], marker=marker_ls[1], color=reset_color[1]),
        Line2D([0], [0], marker=marker_ls[2], color=reset_color[2])
    ]

    legend1 = ax.legend(
        model_handles,
        ["ChatGPT", "Deepseek", "Gemini"],
        # title="Model",
        loc="upper left",
        bbox_to_anchor=(-0.05, -0.15),
        ncol = 3,
        columnspacing=0.7, handletextpad=0.2,
        frameon=False,
    )

    # Keep first legend
    ax.add_artist(legend1)

    # ==========================
    # Legend 2: Line Styles
    # ==========================
    style_handles = [
        Line2D([0], [0], color="black", lw=1, linestyle='-'),
        Line2D([0], [0], color="black", lw=1, linestyle='--')
    ]

    ax.legend(
        style_handles,
        ["pass@1", "pass@5"],
        # title="Metric",
        loc="upper left",
        bbox_to_anchor=(0.65, -0.15),
        columnspacing=1, handletextpad=0.5,
        ncol = 2,
        handlelength=1.0,
        frameon=False
    )


    # Clean up
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    # plt.subplots_adjust(bottom=0.15)

    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/chart5.pdf')

    # plt.show()


def plot_deepseek_v0v1v2():
    # Data
    versions = ["Perf-v0", "Perf-v1", "Perf-v2"]

    improved = [37.50, 30.00, 54.00]
    worse = [12.50, 22.22, 8.33]
    unchanged = [50.00, 48.15, 37.50]
    failed = [17.24, 6.90, 17.24]

    # X positions
    x = np.arange(len(versions))
    width = 0.22

    fig, ax1 = plt.subplots(figsize=(6, 4))

    # ======================
    # Grouped Bar Chart
    # ======================
    bar1 = ax1.bar(x - width, improved, width, label="Cải thiện", color=panel_blue[0])
    bar2 = ax1.bar(x, worse, width, label="Xấu hơn", color=panel_blue[1])
    bar3 = ax1.bar(x + width, unchanged, width, label="Không thay đổi", color=panel_blue[2])

    for bars in [bar1, bar2, bar3]:
        ax1.bar_label(
            bars,
            fmt="%.1f%%",
            padding=2,
            fontsize=8
        )

    ax1.set_xlabel("Mô hình Deepseek")
    ax1.set_ylabel("Tỉ lệ phần trăm (%)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(versions)
    ax1.set_ylim(0, 60)

    # ======================
    # Line Chart (Secondary Y-axis)
    # ======================
    # Secondary axis
    ax2 = ax1.twinx()

    # Smooth curve
    x_smooth = np.linspace(x.min(), x.max(), 300)
    y_smooth = make_interp_spline(x, failed, k=2)(x_smooth)
    # k=2 because you only have 3 data points
    # (k=3 requires at least 4 points)

    # Plot smooth curve
    ax2.plot(
        x_smooth,
        y_smooth,
        color=cs_colors[3],
        linewidth=2.5,
        label="Thất bại"
    )

    # Plot original markers
    ax2.plot(
        x,
        failed,
        color=cs_colors[3],
        marker="o",
        linestyle="None"
    )

    ax2.set_ylabel("Tỉ lệ thất bại (%)")
    ax2.set_ylim(0, 20)
    ax2.set_yticks(np.linspace(0, 25, 6))

    # ======================
    # Legend
    # ======================
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        handles1 + handles2,
        labels1 + labels2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=4,
        fontsize=9,
        frameon=False
    )
    #  Phân tích độ tối ưu thông qua Perf-v0, Perf-v1, và Perf-v2 trên mô hình Deepseek bộ benchmark RTLLM
    plt.tight_layout()

    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/chart_deepseek_v0v1v2.pdf')

    # plt.show()

def plot_chart6_panel():
        # ----------------------------
    # Data
    # ----------------------------

    panel_color = ["#2C4F76", "#4C78A8", "#7AA0CD"]
    baseline_verippa = [90.69, 53.62, 34.84]
    proposed_verippa = [100.00, 98.28, 44.20]

    baseline_rtlopt = [97.20, 75.00, 21.09]
    proposed_rtlopt = [100.00, 98.28, 44.20]

    metrics = ["Cú pháp", "Chức năng", "Cải thiện PPA"]

    # ----------------------------
    # Create figure
    # ----------------------------
    fig, axes = plt.subplots(
        1, 2,
        figsize=(6, 4)
        # sharey=True
    )


    # ==================================================
    # Panel 1: VeriPPA
    # ==================================================
    ax = axes[0]

    x = [0, 1]

    ax.vlines(
        x,
        ymin=0,
        ymax=110,
        color="lightgray",
        linewidth=1
    )

    for metric, y1, y2, c in zip(
            metrics,
            baseline_verippa,
            proposed_verippa, panel_color):
        
        if metric == metrics[1]:
            ax.plot(
            x,
            [y1, 95],
            marker="o",
            markersize=5,
            linewidth=2,
            color=c,
            label=metric
        )
        else:

            ax.plot(
                x,
                [y1, y2],
                marker="o",
                markersize=5,
                linewidth=2,
                label=metric,
                color=c
            )

        ax.text(
            0,
            y1-2,
            f"{y1:.2f}%",
            ha="left",
            va="top",
            fontsize=9
        )

        if y2 == 98.28:
            ax.text(
            1.03,
            95+2,
            f"{y2:.2f}%",
            ha="left",
            va="center",
            fontsize=9
        )
        else:
            ax.text(
                1.03,
                y2+2,
                f"{y2:.2f}%",
                ha="left",
                va="center",
                fontsize=9
            )


    ax.text(
        0,
        112,
        "VeriPPA",
        ha="center"
    )

    ax.text(
        1,
        112,
        "Nghiên cứu này",
        ha="center"
    )

    # ax.set_xticks([0, 1])
    ax.set_xticklabels([])
    ax.tick_params(axis="x", length=0)

    ax.set_yticks([90, 53, 34], labels=["Cú pháp *", "Chức năng", "Cải thiện PPA"])

# 3. Loop through and apply the colors
    for label, color in zip(ax.get_yticklabels(), panel_color):
        label.set_color(color)
        label.set_weight("semibold")

    ax.set_xlim(-0.3, 1.3)
    ax.set_ylim(0, 110)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)


    # ==================================================
    # Panel 2: RTL-OPT
    # ==================================================
    ax = axes[1]

    x = [0, 1]

    ax.vlines(
        x,
        ymin=0,
        ymax=110,
        color="lightgray",
        linewidth=1
    )

    for metric, y1, y2, c in zip(
            metrics,
            baseline_rtlopt,
            proposed_rtlopt, panel_color):
        
        if metric == metrics[1]:

            ax.plot(
            x,
            [y1, 95],
            marker="o",
            markersize=5,
            linewidth=2,
            label=metric,
            color=c
        )
        else:

            ax.plot(
                x,
                [y1, y2],
                marker="o",
                markersize=5,
                linewidth=2,
                label=metric,
                color=c
            )

        ax.text(
            0,
            y1-2,
            f"{y1:.2f}%",
            ha="left",
            va="top",
            fontsize=9
        )

        if y2 == 98.28:
            ax.text(
            1.03,
            95+2,
            f"{y2:.2f}%",
            ha="left",
            va="center",
            fontsize=9
        )
        else:

            ax.text(
                1.03,
                y2+2,
                f"{y2:.2f}%",
                ha="left",
                va="center",
                fontsize=9
            )

    ax.text(
        0,
        112,
        "RTL-OPT",
        ha="center"
    )

    ax.text(
        1,
        112,
        "Nghiên cứu này",
        ha="center"
    )

    # ax.set_xticks([0, 1])
    ax.set_xticklabels([])
    ax.tick_params(axis="x", length=0)

    axes[1].set_yticklabels([])
    ax.tick_params(axis="y", length=0)

    ax.set_xlim(-0.3, 1.3)
    ax.set_ylim(0, 110)

    ax.set_frame_on(False)

    # fig.subplots_adjust(bottom=0.2)

    description = ("(*) Trong khi VeriPPA sử dụng ChatGPT4, RTL-OPT dùng ChatGPT-4o-mini và nghiên cứu này dùng ChatGPT-5.4.")

    fig.text(
    0.2, 0.03, description,
    wrap=True, 
    ha='left', 
    va='bottom', fontsize=10)
    
    plt.tight_layout(rect=[0, 0.15, 1, 1])

    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/chart6_panel.pdf')

    # plt.show()

def plot_dumbbell_expl():
    # Data (remove '%' and convert to float)
    data = {
        "design": [
            "fsm_hdlc", "fsm_onehot", "fsm_ps2data", "fsm_serialdata",
            "fsm2", "fsm2s", "fsm3comb", "fsm3s",
            "gatesv", "gatesv100", "gshare", "kmap4",
            "lemmings2", "lemmings3", "lemmings4", "lfsr32", "m2014_q4k"
        ],
        # Frequency
        "freq_perf": [
            120.07, 150.00, 120.07, 150.00,
            120.07, 120.07, 150.00, 150.00,
            150.00, 150.00, 95.77, 120.07,
            150.00, 150.00, 150.00, 120.07, 150.00
        ],
        "freq_ppa": [
            33.33, 33.33, 32.26, 33.33,
            33.33, 33.33, 33.33, 33.33,
            33.33, 0.00, 5.26, 33.33,
            33.33, 33.33, 18.57, 33.33, 33.14
        ],
        # Power
        "pow_perf": [
            548.84, 55.28, 349.20, 368.23,
            214.87, 335.13, 55.68, 569.58,
            50.86, 28.94, 147.20, 56.95,
            417.19, 337.80, 164.87, 387.79, 637.04
        ],
        "pow_ppa": [
            46.52, 0.76, 75.17, 62.24,
            27.80, 23.45, 15.59, 30.52,
            12.75, 0.00, 29.79, 9.59,
            66.21, 71.89, 22.05, 34.00, 30.36
        ],
        # Area
        "area_perf": [
            -97.51, -89.24, -95.10, 99.30,
            -45.29, -39.55, -68.80, -93.60,
            -85.27, -84.48, 35.81, -36.86,
            -92.75, -96.06, 91.65, 33.22, -90.92
        ],
        "area_ppa": [
            -97.87, 0.00, -95.64, 82.81,
            -80.14, -85.45, -72.24, -94.68,
            -94.71, 0.00, 8.60, -86.05,
            -93.75, -96.10, 49.41, 9.07, -94.64
        ]
    }

    df = pd.DataFrame(data)

    FONTSIZE = 10

    # Keep original order
    y_pos = np.arange(len(df))
    designs = df["design"]

    # Create 3 subplots side by side with a compact size
    fig, axes = plt.subplots(1, 3, figsize=(6, 4), sharey=True)

    # Metrics configuration
    metrics = [
        (df["freq_perf"], df["freq_ppa"], "Cải thiện tần số", "Percent"),
        (df["pow_perf"], df["pow_ppa"], "Cải thiện công suất", "Percent"),
        (df["area_perf"], df["area_ppa"], "Cải thiện diện tích", "Percent")
    ]

    for ax, (perf, ppa, title, xlabel) in zip(axes, metrics):
        # Connecting lines
        for i, (p1, p2) in enumerate(zip(perf, ppa)):
            ax.plot([p1, p2], [i, i], color='gray', linewidth=1.5, alpha=0.6)

        # Dots
        ax.scatter(ppa, y_pos, color=cs_colors[0], s=30, label='Cân bằng PPA', zorder=3)

        ax.scatter(perf, y_pos, color=cs_colors[1], s=30, label='Ưu tiên hiệu năng', zorder=3, marker='^')
        

        # (Value labels omitted to save space – uncomment if needed)
        # for i, (p1, p2) in enumerate(zip(perf, ppa)):
        #     ax.text(p1, i+0.2, f'{p1:.0f}%', fontsize=5, ha='center', va='bottom', color='#1f77b4')
        #     ax.text(p2, i-0.2, f'{p2:.0f}%', fontsize=5, ha='center', va='top', color='#d62728')

        ax.axvline(0, color='black', linewidth=0.6, linestyle='--', alpha=1)
        ax.set_title(title, fontsize = 11)
        ax.tick_params(axis='x', labelsize=FONTSIZE)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.xaxis.set_major_formatter(StrMethodFormatter('{x:.0f}%'))
        ax.grid(axis='x', linestyle='--', alpha=0.5, zorder=0)

    # y-ticks only on first subplot (sharey=True replicates them)
    axes[0].set_yticks(y_pos)
    axes[0].set_yticklabels(designs, fontsize=FONTSIZE)

    # Legend – place below the plots to save space
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, 0.02), ncol=2, markerscale=1.5, frameon=False)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.2, wspace=0.3)  # make room for legend
    # plt.show()
    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/dumbbell_verilogEval_ex.pdf')


def plot_area_gradient():
    # 1. Define the dataset
    categories = ['Hiệu suất', 'Năng lượng', 'Diện tích']
    x_indices = np.arange(len(categories))

    data_series = {
        'Ưu tiên hiệu năng': [118.94, 187.53, -12.96],
        'Cân bằng PPA': [26.27, 37.39, -27.17],
        'Bản ban đầu': [5.29, 7.49, 0.29]
    }

    colors = {
        'Ưu tiên hiệu năng': cs_colors[3],  # Blue
        'Cân bằng PPA': cs_colors[2],         # Green
        'Bản ban đầu': panel_blue[1]       # Orange
    }

    # 2. Set up the figure with requested size (6, 4)
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)

    # Define baseline Y-limit slightly below minimum data to accommodate gradient mapping
    y_min, y_max = -40, 230

    # 3. Plot each series with a line and a clipping gradient path
    for label, y_values in data_series.items():
        color = colors[label]
        
        # Plot the distinct top line
        ax.plot(categories, y_values, label=label, color=color, linewidth=2.5, marker='o', zorder=3)
        
        # Construct a polygon path tracing from 0 baseline up to the line data points
        path_data = (
            [(x_indices[0], 0)] + 
            list(zip(x_indices, y_values)) + 
            [(x_indices[-1], 0), (x_indices[0], 0)]
        )
        codes = [Path.MOVETO] + [Path.LINETO] * (len(path_data) - 1)
        path = Path(path_data, codes)
        patch = PathPatch(path, facecolor='none', edgecolor='none')
        ax.add_patch(patch)
        
        # Generate custom vertical colormap fading from the line color to completely transparent
        cmap = LinearSegmentedColormap.from_list('fade', [(1, 1, 1, 0), color])
        
        # Display the gradient mesh restricted entirely within our line boundary mask
        im = ax.imshow(
            np.array([[0, 1], [0, 1]]).T, cmap=cmap, interpolation='bicubic',
            origin='lower', extent=[x_indices[0], x_indices[-1], min(0, min(y_values)), max(0, max(y_values))],
            aspect='auto', clip_path=patch, clip_on=True, alpha=0.45, zorder=2
        )

    perf_driven_data = data_series['Ưu tiên hiệu năng']

    # Label for 118.94% (Index 0: Performance)
    ax.annotate(
        f'{perf_driven_data[0]}%', 
        xy=(0, perf_driven_data[0]), 
        xytext=(0, 8),               # Offset text 8 points straight up from the marker
        textcoords="offset points", 
        ha='center', va='bottom', 
        fontsize=9, fontweight='bold', color=colors['Ưu tiên hiệu năng']
    )

    ax.annotate(
    f'{perf_driven_data[1]}%', 
    xy=(1, perf_driven_data[1]), 
    xytext=(0, 8),               # Offset text 8 points straight up from the marker
    textcoords="offset points", 
    ha='center', va='bottom', 
    fontsize=9, fontweight='bold', color=colors['Ưu tiên hiệu năng']
    )

    ppa_balance_data = data_series['Cân bằng PPA']

    ax.annotate(f'{ppa_balance_data[0]}%', xy=(0, ppa_balance_data[0]), xytext=(0, 8), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold', color=colors['Cân bằng PPA'])

    ax.annotate(f'{ppa_balance_data[1]}%', xy=(1, ppa_balance_data[1]), xytext=(0, 8), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold', color=colors['Cân bằng PPA'])

    # 4. Clean up chart layout
    ax.axhline(0, color='#888888', linewidth=1, linestyle='--', zorder=1) # 0% baseline
    ax.set_ylim(y_min, y_max)
    padding = 0.2
    ax.set_xlim(x_indices[0] - padding, x_indices[-1] + padding)
    ax.set_ylabel('Tỉ lệ cải thiện (%)')
    # ax.set_title('PPA Summary Comparison', fontsize=12, fontweight='bold', pad=15)
    ax.set_xticks(x_indices)
    ax.set_xticklabels(categories)

    # Format Y-axis with percent signs
    ax.yaxis.set_major_formatter(lambda x, pos: f'{int(x)}%')

    legend_elements = [
        Patch(facecolor=colors['Ưu tiên hiệu năng'], edgecolor='none', label='Ưu tiên hiệu năng'),
        Patch(facecolor=colors['Cân bằng PPA'], edgecolor='none', label='Cân bằng PPA'),
        Patch(facecolor=colors['Bản ban đầu'], edgecolor='none', label='Bản ban đầu')
    ]

    ax.legend(
    handles=legend_elements,
    loc='upper center', 
    bbox_to_anchor=(0.5, -0.15), 
    ncol=3, 
    frameon=True, 
    facecolor='white', 
    edgecolor='#e0e0e0',
    handlelength=1.0,
    handleheight=1.0
    )

    ax.grid(True, axis='y', linestyle=':', alpha=0.5, zorder=0)
    ax.set_facecolor('#fafafa')

    plt.tight_layout()
    plt.show()

def plot_area_gradient_colorbar():
    # 1. Define the data
    metrics = ['Hiệu năng', 'Công suất', 'Diện tích']
    x = np.arange(len(metrics))

    datasets = {
        'Ưu tiên hiệu năng': [118.94, 187.53, -12.96],
        'Cân bằng PPA': [26.27, 37.39, -27.17],
        'Bản ban đầu': [5.29, 7.49, 0.29]
    }


    colors = {
    'Ưu tiên hiệu năng': {
        'line': cs_colors[1], 
        # Fades from 00 (Fully transparent red) to FF (Solid red)
        'grad': ['#E4575600', "#F46C0BFF"] 
    },
    'Cân bằng PPA': {
        'line': '#2C4F76', 
        # Fades from 00 (Fully transparent navy) to FF (Solid navy)
        'grad': ['#2C4F7600', '#2C4F76FF'] 
    }, 
    'Bản ban đầu': {
        'line': '#4C78A8', 
        # Fades from 00 (Fully transparent blue) to FF (Solid blue)
        'grad': ['#4C78A800', '#4C78A8FF'] 
    } 
}
    marker_ls = ['o', 's', '^']

    # 2. Initialize the figure with the required size (6, 4)
    fig, ax = plt.subplots(figsize=(6, 4))

    # Find absolute plotting bounds with padding
    all_values = [v for data in datasets.values() for v in data]
    ymin = min(all_values) - 30
    ymax = max(all_values) + 40

    ax.set_xlim(0, len(metrics) - 1)
    ax.set_ylim(ymin, ymax)

    x_dense = np.linspace(0, len(metrics) - 1, 200)

    # 3. Plot each dataset sequentially with its unique gradient mask
    for (label, values), marker in zip(datasets.items(), marker_ls):
        # Draw boundary line
        ax.plot(x, values, color=colors[label]['line'], linewidth=1.5, label=label, zorder=3, marker=marker)
        
        # Smooth interpolating curve for clipping path
        y_upper = np.interp(x_dense, x, values)
        poly_vertices = [(0, ymin)] + list(zip(x_dense, y_upper)) + [(len(metrics) - 1, ymin)]
        
        # Safe geometric polygon mask
        clip_polygon = Polygon(poly_vertices, facecolor='none', edgecolor='none')
        ax.add_patch(clip_polygon)
        
        # Custom color gradient mapping
        cmap = LinearSegmentedColormap.from_list(f'grad_{label}', colors[label]['grad'])

        y_grid = np.linspace(ymin, ymax, 100)
        grid_data = ((y_grid - ymin) / (ymax - ymin)) ** 5
        grid_matrix = grid_data[:, np.newaxis]
        
        # Overlay transparent 2D gradient mesh
        im = ax.imshow(
        grid_matrix, 
        cmap=cmap, 
        interpolation='bicubic',
        extent=[0, len(metrics) - 1, ymin, ymax], 
        origin='lower', 
        aspect='auto',
        alpha=0.7,  
        zorder=2
        )

        im.set_clip_path(clip_polygon)

    perf_driven_data = datasets['Ưu tiên hiệu năng']

    # Label for 118.94% (Index 0: Performance)
    ax.annotate(
        f'{perf_driven_data[0]}%', 
        xy=(0, perf_driven_data[0]), 
        xytext=(0, 8),               # Offset text 8 points straight up from the marker
        textcoords="offset points", 
        ha='center', va='bottom', fontsize = 11, fontweight='bold', color=colors['Ưu tiên hiệu năng']['line']
    )

    ax.annotate(
    f'{perf_driven_data[1]}%', 
    xy=(1, perf_driven_data[1]), 
    xytext=(0, 8),               # Offset text 8 points straight up from the marker
    textcoords="offset points", 
    ha='center', va='bottom', fontsize = 11, fontweight='bold', color=colors['Ưu tiên hiệu năng']['line']
    )

    ppa_balance_data = datasets['Cân bằng PPA']

    ax.annotate(f'{ppa_balance_data[0]}%', xy=(0, ppa_balance_data[0]), xytext=(0, 8), textcoords="offset points", ha='center', va='bottom', fontsize=11, fontweight='bold', color=colors['Cân bằng PPA']['line'])

    ax.annotate(f'{ppa_balance_data[1]}%', xy=(1, ppa_balance_data[1]), xytext=(0, 8), textcoords="offset points", ha='center', va='bottom', fontsize=11, fontweight='bold', color=colors['Cân bằng PPA']['line'])

    ax.annotate(f'{ppa_balance_data[2]}%', xy=(2, ppa_balance_data[2]), xytext=(0, -16), textcoords="offset points", ha='center', va='bottom', fontsize=11, fontweight='bold', color=colors['Cân bằng PPA']['line'])


    # 4. Generate one shared vertical colorbar 
    # Uses a generic grey/blue visual reference bar for scale context
    # neutral_cmap = LinearSegmentedColormap.from_list('neutral_grad', ['#F2F4F4', '#E45756'])
    # sm = plt.cm.ScalarMappable(cmap=neutral_cmap, norm=plt.Normalize(vmin=ymin, vmax=ymax))
    # sm.set_array([])
    # cbar = fig.colorbar(sm, ax=ax, orientation='vertical', location='left', pad=0.03)
    # cbar.set_label('Tỉ lệ thay đổi (%)', rotation=90, labelpad=10)

    # 5. Clean layout formatting
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    # ax.set_yticks([])
    ax.set_ylabel('Tỉ lệ cải thiện trọng số PPA (%)')
    # ax.set_title('PPA Summary Comparison', fontweight='bold', pad=15)

    padding = 0.2
    ax.set_xlim(x[0] - padding, x[-1] + padding)

    # 0% Baseline and grid layers
    ax.axhline(0, color='#7F8C8D', linestyle='--', linewidth=1, zorder=1)
    ax.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)

    legend_elements = [
        Line2D([0], [0], color=colors['Ưu tiên hiệu năng']['line'], linewidth=2.5, label='Ưu tiên hiệu năng'),
        Line2D([0], [0], color=colors['Cân bằng PPA']['line'], linewidth=2.5, label='Cân bằng PPA'),
        Line2D([0], [0], color=colors['Bản ban đầu']['line'], linewidth=2.5, label='Bản ban đầu')
    ]


    # Position legend cleanly out of the way of the high values
    ax.legend(
        # handles=legend_elements,
        loc='upper center', 
        bbox_to_anchor=(0.5, -0.15), 
        ncol=3, 
        frameon=False, 
        facecolor='white', 
        edgecolor='#e0e0e0',
        # handlelength=1.0,
        # handleheight=1.0
    )

    plt.tight_layout()
    # plt.show()
    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/area_gradient_ex.pdf')

def plot_sum_number_CP_for_Perf():
    # 1. Your original data setup
    versions = [
        'RTLLM\nPerf-v0', 'RTLLM\nPerf-v1', 'RTLLM\nPerf-v2', 
        'VerilogEval\nPerf-v0', 'VerilogEval\nPerf-v1', 'VerilogEval\nPerf-v2'
    ]

    improve = [21.92, 23.88, 23.33, 9.39, 6.46, 16.40]
    # worse = [12.56, 16.18, 15.25, 24.51, 30.39, 25.49]
    no_change = [27.96, 26.79, 20.24, 33.33, 30.39, 24.51]
    failure = [10.41, 3.57, 10.71, 8.82, 3.92, 9.8]

    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(versions))
    width = 0.25
    spacing = 0.3

    colors = [cs_colors[1], panel_blue[3], panel_blue[1]] # Modern palette
    hatch_ls = ['', r'\\\\', '...']
    labels = ['Cải thiện', 'Không thay đổi', 'Thất bại']
    data_matrix = [improve, no_change, failure]
    offsets = [-spacing, 0, spacing]

    # 2. Render using native rounded stroke caps
    for dataset, offset, color, label, pattern in zip(data_matrix, offsets, colors, labels, hatch_ls):
        bars = ax.bar(
            x + offset, dataset, width, 
            label=label, 
            color=color, 
            hatch=pattern,
            # edgecolor=color, 
            linewidth=1.5,          
            # joinstyle='round', 
            # capstyle='round'
        )
        
        # NEW: Loop through each bar to overlay the text values on top
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f'{round(height)}%',                  # Text formatting (e.g., 25.2%)
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),                    # 5 points vertical offset above the cap
                textcoords="offset points",
                ha='center', va='bottom',         # Centered horizontally
                fontsize=8, fontweight='semibold', color='#4a5568'
            )


    # 3. Clean, Professional Theme
    ax.set_xticks(x)
    ax.set_xticklabels(versions, fontsize=9, fontweight='medium')
    # ax.set_xlabel('Benchmark và phiên bản prompt')
    ax.set_ylabel('Tỉ lệ cải thiện (%)', fontweight='medium')
    ax.set_ylim(0, 40)

    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    ax.set_axisbelow(True)

    # Remove borders for a slick, modern clean design
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)

    # ax.spines['bottom'].set_color('#cbd5e1')
    # ax.spines['left'].set_color('#cbd5e1')

    legend_elements = [
        mlines.Line2D([], [], color=colors[0], marker='s', linestyle='None', markersize=10, label=labels[0]),
        mlines.Line2D([], [], color=colors[1], marker='s', linestyle='None', markersize=10, label=labels[1]),
        mlines.Line2D([], [], color=colors[2], marker='s', linestyle='None', markersize=10, label=labels[2])
    ]

    ax.legend(
        handlelength=1.5,
        handleheight=1.5,
        loc='upper center', 
        bbox_to_anchor=(0.5, -0.15), 
        ncol=3, 
        columnspacing=0.5, 
        handletextpad=0.5, 
        frameon=False)

    plt.tight_layout()
    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/sum_all_model_for_perf.pdf')

    # plt.show()

def plot_scatter_CP_models():

    # 1. Define the raw arrays for each version and model
    data_v0 = {
        "ChatGPT": [23.81, 5.71, 36.02, 1.97, 1.48, 13.71, 11.64, 40.00, 8.28, 0.93, 4.20, 0.70],
        "DeepSeek": [1.43, 0.92, 1.97, 25.00, 2.88, 0.74, 7.71, 15.00, 30.57, 0.93, 1.75],
        "Gemini": [1.43, 0.92, 1.97, 25.00, 2.88, 0.74, 7.71, 15.00, 30.57, 0.93, 1.75]
    }

    data_v1 = {
        "ChatGPT": [23.81, 5.71, 34.75, 1.97, 25.00, 24.37, 2.33, 1.48, 6.57, 4.11, 8.33, 8.28, 0.93, 0.71, 4.20, 0.70],
        "DeepSeek": [23.81, 5.71, 34.75, 1.97, 25.00, 24.37, 2.33, 1.48, 6.57, 4.11, 8.33, 8.28],
        "Gemini": [23.81, 5.71, 34.75, 1.97, 25.00, 24.37, 2.33, 1.48]
    }

    data_v2 = {
        "ChatGPT": [23.81, 5.71, 27.97, 1.97, 27.27, 1.48, 8.29, 18.06, 25.63, 30.14, 0.99, 0.71, 4.20, 51.93],
        "DeepSeek": [2.44, 19.05, 5.71, 53.39, 1.83, 1.97, 5.75, 5.71, 25.00, 26.71, 32.48, 0.93, 3.36, 47.02],
        "Gemini": [4.65, 2.44, 19.05, 1.43, 3.29, 4.81, 11.71, 18.06, 26.88, 22.29, 9.24, 3.36, 48.07]
    }

    # 2. Build a unified list of data records
    compiled_rows = []

    def parse_dataset(dataset_dict, version_name):
        for model, val_list in dataset_dict.items():
            for value in val_list:
                compiled_rows.append({"Model": model, "Version": version_name, "Value": value})

    parse_dataset(data_v0, "Perf-v0")
    parse_dataset(data_v1, "Perf-v1")
    parse_dataset(data_v2, "Perf-v2")

    df = pd.DataFrame(compiled_rows)

    # 3. Setup the figure
    plt.figure(figsize=(6, 4))

    # Style configs
    colors = {"ChatGPT": cs_colors[1], "DeepSeek": panel_blue[0], "Gemini": panel_blue[2]}
    version_mapping = {"Perf-v0": 0.0, "Perf-v1": 1.0, "Perf-v2": 2.0}
    markers = {"ChatGPT": 'o', "DeepSeek": 's', "Gemini": '^'}

    # Set random seed so the point spread is perfectly reproducible
    np.random.seed(42)

    # Track legend entries to avoid messy duplicates
    tracked_legends = set()

    # 4. Plot points with wide jitter grouping
    for (version, model), group in df.groupby(["Version", "Model"]):
        base_x = version_mapping[version]
        
        # Apply wide horizontal jitter (-0.3, 0.3)
        jitter = np.random.uniform(-0.4, 0.4, size=len(group))
        x_positions = np.full(len(group), base_x) + jitter
        
        # Establish label only once per model
        if model not in tracked_legends:
            label = model
            tracked_legends.add(model)
        else:
            label = ""

        plt.scatter(
            x_positions,
            group["Value"],
            color=colors[model],
            marker=markers[model],
            label=label,
            s=30,
            alpha=1,
            zorder=3
        )

    # 5. Clean layout limits & grid adjustments
    plt.xlim(-0.6, 2.6)
    plt.xticks([0.0, 1.0, 2.0], ["Perf-v0", "Perf-v1", "Perf-v2"], fontsize=10, fontweight='semibold')
    y_min, y_max = -5, 65
    plt.ylim(y_min, y_max)

    ax = plt.gca()

    for spine in ax.spines.values():
        spine.set_visible(False)

    # Shift arrows slightly inward so they don't intersect or touch at the corner
    gap_offset = 0  # Safe vertical space gap for the Y-axis base
    x_start = -0.65  # Safe horizontal space gap for the X-axis base

    ax.annotate(
        "",
        xy=(-0.6, y_max),
        xytext=(-0.6, y_min + gap_offset),
        arrowprops=dict(arrowstyle="->", lw=1, color="black", clip_on=False),
    )

    # Draw the standalone X-axis arrow (starts slightly to the right of the left boundary)
    ax.annotate(
        "",
        xy=(2.6, y_min),
        xytext=(x_start, y_min),
        arrowprops=dict(arrowstyle="->", lw=1, color="black", clip_on=False),
    )

    # plt.title("Clustered Distribution across Versions", fontsize=12)
    plt.xlabel("Các phiên bản prompt")
    plt.ylabel("Cải thiện Critical Path (%)")
    plt.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)

    # Position legend in the upper left corner safely
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), handletextpad=0,  ncol=3, frameon=False, markerscale=1.5)

    plt.tight_layout()
    # plt.show()

    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/scatter_CP_verilogEval.pdf')

def plot_openlane_conver():

    color_s = ["#2C4F76", "#4C78A8", "#7AA0CD", "#ABC9E9", cs_colors[1]]

    # 1. Define the list of your 5 pickle files
    base_pkl = "/Users/dsmac/Documents/thesis/impl/Verippa/RTLLM_Chatgpt_Perf-v3/"

    ls_design = ["adder_16bit",
                 "asyn_fifo", "calendar", "edge_detect", "fsm"]

    plt.figure(figsize=(6, 4))

    for i, file in enumerate(ls_design):

        pkl_file = os.path.join(base_pkl, file, "openlane_bo_result.pkl")

        try:

            if os.path.exists(pkl_file):
                bo_result = load(pkl_file)

                func_vals = bo_result.func_vals
                running_min = np.minimum.accumulate(func_vals)

                parent_dir = os.path.dirname(pkl_file)

                label_name = os.path.basename(parent_dir)

                if i == 0:
                    plot_label = "Các thiết kế"
                else:
                    plot_label = None 

                if i == 4:

                    best_idx = np.argmin(func_vals)
                    best_y = func_vals[best_idx]
                    
                    best_config = bo_result.x

                    annotation_string = (
                        f"CLOCK_PERIOD = {best_config[0]}\n"
                        f"FP_CORE_UTIL = {best_config[1]}\n"
                        f"PL_TARGET_DENSITY = {best_config[2]}\n"
                        f"SYNTH_STRATEGY = {best_config[3]}"
                    )

                    plt.plot(best_idx, best_y, marker='o', color=panel_blue[0], markersize=5, zorder=5)

                    # print(config_text)

                    plt.annotate(
                        annotation_string,
                        xy=(best_idx, best_y),               # Target coordinate point for arrow tip
                        xytext=(best_idx + 8, best_y + (plt.ylim()[1] - best_y) * 0.4),  # Box position offset
                        arrowprops={
                            'facecolor':'black', 
                            'arrowstyle':"->", 
                            'lw':1.5
                        },
                        bbox={
                            'boxstyle':"round,pad=0.5", 
                            'facecolor':"white", 
                            'edgecolor':"dimgray", 
                            'alpha':0.95
                        },
                        fontsize=9,
                        color='black'
                    )

                # Plot onto the shared plane
                plt.plot(running_min, linewidth=2, label=plot_label, color=color_s[i])


        except Exception as e:
            print(f"Error loading {file} with skopt: {e}")

    plt.axvspan(6, 15, color='gray', alpha=0.15, label='Cửa sổ hội tụ')

# # 2. Add an annotations text arrow pointing to it or labeling it
#     plt.text(10.5, plt.ylim()[1] * 0.9, 'Vòng lặp 6 - 15', 
#          horizontalalignment='center', verticalalignment='top',
#          fontsize=10, fontweight='bold', color='dimgray',
#          bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

    plt.xlabel("Số lượng vòng lặp đánh giá (30 vòng)")
    plt.ylabel("Giá trị Hàm mục tiêu")
    plt.grid(axis="y", linestyle="--", alpha=0.5, zorder=0)
    plt.legend(loc="upper right")
    plt.tight_layout()

    plt.savefig('/Users/dsmac/Documents/thesis/impl/latex/Thesis-Template-main/figure/chap4/baye_convergence.pdf')

    # plt.show()


if __name__ == "__main__":

    database_path = os.path.join(prj_dir, "Report", "Diagram", "Database")
    
    indicator_cvt = ['Freq(MHz)', 'Power(W)','Die(um^2)']

    # Calculate grid dimensions
    total_charts = len(design_list)
    cols = 4
    rows = math.ceil(total_charts / cols)

    # sh_names = ['VerilogEval_benchmark', 'VerilogEval_Chatgpt_Perf-v3', 'VerilogEval_Deepseek_Perf-v3', 'VerilogEval_Gemini_Perf-v3']

    sh_names = ['VerilogEval_benchmark', "VerilogEval_Deepseek_Perf-v3", "VerilogEval_Gemini_Perf-v3", "VerilogEval_Chatgpt_Perf-v3", 'RTLLM_benchmark', 'Perf-v3', 'Gemini-Perf-v3', 'RTLLM_Chatgpt_Perf-v3']

    sh_name_perf = ['VerilogEval_Deepseek_Perf-v0', 'VerilogEval_Deepseek_Perf-v1', 'VerilogEval_Deepseek_Perf-v3']

    sh_name_perf_2 = ['VerilogEval_Gemini_Perf-v0', 'VerilogEval_Gemini_Perf-v1', 'VerilogEval_Gemini_Perf-v3']

    sh_name_perf_3 =['VerilogEval_Chatgpt_Perf-v0', 'VerilogEval_Chatgpt_Perf-v1', 'VerilogEval_Chatgpt_Perf-v3']

    compare_1 = sh_names[0]

    plot_spider_one('performance_metrics_enhance', 'performance_RTLLM_bm_filter', 'performance_RTLLM_enhanced', 'multi_pipe_4bit')
    plot_spider_one('area_metrics_enhance', 'area_RTLLM_bm_filter', 'area_RTLLM_enhanced', 'multi_pipe_4bit')
    plot_spider_one('power_metrics_enhance', 'power_RTLLM_bm_filter', 'power_RTLLM_enhanced', 'multi_pipe_4bit')

    # multi_pipe_4bit, traffic_light

    # plot_area_gradient_colorbar()

    # rtllm_eval_general()
