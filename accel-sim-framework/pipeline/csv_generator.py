#!/usr/bin/env python3


import argparse
import csv
import re
import sys
from pathlib import Path

def extract_block(text: str, metric: str):
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

        bench = [x.strip() for x in lines[j].split(",")[1:]]
        rows = {}

        for k in range(j + 1, len(lines)):
            s = lines[k].strip()
            if not s or s.startswith("-"):
                break
            if "\\s*=" in s and not m_re.search(s):
                break

            parts = [p.strip() for p in lines[k].split(",")]
            if len(parts) >= 2:
                cfg, vals = parts[0], parts[1:]
                vals += [""] * (len(bench) - len(vals))
                rows[cfg] = vals[:len(bench)]

        return bench, rows

    raise SystemExit(f"metric not found: {metric}")

def main():
    inp = Path(sys.argv[1])
    metric = sys.argv[2]

    bench, rows = extract_block(inp.read_text(errors="replace"), metric)

    out = inp.parent / f"{inp.stem}_{re.sub(r'\\W+', '_', metric)}.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["CFG"] + bench)
        for cfg in sorted(rows):
            w.writerow([cfg] + rows[cfg])

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: collect.py <input_csv> <metric>")
    main()