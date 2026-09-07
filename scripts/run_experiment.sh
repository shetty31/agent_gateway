#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run a load test and generate a report into a timestamped run folder.
# Usage: scripts/run_experiment.sh [--scenario mixed] [--total 1000] [--concurrency 100] [--slo 50]

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PYTHON=${PYTHON:-"$ROOT/venv/bin/python"}

# Load and export variables from project .env so test processes inherit AGENT_KEY etc.
if [ -f "$ROOT/.env" ]; then
  echo "Loading environment from $ROOT/.env"
  # export all variables sourced from the file
  set -a
  # shellcheck disable=SC1090
  source "$ROOT/.env"
  set +a
fi

SCENARIO="mixed"
TOTAL=1000
CONC=100
SLO=50

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenario) SCENARIO="$2"; shift 2;;
    --total|--total-requests) TOTAL="$2"; shift 2;;
    --concurrency) CONC="$2"; shift 2;;
    --slo) SLO="$2"; shift 2;;
    --help) echo "Usage: $0 [--scenario name] [--total N] [--concurrency N] [--slo ms]"; exit 0;;
    *) echo "Unknown arg: $1"; exit 2;;
  esac
done

RUN_DATE=$(date +%F)
RUN_TS=$(date +%H%M%S)
SHORT_ID=$($PYTHON - <<'PY'
import uuid
print(str(uuid.uuid4())[:4])
PY
)

OUT_DIR="$ROOT/runs/$RUN_DATE/${RUN_TS}-${SHORT_ID}"
mkdir -p "$OUT_DIR"
mkdir -p "$OUT_DIR/plots"

echo "Run directory: $OUT_DIR"

# Create data symlink inside the run folder pointing to project root data/
if [ -e "$OUT_DIR/data" ] || [ -L "$OUT_DIR/data" ]; then
  rm -rf "$OUT_DIR/data"
fi
ln -sfn "$ROOT/data" "$OUT_DIR/data"

# Write run metadata
cat > "$OUT_DIR/run_metadata.json" <<JSON
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "scenario": "$SCENARIO",
  "total_requests": $TOTAL,
  "concurrency": $CONC,
  "slo_ms": $SLO,
  "run_id": "${RUN_TS}-${SHORT_ID}"
}
JSON

echo "Starting load tester (results -> $OUT_DIR/load_tester_results.json)"
set +e
$PYTHON tests/load_tester.py --scenario "$SCENARIO" --total-requests "$TOTAL" --concurrency "$CONC" --save-results --results-output "$OUT_DIR/load_tester_results.json"
RC=$?
set -e
if [ $RC -ne 0 ]; then
  echo "Load tester failed with exit code $RC" >&2
  exit $RC
fi

echo "Generating performance report into $OUT_DIR/performance_metrics.md"
"$PYTHON" scripts/generate_performance_report.py --input "$OUT_DIR/load_tester_results.json" --data-root "$ROOT/data" --output "$OUT_DIR/performance_metrics.md" --slo "$SLO"

# Update runs/latest symlink
LATEST_LINK="$ROOT/runs/latest"
ln -sfn "$OUT_DIR" "$LATEST_LINK"

echo "Run complete. Artifacts in: $OUT_DIR"
echo "Latest -> $LATEST_LINK"
echo "To view report: cat $OUT_DIR/performance_metrics.md"

exit 0
