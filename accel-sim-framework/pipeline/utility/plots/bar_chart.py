#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _label(name: str) -> str:
    return name.replace("_", " ").strip().title()


def bar_chart(csv_path: str) -> None:
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)

    if df.shape[1] < 2:
        raise ValueError(
            "CSV must have at least 2 columns: first=config, remaining=benchmarks"
        )

    config_col = df.columns[0]
    metric_raw = csv_path.stem
    metric_label = _label(metric_raw)

    df_long = df.melt(
        id_vars=config_col,
        var_name="benchmark",
        value_name=metric_label
    )

    benchmarks = df_long["benchmark"].unique()
    configs = df_long[config_col].unique()

    x = range(len(benchmarks))
    width = 0.8 / max(1, len(configs))

    plt.figure(figsize=(10, 5))

    for i, cfg in enumerate(configs):
        vals = df_long[df_long[config_col] == cfg][metric_label].to_list()
        plt.bar([p + i * width for p in x], vals, width, label=str(cfg))

    mid = (len(configs) - 1) * width / 2
    plt.xticks([p + mid for p in x], benchmarks, rotation=30, ha="right")

    plt.xlabel("Benchmark")
    plt.ylabel(metric_label)
    plt.title(f"{metric_label} vs Benchmark")
    plt.legend(title=_label(config_col))
    plt.tight_layout()
    out_file = csv_path.with_suffix("")
    out_file = out_file.parent / f"{out_file.name}_by_benchmark.png"
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()