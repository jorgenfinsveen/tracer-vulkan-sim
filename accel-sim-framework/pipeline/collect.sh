#!/bin/bash

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SIM_NAME="${SIM_NAME:-run-20240723-1728}"
LOG_DIR="$ROOT/util/job_launching/logfiles"
RESULTS_ROOT="$ROOT/pipeline/results"

RUN_ID="$1"
RUN_DIR="$RESULTS_ROOT/$RUN_ID"

LOGFILE="$(ls -t "$LOG_DIR"/sim_log."$SIM_NAME"-"$RUN_ID"* 2>/dev/null | head -n 1)"
echo "$LOGFILE"

python3 ./util/job_launching/get_stats.py -k -R -r "$RUN_DIR" -l "$LOGFILE" \
  > "$RUN_DIR/$RUN_ID.csv"

echo "Ferdig å lage csv fil."