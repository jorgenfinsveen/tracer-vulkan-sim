#!/usr/bin/env python3
import os, re, sys, csv, glob, parser
from pathlib import Path
from collections import defaultdict, OrderedDict
from typing import Optional, List

DIR_PATH: Path = Path(__file__).resolve().parent
PIPELINE_ROOT: Path = DIR_PATH.parent
PIPELINE_CONFIG_FILE: Path = os.path.join(PIPELINE_ROOT, "setup", "pipeline.yaml")

DASH_RE = re.compile(r"^-{5,}\s*,*")
CONFIG_LINE_RE = re.compile(r"^(?P<gpu>[^;]+);;(?P<kv>[^=]+)=(?P<val>.+)$")

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
        out[m.group("gpu").strip()] = (m.group("kv").strip(), m.group("val").strip())
    return out

def find_total_csv_for_date(total_dir: str, date_key: str) -> Optional[str]:
    hits = sorted(glob.glob(os.path.join(total_dir, f"*{date_key}*")))
    hits = [h for h in hits if h.lower().endswith(".csv")]
    return hits[-1] if hits else None

def safe_float(x: str) -> Optional[float]:
    x = (x or "").strip()
    if not x or x.upper() == "NA":
        return None
    try:
        return float(x)
    except ValueError:
        return None

def fmt(x: Optional[float]) -> str:
    return "" if x is None else f"{x:.4f}"

def parse_metric_block(csv_path: str, metric: str):
    metric_line_re = re.compile(rf"^\s*{re.escape(metric)}\b")
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if not metric_line_re.search(line):
            continue

        k = i + 1
        while k < len(lines) and not lines[k].startswith("CFG,"):
            if DASH_RE.match(lines[k].strip()):
                break
            k += 1

        if k >= len(lines) or not lines[k].startswith("CFG,"):
            continue

        header = next(csv.reader([lines[k].strip()]))
        header_cols_raw = header[1:]

        while header_cols_raw and header_cols_raw[-1].strip() == "":
            header_cols_raw.pop()
        if header_cols_raw and header_cols_raw[-1].strip().upper() == "AVG":
            header_cols_raw.pop()

        keep_idxs = [idx for idx, c in enumerate(header_cols_raw) if c.strip() != ""]
        header_cols = [header_cols_raw[idx].strip() for idx in keep_idxs]

        rows = {}
        j = k + 1
        while j < len(lines):
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
            vals_raw = rec[1:]

            if len(vals_raw) < len(header_cols_raw):
                vals_raw += [""] * (len(header_cols_raw) - len(vals_raw))
            vals_raw = vals_raw[:len(header_cols_raw)]

            vals = [vals_raw[idx] for idx in keep_idxs]
            rows[cfg] = vals
            j += 1

        return header_cols, rows

    raise RuntimeError(f"Metric '{metric}' not found in {csv_path}")

def group_columns(header_cols):
    groups = OrderedDict()
    for idx, col in enumerate(header_cols):
        col = (col or "").strip()
        if not col:
            continue
        if "--" in col:
            group, kernel = col.split("--", 1)
        else:
            group, kernel = col, col
        kind = "render" if "MESA_SHADER" in kernel else "compute"
        groups.setdefault(group, {"render": [], "compute": []})
        groups[group][kind].append(idx)
    return groups

def avg_of_indices(vals: List[str], indices: List[int]) -> Optional[float]:
    nums = []
    for i in indices:
        if i < len(vals):
            v = safe_float(vals[i])
            if v is not None:
                nums.append(v)
    return (sum(nums) / len(nums)) if nums else None

def main():
    pipeline = parser.get_pipeline(PIPELINE_CONFIG_FILE)
    exp_name = pipeline.experiment.name
    metric = pipeline.collect.metric

    results_dir = os.path.expandvars(pipeline.results_dir)
    sim_logs_path = os.path.join(results_dir, "output", "simulator_logs.yaml")
    export_dir = os.path.join(results_dir, "export")
    export_total_dir = os.path.join(export_dir, "total")

    runs = find_matching_runs(sim_logs_path, exp_name)
    if not runs:
        sys.exit(2)

    cfg_param_map_global = {}
    all_group_keys = OrderedDict()
    out_rows = []

    for _, date_key, configs_list in runs:
        total_csv = find_total_csv_for_date(export_total_dir, date_key)
        if not total_csv:
            continue

        cfg_param_map_global.update(parse_configs_for_run(configs_list))

        header_cols, rows = parse_metric_block(total_csv, metric)
        groups = group_columns(header_cols)

        for g in groups:
            all_group_keys.setdefault(f"{g}__render", None)
            all_group_keys.setdefault(f"{g}__compute", None)

        for gpu_name, vals in rows.items():
            row = {"GPU": gpu_name}

            param_name = None
            if gpu_name in cfg_param_map_global:
                param_name, param_val = cfg_param_map_global[gpu_name]
                row[param_name] = param_val

            all_avgs = []
            for g, km in groups.items():
                r = avg_of_indices(vals, km["render"])
                c = avg_of_indices(vals, km["compute"])
                row[f"{g}__render"] = fmt(r)
                row[f"{g}__compute"] = fmt(c)
                if r is not None:
                    all_avgs.append(r)
                if c is not None:
                    all_avgs.append(c)

            row["AVG"] = fmt(sum(all_avgs) / len(all_avgs)) if all_avgs else ""
            out_rows.append((gpu_name, param_name, row))

    if not out_rows:
        sys.exit(3)

    param_names = [p for _, p, _ in out_rows if p]
    param_name = max(set(param_names), key=param_names.count) if param_names else None

    out_path = os.path.join(export_dir, f"{metric}_per_gpu.csv")
    fieldnames = ["GPU"]
    if param_name:
        fieldnames.append(param_name)
    fieldnames += list(all_group_keys.keys()) + ["AVG"]

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for _, _, r in sorted(out_rows, key=lambda t: t[0]):
            if param_name and param_name not in r:
                r[param_name] = ""
            w.writerow({k: r.get(k, "") for k in fieldnames})

if __name__ == "__main__":
    main()
