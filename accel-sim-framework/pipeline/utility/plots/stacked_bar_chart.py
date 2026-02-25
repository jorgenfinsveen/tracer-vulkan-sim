#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import re

def extract_number(value) -> str:
    m = re.search(r"\d+", str(value))
    return m.group(0) if m else str(value)

def get_gpu_name(csv_path: Path) -> str:
    return csv_path.parent.name

def stacked_bar_chart(csv_path: str) -> None:
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)

    configs = df.iloc[:, 0].tolist()
    x_labels = [extract_number(c) for c in configs]
    x_pos = np.arange(len(x_labels))

    y_render = df["render"].astype(float).tolist()
    y_compute = df["compute"].astype(float).tolist()

    gpu_name = get_gpu_name(csv_path)

    plt.figure(figsize=(max(10, len(x_labels) * 0.8), 6))
    plt.bar(x_pos, y_render, label="render")
    plt.bar(x_pos, y_compute, bottom=y_render, label="compute")
    plt.xticks(x_pos, x_labels)
    plt.ylabel("Average Time")
    plt.grid(True)
    plt.legend()
    plt.title(f"Average render and compute time for {gpu_name}")
    plt.tight_layout()
    out_path = csv_path.with_suffix("").parent / f"{csv_path.stem}_stacked_bar_chart.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()