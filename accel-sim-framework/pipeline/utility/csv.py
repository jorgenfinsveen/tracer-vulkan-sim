#!/usr/bin/env python3
import os
import re
import sys
import csv
import glob
import parser
from pathlib import Path
from collections import defaultdict, OrderedDict
from typing import Optional

DIR_PATH: Path = Path(__file__).resolve().parent
PIPELINE_ROOT: Path = DIR_PATH.parent
PIPELINE_CONFIG_FILE: Path = os.path.join(PIPELINE_ROOT, "setup", "pipeline.yaml")

DASH_RE = re.compile(r"^-{5,}\s*,*")
CONFIG_LINE_RE = re.compile(r"^(?P<gpu>[^;]+);;(?P<kv>[^=]+)=(?P<val>.+)$")

pipeline = {}


def pick_existing_glob(*patterns: str) -> str:
    hits = []
    for pat in patterns:
        hits.extend(glob.glob(pat))
    hits = sorted(set([h for h in hits if os.path.isfile(h)]))
    if hits:
        return hits[0]
    tried = "\n  - " + "\n  - ".join(patterns)
    raise FileNotFoundError(f"Could not find required file. Tried:{tried}")


def pick_existing_dir(*candidates: str) -> str:
    for p in candidates:
        if p and os.path.isdir(p):
            return p
    tried = "\n  - " + "\n  - ".join([c for c in candidates if c])
    raise FileNotFoundError(f"Could not find required directory. Tried:{tried}")


def find_matching_runs(path: Path, experiment_name: str):
    sim_logs = parser.get_simulator_logs(path)
    matches = []
    for key, log in sim_logs.items():
        if log.experiment != experiment_name:
            continue
        date = key[4:] if key.startswith("sim-") else key
        matches.append((key, date, log.configs))
    matches.sort(key=lambda x: x[1])
    return matches


def parse_configs_for_run(configs_list):
    out = {}
    for item in configs_list:
        m = CONFIG_LINE_RE.match(str(item).strip())
        if not m:
            continue
        gpu = m.group("gpu").strip()
        param = m.group("kv").strip()
        val = m.group("val").strip()
        out[gpu] = (param, val)
    return out


def find_total_csv_for_date(total_dir: str, date_key: str) -> str | None:
    hits = sorted(glob.glob(os.path.join(total_dir, f"*{date_key}*")))
    hits = [h for h in hits if h.lower().endswith(".csv")]
    if not hits:
        return None
    return hits[-1]


def safe_float(x: str) -> Optional[float]:
    x = (x or "").strip()
    if not x or x.upper() == "NA":
        return None
    try:
        return float(x)
    except ValueError:
        return None


def fmt(x: Optional[float]) -> str:
    if x is None:
        return ""
    return f"{x:.4f}"


def parse_metric_block(csv_path: str, metric: str):
    metric_line_re = re.compile(rf"^\s*{re.escape(metric)}\b")
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()

    n = len(lines)
    for i in range(n):
        if not metric_line_re.search(lines[i]):
            continue

        k = i + 1
        while k < n and not lines[k].startswith("CFG,"):
            if DASH_RE.match(lines[k].strip()):
                break
            k += 1

        if k >= n or not lines[k].startswith("CFG,"):
            continue

        header = next(csv.reader([lines[k].strip()]))
        header_cols = header[1:]

        rows = {}

        j = k + 1
        while j < n:
            l = lines[j].strip()
            if not l:
                j += 1
                continue
            if DASH_RE.match(l):
                break
            rec = next(csv.reader([l]))
            if not rec:
                j += 1
                continue

            cfg = rec[0].strip()
            vals = rec[1:]
            
            if len(vals) > len(header_cols):
                vals = vals[: len(header_cols)]
            elif len(vals) < len(header_cols):
                vals += [""] * (len(header_cols) - len(vals))

            rows[cfg] = vals
            j += 1

        return header_cols, rows

    raise RuntimeError(f"Could not find metric block '{metric}' in {csv_path}")


