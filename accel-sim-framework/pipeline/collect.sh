#!/bin/bash

cd "$ACCEL_SIM"

SIM_NAME="${SIM_NAME:-run-20240723-1728}"
RESULTS_ROOT="$ACCEL_SIM/pipeline/results"
LOG_DIR="$ACCEL_SIM/util/job_launching/logfiles"
OUT_DIR="$ACCEL_SIM/pipeline"

RUN_ARG="${1:-}"

LOGFILE="$(ls -t "$LOG_DIR"/sim_log."$SIM_NAME"-* | head -n 1)"

if [[ -n "$RUN_ARG" ]]; then
  RUN_DIRS=( "$RESULTS_ROOT/$RUN_ARG/" )
else
  RUN_DIRS=( "$RESULTS_ROOT"/*/ )
fi

TMP1="$(mktemp)"
TMP2="$(mktemp)"
trap 'rm -f "$TMP1" "$TMP2"' EXIT

FIRST=1

for RUN_DIR in "${RUN_DIRS[@]}"; do
  ./util/job_launching/get_stats.py -k -R -r "$RUN_DIR" -l "$LOGFILE" > "$TMP1"

  if [[ $FIRST -eq 1 ]]; then
    cat "$TMP1" > "$TMP2"
    FIRST=0
  else
    tail -n +2 "$TMP1" >> "$TMP2"
  fi
done

mv "$TMP2" "$OUT_DIR/render_passes_2k.csv"

echo "Fila er ferdiglaga"