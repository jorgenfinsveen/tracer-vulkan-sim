#!/usr/bin/env python

import os
import sys
import yaml
import argparse
import subprocess

from typing import Optional
from datetime import datetime


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

def nonexistent_error(filename, filepath):
    gpgpusim_root = os.getenv("GPGPUSIM_ROOT")
    error_logs = os.path.join(gpgpusim_root, "../../pipeline/logs/pipeline.err")
    with open(error_logs, "a",encoding="utf-8") as f:
        f.write(f"[{args.target}] unable to find {filename} at: {filepath}")
    sys.exit(1)


def parse_sim_logs():
    global logs
    logfile = os.path.expandvars(args.logs)
    if not os.path.exists(logfile):
        nonexistent_error("simulator_logs.yaml", logfile)
    with open(logfile, "r", encoding="utf-8") as f:
        logs = yaml.safe_load(f) or {}


def parse_pipeline_config():
    global pipeline
    configfile = os.path.expandvars(args.pipeline)
    if not os.path.exists(configfile):
        nonexistent_error("pipeline.yaml", configfile)
    with open(configfile, "r", encoding="utf-8") as f:
        pipeline = yaml.safe_load(f) or {}
    

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

class NoQuotesDumper(yaml.SafeDumper):
    pass

def str_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='')


NoQuotesDumper.add_representer(str, str_representer)

def main():
    parse_sim_logs()
    parse_pipeline_config()

    global logs, target
    if logs is None:
        logs = {}

    if args.target in logs and isinstance(logs[args.target], dict):
        target = logs[args.target]
    else:
        target = {}
        logs[args.target] = target

    target["accelsim-commit"] = extract_commit_hashes(args.job_name, "accelsim-commit-", "gpgpu-sim_git-commit-")
    target["gpgpusim-commit"] = extract_commit_hashes(args.job_name, "gpgpu-sim_git-commit-")
    target["date"] = datetime.strptime(args.target, "%Y_%m_%d__%H_%M").strftime("%Y-%m-%d %H:%M")
    target["node"] = subprocess.check_output(["hostname"], text=True).strip()

    logs_path = os.path.expandvars(args.logs)
    logs_dir = os.path.dirname(os.path.abspath(logs_path))
    config_path = os.path.join(logs_dir, "gpgpusim.config")

    if not os.path.exists(config_path):
        nonexistent_error("gpgpusim.config", config_path)
    
    param_fields = pipeline.get("experiment", {}).get("params", [])
    params_list = []
    for field in param_fields:
        val = get_config_value(config_path, field)
        params_list.append({field: val if val is not None else -1})
    target["params"] = params_list

    result_fields = pipeline.get("experiment", {}).get("results", [])
    existing_results = {}

    if isinstance(target.get("results"), list):
        for d in target["results"]:
            if isinstance(d, dict) and len(d) == 1:
                (k, v), = d.items()
                existing_results[k] = v

    results_list = []
    for field in result_fields:
        results_list.append({field: existing_results.get(field, "REPLACE_VALUE")})
    target["results"] = results_list

    new_logs = {f"sim-{args.target}": logs[args.target]}
    for k, v in logs.items():
        if k != args.target:
            new_logs[k] = v

    with open(logs_path, "w", encoding="utf-8") as f:
        yaml.dump(new_logs, f, sort_keys=False, allow_unicode=True, Dumper=NoQuotesDumper)
        #yaml.safe_dump(new_logs, f, sort_keys=False, allow_unicode=True)

main()