#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import utility.parser as ps

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_YAML = PIPELINE_ROOT.parent / "setup" / "pipeline.yaml"

pipeline = {}
experiment = {}

# Method for grouping data
# df is the csv file as a input
# row is what row in the csv file you want to gorup, meaning it cores based on different configs.
# data_type is what type of data you want to gropup it by, meaning ether render og compute. So here we need to pass MEAS for render and NZ2 for compute
# Benchmark is to filter for different benchmark, example is render_passes_2k/all1, where if the coulmn name dosent start with this name it dosent add it to the groupping.
def group_data(df, row, data_type, benchmark):
    data_list = []
    for col_name in df.columns[1:]:
        if not col_name.startswith(benchmark):
            continue
        
        col_name_part = col_name.split("/")[2]
        
        if col_name_part.startswith(data_type):
            data_list.append(df.loc[row, col_name])
    
    return data_list

# Computes the avg result of a grouped data
# data_list is the list of data that you want to compute the avg of
def compute_avg_data(data_list):
    n = len(data_list)
    sum = 0
    for i in range(n):
        sum = sum + data_list[i]
    return sum/n

# The function fetches all unic benchmark based on a csv file
# df is the csv file object pass as a parameter.
def fetch_benchmarks(df):
    #benchmark_list = []
    #for col_name in df.columns[1:]:
        #if col_name == "AVG":
           # continue
       # name_split = col_name.split("/")
      #  name = name_split[0] + "/" + name_split[1]
       # benchmark_list.append(name)
    #return set(benchmark_list)

    benchmark_list = []
    for col_name in df.columns[1:]:
        if col_name == "AVG":
            continue
        name_split = col_name.split("/")
        name = name_split[0] + "/" + name_split[1]
        benchmark_list.append(name)
    return set(benchmark_list)

# Returns the configuration metric name
def get_config_metric_name(df):
    return df.columns[0]
    

def get_config_metric(df):
    return df.iloc[:, 0].tolist()

def gorup_benchmakr_with_configs(benchmarks, configs):
    x_benchmarks = []
    x_configs = []

    for b in benchmarks:
        for c in configs:
            x_benchmarks.append(b)
            x_configs.append(c)

    return x_benchmarks, x_configs

def group_y_data(len_config, len_benchmarks, avg_data_list):
    y_render = []
    y_compute = []

    for row in range(len_config):
        for b in range(len_benchmarks):
            y_render.append(avg_data_list[row][b][0])
            y_compute.append(avg_data_list[row][b][1])

    return y_render, y_compute

def compute_avg_data_list(df, len_config, benchmarks):
    avg_data_list = []

    for row in range(len_config):
        row_out = []
        for benchmark in benchmarks:
            mesa_vals = group_data(df, row, "MESA", benchmark)
            zn2_vals  = group_data(df, row, "ZN2", benchmark)

            mesa_avg = compute_avg_data(mesa_vals)
            zn2_avg  = compute_avg_data(zn2_vals)

            row_out.append([mesa_avg, zn2_avg])
        avg_data_list.append(row_out)
    return avg_data_list

def get_gpu_name(csv_path: str) -> str:
    gpu_name = Path(csv_path).parent.name
    return gpu_name

def get_benchmark_name():
    global pipeline
    pipeline = ps.get_pipeline(PIPELINE_YAML)
    exp_name = pipeline.experiment.name

    global experiment
    experiment = ps.get_experiment(pipeline.experiment.name)
    benchmark = experiment.benchmarks[0]

    if ":" in benchmark:
        benchmark_name = benchmark.split(":")[1].strip()
        return benchmark_name
    return benchmark.strip()


def staked_bar_chart(csv_path: str) -> None:
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)

    benchmarks = sorted(fetch_benchmarks(df))
    configs = sorted(get_config_metric(df))
    len_benchmarks = len(benchmarks)
    len_config = len(configs)

    x_benchmarks, x_configs = gorup_benchmakr_with_configs(benchmarks, configs)
    #x_labels = [f"{b}\n{c}" for b, c in zip(x_benchmarks, x_configs)]
    x_labels = configs

    x_pos = np.arange(len(x_labels))

    avg_data_list = compute_avg_data_list(df, len_config, benchmarks)
    y_render, y_compute = group_y_data(len_config, len_benchmarks, avg_data_list)

    gpu_name = get_gpu_name(csv_path)
    benchmark_name = get_benchmark_name()

    plt.bar(x_pos, y_render, label="render")
    plt.bar(x_pos, y_compute, bottom=y_render, label="compute")
    plt.xticks(x_pos, x_labels)
    plt.legend()
    plt.title(f"Average render and compute time for {gpu_name}\n {benchmark_name}")
    plt.tight_layout()
    plt.grid(True)
    plt.savefig(csv_path.with_suffix("").parent / f"{csv_path.stem}_stacked_bar_chart.png", dpi=300, bbox_inches="tight")
    #plt.savefig("test_plot.png")
    plt.savefig("test_plot.png")
    plt.close()

def main():
    csv_dir= "/cluster/home/olekd/projects/crisp_framework/accel-sim-framework/pipeline/results/export/RTX3070/more_streaming_multiprocessors.csv"
    print("Result dir: ", get_result_dir(csv_dir))
    #staked_bar_chart(csv_dir)

    




if __name__ == "__main__":
    main()