def group_columns_render_compute(header_cols):
    groups = OrderedDict()
    for idx, col in enumerate(header_cols):
        col = (col or "").strip()
        if not col:
            continue

        if "--" in col:
            group, kernel = col.split("--", 1)
        else:
            group, kernel = col, col

        group = group.strip()
        kernel = kernel.strip()

        kind = "render" if "MESA_SHADER" in kernel else "compute"

        if group.upper() == "AVG":
            continue

        if group not in groups:
            groups[group] = {"render": [], "compute": []}
        groups[group][kind].append(idx)

    return groups


def avg_of_indices(vals, indices):
    nums = []
    for i in indices:
        if i >= len(vals):
            continue
        v = safe_float(vals[i])
        if v is not None:
            nums.append(v)
    if not nums:
        return None
    return sum(nums) / len(nums)


def main():
    global pipeline
    pipeline = parser.get_pipeline(PIPELINE_CONFIG_FILE)
    exp_name = pipeline.experiment.name
    metric = pipeline.collect.metric

    results_dir = os.path.expandvars(pipeline.results_dir)
    sim_logs_path = os.path.join(results_dir, "output", "simulator_logs.yaml")

    export_dir = os.path.join(results_dir, "export")
    export_total_dir = os.path.join(export_dir, "total")

    runs = find_matching_runs(sim_logs_path, exp_name)
    if not runs:
        print(f"No runs matched experiment.name={exp_name}", file=sys.stderr)
        sys.exit(2)

    per_gpu_rows = defaultdict(list)
    all_group_keys = OrderedDict()

    for _, date_key, configs_list in runs:
        total_csv = find_total_csv_for_date(export_total_dir, date_key)
        if not total_csv:
            print(f"WARNING: No total CSV found for date {date_key} in {export_total_dir}", file=sys.stderr)
            continue

        cfg_param_map = parse_configs_for_run(configs_list)
        header_cols, rows = parse_metric_block(total_csv, metric)
        groups = group_columns_render_compute(header_cols)

        for g in groups.keys():
            all_group_keys.setdefault(f"{g}__render", None)
            all_group_keys.setdefault(f"{g}__compute", None)

        for gpu_name, vals in rows.items():
            if gpu_name not in cfg_param_map:
                continue

            param_name, param_val = cfg_param_map[gpu_name]
            out_row = {param_name: param_val}

            all_avgs_for_row = []
            for g, kind_map in groups.items():
                r = avg_of_indices(vals, kind_map["render"])
                c = avg_of_indices(vals, kind_map["compute"])

                out_row[f"{g}__render"] = fmt(r)
                out_row[f"{g}__compute"] = fmt(c)

                if r is not None:
                    all_avgs_for_row.append(r)
                if c is not None:
                    all_avgs_for_row.append(c)

            out_row["AVG"] = fmt(sum(all_avgs_for_row) / len(all_avgs_for_row)) if all_avgs_for_row else ""
            per_gpu_rows[gpu_name].append((param_name, out_row))

    if not per_gpu_rows:
        print("No rows produced. Do the CFG names in CSV match simulator_logs configs GPU names?", file=sys.stderr)
        sys.exit(3)

    for gpu, row_pairs in per_gpu_rows.items():
        gpu_model = gpu.split("_")[0]
        out_gpu_dir = os.path.join(export_dir, gpu_model)
        os.makedirs(out_gpu_dir, exist_ok=True)
        out_path = os.path.join(out_gpu_dir, f"{metric}.csv")

        param_names = [p for (p, _) in row_pairs]
        param_name = max(set(param_names), key=param_names.count)

        fieldnames = [param_name] + list(all_group_keys.keys()) + ["AVG"]

        with open(out_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for _, r in row_pairs:
                if param_name not in r:
                    r[param_name] = ""
                w.writerow({k: r.get(k, "") for k in fieldnames})

        print(f"Wrote {out_path} ({len(row_pairs)} rows)")

    print(f"Done. Experiment={exp_name}, metric={metric}")


if __name__ == "__main__":
    main()
