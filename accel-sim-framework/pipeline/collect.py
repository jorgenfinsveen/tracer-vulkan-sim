#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: collect.py <RUN_ID>  (e.g. 2026_02_04__09_15)")

    run_id = sys.argv[1].strip()

    pipeline_root = Path(__file__).resolve().parent
    results_root  = pipeline_root / "results"
    output_root   = results_root / "output"

    get_stats = pipeline_root.parent / "util" / "job_launching" / "get_stats.py"
    if not get_stats.exists():
        get_stats = pipeline_root / "util" / "job_launching" / "get_stats.py"
    if not get_stats.exists():
        raise SystemExit(f"Cannot find get_stats.py (edit path). Tried:\n  {pipeline_root.parent / 'util/job_launching/get_stats.py'}\n  {pipeline_root / 'util/job_launching/get_stats.py'}")

    o_files = sorted(output_root.rglob(f"sim-{run_id}.o"))
    if not o_files:
        raise SystemExit(f"No .o files found for sim-{run_id}.o under {output_root}")

    sh_path = results_root / f"collect_{run_id}.sh"

    lines = []
    lines.append("#!/bin/bash")
    lines.append("set -euo pipefail")
    lines.append(f'RUN_ID="{run_id}"')
    lines.append(f'GET_STATS="{get_stats}"')
    lines.append('echo "Found .o files:"')
    for p in o_files:
        lines.append(f'echo "  {p}"')
    lines.append('echo "Generating per-run CSV next to each .o file..."')

    for p in o_files:
        run_dir = p.parent
        out_csv = run_dir / f"{run_id}.csv"
        lines.append(f'echo "-> {p}"')
        lines.append(f'python3 "$GET_STATS" -k -R -r "{run_dir}" -l "{p}" > "{out_csv}"')
        lines.append("")

    lines.append('echo "Ferdig :)"')

    sh_path.write_text("\n".join(lines) + "\n")
    sh_path.chmod(0o755)

    print(f"Wrote: {sh_path}")
    ans = input("Run it now? [y/N] ").strip().lower()
    if ans == "y":
        subprocess.run(["bash", str(sh_path)], check=True)

if __name__ == "__main__":
    main()
