# CE Health Skill

CE briefing packet — everything you need to know about a CE before starting any depth analysis.

## What it produces

| Section | What it shows |
|---------|---------------|
| CE Metadata | Name, market, category, management type, status |
| CE Vitals | Revenue, ROI(1), TR, CR, AOV, Orders × 4 windows |
| Channel Breakdown | Per-channel revenue split (Google Search, PMax, Bing, Organic, etc.) |
| Funnel | LP2S, S2C, C2O overall × 4 windows |
| L12M Trajectory | Monthly CE health + paid performance (always included) |
| Top TGIDs | Top 10 experiences by revenue with deltas |
| Shapley Diagnosis | $ attribution per driver (Traffic, CVR, AOV, TR, CR) |
| Historical Context | Past audits + Slack discussions |

## Usage

```bash
/ce-health "Louvre Museum" --range l4w       # last 4 weeks
/ce-health 252 --range l1w                   # last 1 week
/ce-health 252 --range l3m                   # last 3 months
/ce-health 252 --range month                 # alias for l1m
/ce-health 189 --start 2026-03-06 --end 2026-04-05  # custom dates
```

**Range syntax:** `l<N>w` (N weeks) or `l<N>m` (N months). Any number works.

## Install

1. Copy `SKILL.md` to `.claude/skills/ce-health/SKILL.md` in your analytics repo
2. Copy `ce_health.py` to `scripts/ce_health.py`
3. Ensure `scripts/perf_audit_engine_v6/` exists (reuses BQ helpers and formatters)

## Requirements

- Python 3.9+
- `google-cloud-bigquery`
- BigQuery access to `headout-analytics` project
- Slack MCP (optional, for historical context search)

## Window Structure

Every range produces **4 comparison windows**:

- **Current** — the period being analyzed
- **Prior** — same duration immediately before (WoW/MoM sequential)
- **LY Current** — same period last year (YoY)
- **LY Prior** — prior period last year (seasonal context)

Column labels adapt: `TW/LW` for weekly, `TM/LM` for monthly, `L4W/P4W` for 4-week, etc.

## Related Skills

- [`perf-audit-skill`](https://github.com/aaradhyaraiHO/perf-audit-skill) — Deep paid-channel diagnostic
- `/cvr-rca` — Funnel CVR root cause analysis
- `/availability-diagnostics` — Supply/inventory health check
