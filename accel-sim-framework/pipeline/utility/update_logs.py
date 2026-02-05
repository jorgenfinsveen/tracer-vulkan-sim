#!/usr/bin/env python

import os
import sys
import yaml
import time
import argparse

from pathlib import Path
from itertools import islice
from datetime import datetime
from typing import Optional, Iterable

DEBUG = False

parser = argparse.ArgumentParser(description="Parameters to pass to the script.")
parser.add_argument("--target", required=True, help="Datetime to search for in the logs. Format: %Y_%m_%d__%H_%M")
parser.add_argument("--logs", required=True, help="Absolute path to simulator_logs.yaml.")
parser.add_argument("--pipeline", required=True, help="Absolute path to pipeline.yaml.")
parser.add_argument("--job_name", required=True, help="Name of the job (contains commit-hashes for accel-sim and gpgpu-sim).")
args = parser.parse_args()

logs = {}
'''Dictionary of the contents of simulator_logs.yaml'''

target = {}
'''Sub-dictionary of the contents of simulator_logs.yaml'''

pipeline = {}
'''Dictionary of the contents of pipeline.yaml'''

experiment_name = ""

def nonexistent_error(filename, filepath):
    gpgpusim_root = os.getenv("GPGPUSIM_ROOT")
    error_logs = os.path.join(gpgpusim_root, "../../pipeline/setup/pipeline.yaml")
    with open(error_logs, "a",encoding="utf-8") as f:
        f.write(f"[{args.target}] unable to find {filename} at: {filepath}")
    print(f"[{args.target}] unable to find {filename} at: {filepath}")
    sys.exit(1)


def parse_sim_logs():
    global logs
    logfile = os.path.expandvars(args.logs)
    if not os.path.exists(logfile):
        Path(logfile).touch()
    with open(logfile, "r", encoding="utf-8") as f:
        logs = yaml.safe_load(f) or {}


def parse_pipeline_config():
    global pipeline, experiment_name
    configfile = os.path.expandvars(args.pipeline)
    if not os.path.exists(configfile):
        nonexistent_error("pipeline.yaml", configfile)
    with open(configfile, "r", encoding="utf-8") as f:
        pipeline = yaml.safe_load(f) or {}
        experiment_name = pipeline["experiment"]["name"]
        pipeline["experiment"] = parse_experiment(pipeline["experiment"])


def parse_experiment(experiment):
    path = os.path.expandvars(experiment["path"])
    name = experiment["name"]
    if not os.path.exists(path):
        nonexistent_error("experiments.yaml", path)
    with open(path, "r", encoding="utf-8") as f:
        experiments = yaml.safe_load(f) or {}
        if not experiments[name]:
            nonexistent_error(f"field {name} in experiments.yaml", path)
        return experiments[name]
    

def extract_commit_hashes(s, start, end: Optional[str] = None):
    i = s.find(start)
    if i == -1:
        return ""

    start_idx = i + len(start)
    if end is None:
        return s[start_idx:]

    j = s.find(end, start_idx)
    return s[start_idx:j] if j != -1 else ""


def cast_value(v: str):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v
        
def get_config_value(path: str, field: str):
    wanted = f"-{field}"
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) > 1 and parts[0] == wanted:
                return cast_value(parts[1])
    return None


def iter_target_dirs(root: Path, allowed_names: Iterable[str]):
    allowed = set(allowed_names)
    dirs = []
    if DEBUG:
        print(f"DIRS: {root}")
    for d in root.rglob("*"):
        if DEBUG:
            print(f"name: {d.name}")
            print(f"is dir: {d.is_dir()}")
            print(f"allowed: {d.name in allowed}\n")
        if d.is_dir() and d.name in allowed:
            dirs.append(d)
            # path = os.path.join(d, args.target, '.o')
            # if os.path.exists(path):
            #     print(f"\t- {d}")
            #     yield d
    return dirs

def read_if_exists(path: Path) -> str:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")

def search_first_lines(path, s, n=30):
    BYTES_TO_READ = int(250 * 1024 * 1024)
    count = 0
    f = open(path)
    fsize = int(os.stat(path).st_size)
    if fsize > BYTES_TO_READ:
        f.seek(0, os.SEEK_END)
        f.seek(f.tell() - BYTES_TO_READ, os.SEEK_SET)
    lines = f.readlines()
    for line in lines:
        count += 1
        if count >= n:
            return ""
        if line.startswith(s):
            return line.strip()

