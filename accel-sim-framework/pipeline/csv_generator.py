#!/usr/bin/env python3
import re
import csv
import sys
from pathlib import Path

SIM_HDR_RE = re.compile(r"^\s*sim-([0-9]{4}_[0-9]{2}_[0-9]{2}__[0-9]{2}_[0-9]{2})\s*:\s*$")
LIST_ITEM_RE = re.compile(r'^\s*-\s*"?(.*?)"?\s*$')
KV_RE = re.compile(r"^\s*([A-Za-z0-9_\-]+)\s*:\s*(.*?)\s*$")

GPU_ROW_MAP = {
    "ORIN": "ORIN-SASS-concurrent-fg-VISUAL",
    "RTX3070": "RTX3070-SASS-concurrent-fg-VISUAL",
}

def strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s

def read_experiment_defs(experiments_yaml: Path):
    text = experiments_yaml.read_text(errors="replace").splitlines()
    defs = {}
    cur_exp = None
    in_experiment_root = False
    current_key = None

    for line in text:
        raw = line.rstrip("\n")
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue

        indent = len(raw) - len(raw.lstrip(" "))

        if indent == 0 and raw.strip() == "experiment:":
            in_experiment_root = True
            cur_exp = None
            current_key = None
            continue

        if not in_experiment_root:
            continue

        if indent in (2, 1) and raw.strip().endswith(":") and not raw.strip().startswith(("-", "#")):
            cur_exp = raw.strip()[:-1]
            defs[cur_exp] = {"adjusted_param": [], "target_result": []}
            current_key = None
            continue

        m = KV_RE.match(raw)
        if m and cur_exp:
            k = m.group(1)
            v = m.group(2).strip()
            if v == "" and k in ("adjusted_param", "target_result"):
                current_key = k
            continue

        lm = LIST_ITEM_RE.match(raw)
        if lm and cur_exp and current_key:
            defs[cur_exp][current_key].append(strip_quotes(lm.group(1)))
            continue

    return defs

def read_simulator_logs(sim_logs_yaml: Path):
    lines = sim_logs_yaml.read_text(errors="replace").splitlines()
    runs = []

    i = 0
    cur = None
    mode = None
    while i < len(lines):
        s = lines[i].rstrip("\n")
        if not s.strip() or s.lstrip().startswith("#"):
            i += 1
            continue

        hm = SIM_HDR_RE.match(s)
        if hm:
            if cur:
                runs.append(cur)
            cur = {"run_id": hm.group(1), "experiment": None, "configs": [], "benchmarks": []}
            mode = None
            i += 1
            continue

        if not cur:
            i += 1
            continue

        km = KV_RE.match(s)
        if km:
            key = km.group(1)
            val = strip_quotes(km.group(2))
            if key == "experiment":
                cur["experiment"] = val
                mode = None
            elif key == "configs":
                mode = "configs"
            elif key == "benchmarks":
                mode = "benchmarks"
            else:
                mode = None
            i += 1
            continue

        lm = LIST_ITEM_RE.match(s)
        if lm and mode in ("configs", "benchmarks"):
            cur[mode].append(strip_quotes(lm.group(1)))
            i += 1
            continue

        i += 1

    if cur:
        runs.append(cur)
    return runs

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

    raise KeyError(metric)

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

def load_existing_table(csv_path: Path):
    if not csv_path.exists():
        return None, {}

    with csv_path.open("r", newline="") as f:
        r = csv.reader(f)
        try:
            header = next(r)
        except StopIteration:
            return None, {}
        rows = {}
        for row in r:
            if not row:
                continue
            key = row[0]
            rows[key] = row[1:]
        return header, rows

