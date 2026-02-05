#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

def find_get_stats(pipeline_root: Path) -> Path:
    candidates = [
        pipeline_root / "util" / "job_launching" / "get_stats.py",
        pipeline_root.parent / "util" / "job_launching" / "get_stats.py",
        pipeline_root / "accel-sim-framework" / "util" / "job_launching" / "get_stats.py",
        pipeline_root.parent / "accel-sim-framework" / "util" / "job_launching" / "get_stats.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise SystemExit("Could not find get_stats.py (edit find_get_stats() with the correct path).")

def parse_weird_csv_blocks(text: str):
    lines = text.splitlines()
    out = {}

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        if "\\s*=" not in line:
            i += 1
            continue

        metric = line.split("\\s*=", 1)[0].strip().strip(",")
        if not metric:
            i += 1
            continue

        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines) or not lines[j].startswith("CFG,"):
            i += 1
            continue

        headers = [x.strip() for x in lines[j].split(",")[1:]]
        rows = {}

        k = j + 1
        while k < len(lines):
            s = lines[k].strip()
            if not s or s.startswith("-"):
                break
            if "\\s*=" in s:
                break

            parts = [p.strip() for p in lines[k].split(",")]
            if len(parts) >= 2:
                cfg = parts[0]
                vals = parts[1:]
                vals += [""] * (len(headers) - len(vals))
                rows[cfg] = vals[:len(headers)]
            k += 1

        out[metric] = (headers, rows)
        i = k
    return out

def merge_blocks(all_blocks: list[dict]):
    """
    Merge many parsed weird-csv dicts into one:
      - union headers for each metric (preserve first-seen order)
      - align/pad row values to merged headers
    """
    merged = {}

    for blocks in all_blocks:
        for metric, (hdrs, rows) in blocks.items():
            if metric not in merged:
                merged[metric] = (list(hdrs), {cfg: list(vals) for cfg, vals in rows.items()})
                continue

            m_hdrs, m_rows = merged[metric]
            idx_map = {h: ix for ix, h in enumerate(m_hdrs)}

            new_headers = []
            for h in hdrs:
                if h not in idx_map:
                    idx_map[h] = len(m_hdrs) + len(new_headers)
                    new_headers.append(h)
            if new_headers:
                m_hdrs.extend(new_headers)
                for cfg in m_rows:
                    m_rows[cfg].extend([""] * len(new_headers))

            for cfg, vals in rows.items():
                if cfg not in m_rows:
                    m_rows[cfg] = [""] * len(m_hdrs)

                for h, v in zip(hdrs, vals):
                    if v == "":
                        continue
                    m_rows[cfg][idx_map[h]] = v

    return merged

def write_weird_csv(path: Path, merged: dict):
    lines = []
    for metric in sorted(merged.keys()):
        hdrs, rows = merged[metric]
        lines.append(f"{metric}\\s*=\\s*(.*),,,,")
        lines.append("CFG," + ",".join(hdrs))
        for cfg in sorted(rows.keys()):
            lines.append(cfg + "," + ",".join(rows[cfg]))
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n")

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: collect.py <RUN_ID>  (e.g. 2026_02_04__09_15)")

    run_id = sys.argv[1].strip()

    pipeline_root = Path(__file__).resolve().parent
    results_root = pipeline_root / "results"
    output_root = results_root / "output"

    get_stats = find_get_stats(pipeline_root)

    o_files = sorted(output_root.rglob(f"sim-{run_id}.o"))
    if not o_files:
        raise SystemExit(f"No .o files found for sim-{run_id}.o under {output_root}")

    out_total_dir = results_root / "export" / "total"
    out_total_dir.mkdir(parents=True, exist_ok=True)
    out_total_csv = out_total_dir / f"{run_id}.csv"

    print("Found .o files:")
    for p in o_files:
        print(f"  {p}")

    ans = input(f"Generate total CSV at {out_total_csv}? [y/N] ").strip().lower()
    if ans != "y":
        raise SystemExit("Aborted.")

    parsed_blocks = []
    for p in o_files:
        run_dir = p.parent
        cmd = ["python3", str(get_stats), "-k", "-R", "-r", str(run_dir), "-l", str(p)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"\nERROR running get_stats on: {p}")
            print(res.stderr)
            raise SystemExit(res.returncode)

        parsed_blocks.append(parse_weird_csv_blocks(res.stdout))

    merged = merge_blocks(parsed_blocks)
    write_weird_csv(out_total_csv, merged)

    print(f"\nWrote total CSV: {out_total_csv}")
    print("Ferdig :)")

if __name__ == "__main__":
    main()
