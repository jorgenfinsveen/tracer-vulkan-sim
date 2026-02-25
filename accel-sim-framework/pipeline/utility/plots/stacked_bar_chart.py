#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from utility.kernel_handler import KernelHandler
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import utility.parser as ps
import statistics

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_YAML = PIPELINE_ROOT.parent / "setup" / "pipeline.yaml"

pipeline = {}
experiment = {}

def group_data(df, row, benchmark, kernel_handler: KernelHandler, want_render: bool):
    data_list = []
    for col_name in df.columns[1:]:
        if not col_name.startswith(benchmark):
            continue
        col_name_part = col_name.split("/")[2]

        if want_render:
            if kernel_handler.is_render_kernel(col_name_part):
                data_list.append(df.loc[row, col_name])
        else:
            if kernel_handler.is_compute_kernel(col_name_part):
                data_list.append(df.loc[row, col_name])

    return data_list


def compute_avg_data(data_list):
    return statistics.mean(data_list) if data_list else 0


def fetch_benchmarks(df):
    benchmark_list = []
    for col_name in df.columns[1:]:
        if col_name == "AVG":
            continue
        name_split = col_name.split("/")
        name = name_split[0] + "/" + name_split[1]
        benchmark_list.append(name)
    return set(benchmark_list)


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


def compute_avg_data_list(df, len_config, benchmarks, kernel_handler: KernelHandler):
    avg_data_list = []

    for row in range(len_config):
        row_out = []
        for benchmark in benchmarks:
            render_vals = group_data(df, row, benchmark, kernel_handler, want_render=True)
            compute_vals = group_data(df, row, benchmark, kernel_handler, want_render=False)

            render_avg = compute_avg_data(render_vals) if render_vals else 0
            compute_avg = compute_avg_data(compute_vals) if compute_vals else 0

            row_out.append([render_avg, compute_avg])
        avg_data_list.append(row_out)

    return avg_data_list


def get_gpu_name(csv_path: str) -> str:
    gpu_name = Path(csv_path).parent.name
    return gpu_name


def get_benchmark_name():
    global pipeline
    pipeline = ps.get_pipeline(PIPELINE_YAML)

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
    kernel_names = []
    for col_name in df.columns[1:]:
        if col_name == "AVG":
            continue
        parts = col_name.split("/")
        if len(parts) > 2:
            kernel_names.append(parts[2])

    kernel_handler = KernelHandler(kernel_names)

    benchmarks = sorted(fetch_benchmarks(df))
    configs = sorted(get_config_metric(df))
    len_benchmarks = len(benchmarks)
    len_config = len(configs)

    x_benchmarks, x_configs = gorup_benchmakr_with_configs(benchmarks, configs)
    x_labels = configs
    x_pos = np.arange(len(x_labels))

    avg_data_list = compute_avg_data_list(df, len_config, benchmarks, kernel_handler)
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
    plt.savefig(
        csv_path.with_suffix("").parent / f"{csv_path.stem}_stacked_bar_chart.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()