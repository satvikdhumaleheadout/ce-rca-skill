#!/usr/bin/env bash
# run_analysis.sh — Runs all BQ queries and produces summary.json
#
# Usage:
#   ./run_analysis.sh <ce_id> [<pre_start> <pre_end> <post_start> <post_end>]
#
# Dates are optional. When omitted, defaults to:
#   post  = last 30 days  (yesterday back 30 days)
#   pre   = 30 days before that
#
# Examples:
#   ./run_analysis.sh 167
#   ./run_analysis.sh 167 2024-03-01 2024-03-30 2024-03-31 2024-04-29

set -euo pipefail

CE_ID="${1:?Usage: run_analysis.sh <ce_id> [pre_start pre_end post_start post_end]}"

# ── Default date windows (30/30) — override by passing all four date args ──────
_date_offset() {
  # Cross-platform: try BSD date (macOS) then GNU date (Linux)
  if date -v-"${1}"d '+%Y-%m-%d' 2>/dev/null; then return; fi
  date -d "${1} days ago" '+%Y-%m-%d'
}

PRE_START="${2:-$(_date_offset 60)}"
PRE_END="${3:-$(_date_offset 31)}"
POST_START="${4:-$(_date_offset 30)}"
POST_END="${5:-$(_date_offset 1)}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REFS_DIR="$SCRIPT_DIR/../references"

# ── Output directory — auto-increment if folder already exists ─────────────
# CVR_RCA_OUTPUT_DIR env var overrides the default; set it in ~/.zshrc to
# keep runs in a custom location (e.g. your existing "Test Runs" folder).
_BASE_DIR="${CVR_RCA_OUTPUT_DIR:-${HOME}/Documents/CVR RCA Runs}/ce${CE_ID}_${PRE_START}_${POST_END}"
if [ ! -d "$_BASE_DIR" ]; then
  OUTPUT_DIR="$_BASE_DIR"
else
  _N=2
  while [ -d "${_BASE_DIR}_run${_N}" ]; do
    _N=$(( _N + 1 ))
  done
  OUTPUT_DIR="${_BASE_DIR}_run${_N}"
  echo "Note: base folder already exists — writing to $(basename "$OUTPUT_DIR")"
fi
export OUTPUT_DIR

mkdir -p "$OUTPUT_DIR"

BQ="bq query --use_legacy_sql=false --format=json --quiet --max_rows=1000 --project_id=headout-analytics"

# ── Helper: substitute all placeholders in a SQL file ──────────────────────────
substitute_sql() {
  local sql_file="$1"
  local primary_mbho="${2:-ALL}"
  sed \
    -e "s/{{CE_ID}}/$CE_ID/g" \
    -e "s/{{PRE_START}}/$PRE_START/g" \
    -e "s/{{PRE_END}}/$PRE_END/g" \
    -e "s/{{POST_START}}/$POST_START/g" \
    -e "s/{{POST_END}}/$POST_END/g" \
    -e "s/{{PRIMARY_MBHO}}/$primary_mbho/g" \
    "$sql_file"
}

# ── Stage 0: CE metadata + top page URL (serial — populates report header) ────
echo "[0/4] Fetching CE metadata..."
substitute_sql "$REFS_DIR/q0_meta.sql" | $BQ > "$OUTPUT_DIR/stage0.json"
echo "      Done. $(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/stage0.json')); print(d[0].get('combined_entity_name', '(unknown)') if d else '(no rows)')")"

# ── Stage 1: Base funnel (always runs next, determines primary segment) ────────
echo "[1/4] Running base funnel query..."
substitute_sql "$REFS_DIR/q1_base.sql" | $BQ > "$OUTPUT_DIR/stage1.json"
echo "      Done. $(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/stage1.json')); print(len(d), 'rows')")"

# ── Determine primary MB/HO from Stage 1 results ──────────────────────────────
PRIMARY_MBHO=$(python3 - <<'PYEOF'
import json, sys, os
data = json.load(open(os.environ['OUTPUT_DIR'] + '/stage1.json'))
post = [r for r in data if r.get('mb_ho') not in ('ALL', None) and r.get('period') == 'post']
if not post:
    print('ALL')
    sys.exit()
agg = {}
for r in post:
    k = r['mb_ho']
    agg[k] = agg.get(k, 0) + int(r.get('users_lp') or 0)
print(max(agg, key=agg.get))
PYEOF
)
export OUTPUT_DIR PRIMARY_MBHO
echo "      Primary MB/HO: $PRIMARY_MBHO"

# ── Stage 3 + 7: Run in parallel ──────────────────────────────────────────────
echo "[2/4] Running daily trend and 90-day rolling trend + LY in parallel..."

substitute_sql "$REFS_DIR/q3_trend.sql" "$PRIMARY_MBHO" \
  | $BQ > "$OUTPUT_DIR/stage3.json" &
PID_Q3=$!

# Q7: 90-day rolling CVR trend + last-year equivalent (POST_END drives both windows)
substitute_sql "$REFS_DIR/q7_trend_and_ly.sql" \
  | $BQ > "$OUTPUT_DIR/stage7.json" &
PID_Q7=$!

wait $PID_Q3 && echo "      Daily trend done."
wait $PID_Q7 && echo "      90-day trend + LY done."

# ── Aggregate: raw JSON → summary.json ────────────────────────────────────────
echo "[3/4] Aggregating results..."
python3 "$SCRIPT_DIR/aggregate.py" \
  --stage0       "$OUTPUT_DIR/stage0.json" \
  --stage1       "$OUTPUT_DIR/stage1.json" \
  --stage3       "$OUTPUT_DIR/stage3.json" \
  --stage7       "$OUTPUT_DIR/stage7.json" \
  --ce_id        "$CE_ID" \
  --pre_start    "$PRE_START" \
  --pre_end      "$PRE_END" \
  --post_start   "$POST_START" \
  --post_end     "$POST_END" \
  --primary_mbho "$PRIMARY_MBHO" \
  --output       "$OUTPUT_DIR/summary.json"

echo ""
echo "Analysis complete."
echo "Summary  → $OUTPUT_DIR/summary.json"
echo "Raw data → $OUTPUT_DIR/stage{0,1,3,7}.json  (keep for debugging)"
echo "Windows  → pre: $PRE_START – $PRE_END  |  post: $POST_START – $POST_END"
# Changelog
# c001 2026-04-24 Initial version
# c002 2026-04-27 Default 30/30-day window — dates are now optional args; script
#                 computes POST_END=yesterday, POST_START=30d ago, PRE_END=31d ago,
#                 PRE_START=61d ago when not supplied. Cross-platform _date_offset()
#                 helper handles both BSD (macOS) and GNU (Linux) date.
# c003 2026-04-27 Output directory now includes pre_start and post_end dates:
#                 /tmp/cvr_rca_<ce_id>_<pre_start>_<post_end>/
#                 Prevents multiple runs on the same CE from overwriting each other.
# c004 2026-04-28 Output moved from /tmp to persistent run folder:
#                 ~/Documents/RCA skill/Test Runs/ce<ce_id>_<pre_start>_<post_end>/
#                 All outputs (summary.json, findings.md, report.html, transcript.md,
#                 evaluation.md) now live together in one folder per run.
