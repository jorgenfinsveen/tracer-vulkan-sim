#!/usr/bin/env python3
import os
import sys
import yaml
import utility.parser as ps

from pathlib import Path

DIR_PATH = Path(__file__).resolve().parent
PIPELINE_CONFIG_FILE = os.path.join(DIR_PATH, "setup", "pipeline.yaml")

pipeline = {}


def parse_pipeline_config():
    global pipeline
    pipeline = ps.get_pipeline(PIPELINE_CONFIG_FILE)
    for dest in ["trace_lookup", "results_dir"]:
            pipeline[dest] = os.path.expandvars(pipeline[dest])
    for dest in pipeline["config_destinations"]:
            pipeline["config_destinations"][dest] = os.path.expandvars(pipeline["config_destinations"][dest]) 


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: collect.py <RUN_ID>  (e.g. 2026_02_04__09_15)")

    run_id = sys.argv[1].strip()

    parse_pipeline_config()

    results_dir = os.path.expandvars(pipeline['results_dir'])
    output_dir = os.path.join(results_dir, "output", pipeline['experiment']['name'])
    export_dir = os.path.join(results_dir, "export", "total")

    export_csv = os.path.join(export_dir, f"{run_id}.csv")
    executable = os.path.join(DIR_PATH, "util", "job_launching", "get_stats.py")

    benchmarks = ",".join(pipeline['benchmarks'])
    configs = ",".join(pipeline['instances'])

    lines = []
    lines.append("#!/usr/bin/env bash")
    lines.append("set -euo pipefail\n")

    lines.append(f'mkdir -p {export_dir}\n')

    lines.append(f'{executable} \\')
    lines.append('\t-A \\')
    lines.append('\t-k \\')
    lines.append('\t-R \\')
    lines.append('\t-o True \\')
    lines.append(f'\t-C {configs} \\')
    lines.append(f'\t-l {run_id} \\')
    lines.append(f'\t-B {benchmarks} \\')
    lines.append(f'\t-r {output_dir} \\')
    lines.append(f'\t > {export_csv}')

    lines.append('\necho "Ferdig :)"')

    export_sh = os.path.join(results_dir, f"2collect_{run_id}.sh")
    with open(export_sh, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(f"{line}\n")

    os.system(f"chmod +x {export_sh}")

    print(f"Wrote: {export_sh}")
    ans = input("Run it now? [y/N]: ").strip().lower()
    if ans == "y":
        os.system(f'bash {export_sh}')
    run_csv_generator = input("Run csv generator for the test result? [y/N]: ")
    if run_csv_generator == "y":
        os.system(f'./utility/csv_generator.py')
if __name__ == "__main__":
    main()
