#!/usr/bin/env python3

import os
import sys
import yaml
from pathlib import Path
from typing import Iterable, Optional

THIS_DIR: Path  = Path(__file__).resolve().parent
sys.path.append(str(THIS_DIR))


import model.pipeline, model.traces, model.experiment, model.simlog, model.config, model.outfile




PIPELINE_ROOT: Path  = THIS_DIR.parent
PIPELINE_SETUP_DIR: Path = os.path.join(PIPELINE_ROOT, 'setup')
PIPELINE_CONFIG_FILE: Path  = os.path.join(PIPELINE_SETUP_DIR, 'pipeline.yaml')

def nonexistent_error(path: Path) -> FileNotFoundError:
    raise FileNotFoundError(f"File not found: {path}")


def assert_file_exists(path: Path, exception=True) -> Path:
    path = Path(os.path.expandvars(str(path).strip()))
    if os.path.exists(path):
        return path
    if not exception:
        return None
    nonexistent_error(path)


def get_pipeline(path: Path="") -> model.pipeline.Pipeline:     # type: ignore
    if path == "":
        path = PIPELINE_CONFIG_FILE

    path = assert_file_exists(path)

    with open(path, 'r', encoding='utf-8') as f:  
        pl = yaml.safe_load(f) or {}
        return model.pipeline.get(pl, path)
    
def get_experiments(path: Path="") -> model.experiment.Experiments: # type: ignore
    if path == "": 
        path = get_pipeline().experiment.path

    path = assert_file_exists(path)

    with open(path, 'r', encoding='utf-8') as f:
        exp = yaml.safe_load(f) or {}
        return model.experiment.get(exp, path)
    
def get_experiment(name: str, path: Path="") -> model.experiment.Experiment: # type: ignore
    if path == "": 
        path = get_pipeline().experiment.path

    path = assert_file_exists(path)

    with open(path, 'r', encoding='utf-8') as f:
        exps = yaml.safe_load(f) or {}
        exps = model.experiment.get(exps, path)
        return model.experiment.get_experiment(exps, name.strip())


def get_traces(path: Path="") -> model.traces.Traces: # type: ignore
    if path == "":
        path = get_pipeline().trace_lookup
    
    path = assert_file_exists(path)

    with open(path, 'r', encoding='utf-8') as f:  
        tr = yaml.safe_load(f) or {}
        return model.traces.get(tr, path)


def get_simulator_logs(path: Path="") -> model.simlog.SimulatorLogs: # type: ignore
    if path == "":
        results_dir = os.path.expandvars(get_pipeline().results_dir)
        path = os.path.join(results_dir, 'output', 'simulator_logs.yaml')
    
    path = assert_file_exists(path)

    with open(path, 'r', encoding='utf-8') as f:  
        sl = yaml.safe_load(f) or {}
        return model.simlog.get(sl, path)


def get_config(path: Path) -> model.config.Config: # type: ignore
    path = assert_file_exists(path)
    return model.config.get(path)


def get_outfile(path: Path) -> model.outfile.Outfile: # type: ignore
    path = assert_file_exists(path)
    return model.outfile.get(path)


def iter_target_dirs(path: Path, allowed_names: Iterable[str], allowed_subnames: Iterable[str]=None) -> list[Path]:
    path = assert_file_exists(path)
    allowed = set(allowed_names)
    dirs = []
    for d in path.rglob("*"):
        if d.is_dir() and d.name in allowed:
            if not allowed_subnames:
                dirs.append(d)
            elif any(x in allowed_subnames for x in d.parts):
                dirs.append(d)
    return dirs


def search_in_string(s: str, start: str, end: Optional[str] = None) -> str:
    i = s.find(start)
    if i == -1:
        return ""
    start_idx = i + len(start)
    if end is None:
        return s[start_idx:]
    j = s.find(end, start_idx)
    return s[start_idx:j] if j != -1 else ""


def extract_commit_hashes(s: str) -> dict:
    return {
        'accelsim-commit': search_in_string(s, "accelsim-commit-", "gpgpu-sim_git-commit-"),
        'gpgpusim-commit': search_in_string(s, "gpgpu-sim_git-commit-")
    }

def get_line(path: Path, prefix: str, n=350):
    path = assert_file_exists(path)
    prefix = prefix.strip()
    if prefix == '' or prefix == '-':
        return None
    BYTES_TO_READ = int(250 * 1024 * 1024)
    count = 0
    with open(path, 'r', encoding='utf-8') as f:
        fsize = int(os.stat(path).st_size)
        if fsize > BYTES_TO_READ:
            f.seek(0, os.SEEK_END)
            f.seek(f.tell() - BYTES_TO_READ, os.SEEK_SET)
        lines = f.readlines()
        for line in lines:
            if not line or line.startswith('#'):
                continue
            count += 1
            if count >= n:
                return None
            if line.startswith(prefix):
                return line.strip()
        return None
    
def new_sim_log(path: Path=None) -> model.simlog.SimulatorLogs:
    return model.simlog.new_log(path)

def new_sim_log_entry() -> model.namespace.NS:
    return model.simlog.new_sim_log_entry()

def sim_logs_to_dict(x) -> dict:
    if hasattr(x, "_obj"):
        x = x._obj
    return model.namespace.to_dict(x)