def write_table(csv_path: Path, header: list[str], rows: dict[str, list[str]]):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    def sort_key(k):
        try:
            return (0, float(k))
        except Exception:
            return (1, k)
    keys = sorted(rows.keys(), key=sort_key)

    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for k in keys:
            w.writerow([k] + rows[k])


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: csv_generator.py <EXPERIMENT_NAME>   (e.g. more_streaming_multiprocessors)")

    experiment_name = sys.argv[1]

    root = Path(__file__).resolve().parents[1]
    sim_logs_yaml = root / "simulator_logs.yaml"
    experiments_yaml = root / "setup" / "experiments.yaml"
    results_root = root / "results"
    total_root = results_root / "export" / "total"
    export_root = results_root / "export"

    if not sim_logs_yaml.exists():
        raise SystemExit(f"Missing: {sim_logs_yaml}")
    if not experiments_yaml.exists():
        raise SystemExit(f"Missing: {experiments_yaml}")
    if not total_root.exists():
        raise SystemExit(f"Missing: {total_root}")

    exp_defs = read_experiment_defs(experiments_yaml)
    if experiment_name not in exp_defs:
        raise SystemExit(f"Unknown experiment '{experiment_name}'. Known: {', '.join(sorted(exp_defs.keys()))}")

    adjusted_params = exp_defs[experiment_name]["adjusted_param"]
    metrics = exp_defs[experiment_name]["target_result"]

    if not adjusted_params:
        raise SystemExit(f"{experiment_name}: adjusted_param is empty")
    if len(adjusted_params) != 1:
        raise SystemExit(f"{experiment_name}: expected exactly 1 adjusted_param, got {adjusted_params}")
    adjusted_param = adjusted_params[0]

    runs = read_simulator_logs(sim_logs_yaml)
    runs = [r for r in runs if r.get("experiment") == experiment_name]

    if not runs:
        raise SystemExit(f"No runs found in {sim_logs_yaml.name} for experiment='{experiment_name}'")

    acc = {}

    for run in runs:
        run_id = run["run_id"]
        total_csv = total_root / f"{run_id}.csv"
        if not total_csv.exists():
            print(f"warning: total csv missing for run {run_id}: {total_csv}")
            continue

        text = total_csv.read_text(errors="replace")
        wanted_bench = set()
        for b in run.get("benchmarks", []):
            parts = [p.strip() for p in b.split(";") if p.strip()]
            if len(parts) == 3:
                suite, a, n = parts
                wanted_bench.add(f"{suite}/{a}")
                wanted_bench.add(f"{suite}/{n}")
            elif len(parts) == 2:
                suite, mode = parts
                wanted_bench.add(f"{suite}/{mode}")
            elif len(parts) == 1:
                wanted_bench.add(parts[0])

        for cfgstr in run.get("configs", []):
            chunks = cfgstr.split(";;")
            gpu = chunks[0].strip()
            param_part = chunks[1].strip() if len(chunks) > 1 else ""
            param_value = None
            if param_part.startswith(adjusted_param + "="):
                param_value = param_part.split("=", 1)[1].strip()
            else:
                continue

            for metric in metrics:
                try:
                    headers, rows = extract_metric_block(text, metric)
                except KeyError:
                    print(f"warning: metric '{metric}' not found in {total_csv.name}")
                    continue

                gpu_row = GPU_ROW_MAP.get(gpu, gpu)

                if gpu_row not in rows:
                    print(f"warning: gpu row '{gpu_row}' not found for metric '{metric}' in {total_csv.name}")
                    continue

                groups = group_benchmarks(headers)
                gpu_vals = rows[gpu_row]


                bench_avgs = {}
                for bname in sorted(wanted_bench):
                    if bname in groups:
                        bench_avgs[bname] = avg_of_indices(gpu_vals, groups[bname])

                key = (gpu, metric)
                if key not in acc:
                    acc[key] = {"bench_cols": set(), "rows": {}}
                acc[key]["bench_cols"].update(bench_avgs.keys())
                rowmap = acc[key]["rows"].setdefault(param_value, {})
                rowmap.update(bench_avgs)

    for (gpu, metric), blob in acc.items():
        bench_cols = sorted(blob["bench_cols"])
        header = [adjusted_param] + bench_cols

        out_path = export_root / gpu / adjusted_param / f"{metric}.csv"
        existing_header, existing_rows = load_existing_table(out_path)
        merged = {}

        if existing_header and len(existing_header) >= 2:
            existing_bench_cols = existing_header[1:]
            for pval, vals in existing_rows.items():
                merged[pval] = {}
                for i, b in enumerate(existing_bench_cols):
                    merged[pval][b] = vals[i] if i < len(vals) else ""

            for b in existing_bench_cols:
                if b not in bench_cols:
                    bench_cols.append(b)
            bench_cols = sorted(set(bench_cols))
            header = [adjusted_param] + bench_cols

        for pval, benchmap in blob["rows"].items():
            merged.setdefault(pval, {})
            merged[pval].update(benchmap)

        final_rows = {}
        for pval, benchmap in merged.items():
            final_rows[pval] = [benchmap.get(b, "") for b in bench_cols]

        write_table(out_path, header, final_rows)
        print(f"Wrote/updated: {out_path}")

if __name__ == "__main__":
    main()