def collect_instance_stats(root, param_fields, result_fields, allowed_names: list[str]) -> tuple[list, list, dict]:
    root = Path(root)

    results = {}
    benchmarks = []
    configs = []
    benchmarks_d = {}
    for d in iter_target_dirs(root, allowed_names):
        out_path = os.path.join(d, f"{args.target}.o")
        cnf_path = os.path.join(d, 'gpgpusim.config')


        dirs = list(Path(d).parts)
        config = str(dirs[-1])
        bench_param = str(dirs[-2])
        benchmark = str(dirs[-3])

        if DEBUG:
            print(f"dirs: {dirs}")
            print(f"config: {config}")
            print(f"bench_param: {bench_param}")
            print(f"benchmark: {benchmark}")

        if not any(config in c for c in configs):
            entry = f"{config};"
            for field in param_fields:
                entry += f";{field}="
                val = get_config_value(cnf_path, field)
                entry += str(val) if val is not None else str(-1)
            configs.append(entry)

        if benchmark not in benchmarks_d:
            benchmarks_d[benchmark] = [benchmark]

        if bench_param not in list(benchmarks_d[benchmark]):
            benchmarks_d[benchmark].append(f"{bench_param}")
        # for b in benchmarks_d[benchmark]:
        #     for entry in 
        #     if bench_param not in b:
        #         benchmarks_d[benchmark].append(f"{bench_param}")

        if config not in allowed_names:
            continue
        
        if config not in results:
            results[config] = {}

        if benchmark not in results[config]:
            results[config][benchmark] = {}

        if bench_param not in results[config][benchmark]:
            results[config][benchmark][bench_param] = {}


        line = search_first_lines(out_path, "node")
        node = line.split(":")[1] if len(line.split(":")) > 1 else ""


        results[config][benchmark][bench_param]["node"] = node

        for field in result_fields:
            results[config][benchmark][bench_param][field] = "REPLACE_VALUE"

    for entry in benchmarks_d.values():
        s = ""
        for part in entry:
            s += part + ";"
        benchmarks.append(s[:-1])
    return configs, benchmarks, results


def main():
    time.sleep(10)
    parse_sim_logs()
    parse_pipeline_config()

    global logs, target
    if logs is None:
        logs = {}

    if f"sim-{args.target}" in logs and isinstance(logs[f"sim-{args.target}"], dict):
        target = logs[f"sim-{args.target}"]
    else:
        target = {}
        logs[f"sim-{args.target}"] = target

    target["accelsim-commit"] = extract_commit_hashes(args.job_name, "accelsim-commit-", "gpgpu-sim_git-commit-")
    target["gpgpusim-commit"] = extract_commit_hashes(args.job_name, "gpgpu-sim_git-commit-")
    target["date"] = datetime.strptime(args.target, "%Y_%m_%d__%H_%M").strftime("%Y-%m-%d %H:%M")
    target["benchmarks"] = pipeline.get("benchmarks", [])
    
    param_fields = pipeline.get("experiment", {}).get("params", [])
    result_fields = pipeline.get("experiment", {}).get("results", [])
    instances = pipeline.get("instances", [])
    
    if DEBUG:
        print(experiment_name)
        print(f"param_fields: {param_fields}")
        print(f"result_fields: {result_fields}")
        print(f"instances: {instances}")

    root = f"{os.path.expandvars(pipeline['results_dir'])}/output/{experiment_name}"
    
    f"{os.getenv('ACCEL_SIM')}/pipeline/"
    configs, benchmarks, results = collect_instance_stats(root, param_fields, result_fields, instances)

    target["configs"] = configs
    target["benchmarks"] = benchmarks
    target["results"] = results

    new_logs = {f"sim-{args.target}": logs[f"sim-{args.target}"]}
    for k, v in logs.items():
        if k != f"sim-{args.target}":
            new_logs[k] = v

    logfile = os.path.expandvars(args.logs)
    with open(logfile, "w", encoding="utf-8") as f:
        yaml.dump(new_logs, f, sort_keys=False, allow_unicode=True)
main()