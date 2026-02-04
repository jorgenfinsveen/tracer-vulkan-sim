#!/usr/bin/env python3
import re
import csv
import sys
from pathlib import Path

RUN_HDR_RE = re.compile(r"^([0-9]{4}_[0-9]{2}_[0-9]{2}__[0-9]{2}_[0-9]{2}):\s*$")
PARAM_ITEM_RE = re.compile(r"^\s*-\s*([A-Za-z0-9_]+)\s*:\s*(.+?)\s*$")
RESULT_ITEM_RE = re.compile(r"^\s*-\s*([A-Za-z0-9_]+)\s*:\s*([0-9.Ee+-]+)\s*$")

def find_run_info_in_yaml(yaml_path: Path, run_id: str):
    lines = yaml_path.read_text(errors="replace").splitlines()

    i = 0
    while i < len(lines):
        m = RUN_HDR_RE.match(lines[i].rstrip())
        if not m:
            i += 1
            continue

        this_id = m.group(1)
        i += 1
        if this_id != run_id:
            while i < len(lines) and not RUN_HDR_RE.match(lines[i].rstrip()):
                i += 1
            continue

        changed_key = None
        changed_val = None
        metrics = []

        in_params = False
        in_results = False

        while i < len(lines) and not RUN_HDR_RE.match(lines[i].rstrip()):
            s = lines[i].rstrip()

            if re.match(r"^\s*params\s*:\s*$", s):
                in_params = True
                in_results = False
                i += 1
                continue

            if re.match(r"^\s*results\s*:\s*$", s):
                in_results = True
                in_params = False
                i += 1
                continue

            if in_params:
                pm = PARAM_ITEM_RE.match(s)
                if pm and changed_key is None:
                    changed_key = pm.group(1)
                    changed_val = pm.group(2).strip().strip('"')
            elif in_results:
                rm = RESULT_ITEM_RE.match(s)
                if rm:
                    metrics.append(rm.group(1))

            i += 1

        if not changed_key or changed_val is None:
            raise SystemExit(f"Found {run_id} in {yaml_path}, but couldn't parse params[0].")
        if not metrics:
            raise SystemExit(f"Found {run_id} in {yaml_path}, but couldn't parse results metrics.")

        return changed_key, changed_val, metrics

    return None

def locate_run_yaml(results_output_root: Path, run_id: str) -> tuple[Path, str, str, list[str]]:
    candidates = list(results_output_root.rglob("*.yaml")) + list(results_output_root.rglob("*.yml"))

    for yp in candidates:
        info = find_run_info_in_yaml(yp, run_id)
        if info:
            changed_key, changed_val, metrics = info
            return yp, changed_key, changed_val, metrics

    raise SystemExit(f"Could not find any YAML under {results_output_root} containing run_id={run_id}")

def extract_metric_block(text: str, metric: str):
    m_re = re.compile(re.escape(metric), re.I)
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if not m_re.search(line):
            continue

        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines) or not lines[j].startswith("CFG,"):
            continue

        headers = [x.strip() for x in lines[j].split(",")[1:]]
        rows = {}

        for k in range(j + 1, len(lines)):
            s = lines[k].strip()
            if not s or s.startswith("-"):
                break
            if "\\s*=" in s and not m_re.search(s):
                break

            parts = [p.strip() for p in lines[k].split(",")]
            if len(parts) >= 2:
                cfg = parts[0]
                vals = parts[1:]
                vals += [""] * (len(headers) - len(vals))
                rows[cfg] = vals[:len(headers)]

        return headers, rows

    raise SystemExit(f"Metric not found in total CSV: {metric}")

def group_benchmarks(headers: list[str]):
    groups = {}
    for idx, h in enumerate(headers):
        left = h.split("--", 1)[0].strip()
        groups.setdefault(left, []).append(idx)
    return groups

def avg_of_indices(values: list[str], idxs: list[int]) -> str:
    nums = []
    for i in idxs:
        if i >= len(values):
            continue
        v = values[i].strip()
        if not v or v.upper() == "NA":
            continue
        try:
            nums.append(float(v))
        except ValueError:
            continue
    if not nums:
        return ""
    return f"{sum(nums) / len(nums):.6f}"

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: csv_generator.py <RUN_ID>  (e.g. 2026_01_12__14_37)")

    run_id = sys.argv[1]
    root = Path(__file__).resolve().parents[1]
    results_root = root / "pipeline" / "results"
    output_root  = results_root / "output"
    total_csv    = results_root / "export" / "total" / f"{run_id}.csv"

    if not total_csv.exists():
        raise SystemExit(f"Total CSV not found: {total_csv}")

    yaml_path, changed_key, changed_val, metrics = locate_run_yaml(output_root, run_id)

    text = total_csv.read_text(errors="replace")

    out_dir = results_root / "export" / "by_change" / changed_key
    out_dir.mkdir(parents=True, exist_ok=True)

    for metric in metrics:
        headers, rows = extract_metric_block(text, metric)
        groups = group_benchmarks(headers)
        wanted = [g for g in groups.keys() if g.endswith("/NO_ARGS") or g.endswith("/all1")]
        wanted = sorted(wanted)

        out_path = out_dir / f"{metric}-{run_id}.csv"
        with out_path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow([changed_key] + wanted)
            row_avgs = []
            for g in wanted:
                idxs = groups[g]
                per_cfg = [avg_of_indices(rows[cfg], idxs) for cfg in rows]
                nums = [float(x) for x in per_cfg if x]
                row_avgs.append(f"{sum(nums)/len(nums):.6f}" if nums else "")

            w.writerow([changed_val] + row_avgs)

        print(f"Wrote: {out_path}")
        print(f"  (from yaml: {yaml_path})")

if __name__ == "__main__":
    main()