# Perf Audit Skill (v6.1)

Deep paid performance audit for Headout Combined Entities (CEs). Produces a 10-section diagnostic report with sized actions.

## What It Does

Three-layer pipeline:
1. **Data Collection** — `engine/sources/bq.py` queries BigQuery for CE health, channel attribution, campaign cohorts, budget/bidding, geo coverage, landing pages, and ad group performance
2. **Table Rendering** — `engine/render/audit_skeleton.py` produces a markdown skeleton with pre-formatted tables and `<!-- NARRATIVE -->` markers
3. **Diagnostic Narrative** — Claude walks the `DIAGNOSTICS.md` hypothesis trees against the data and fills in analyst-quality narrative for each section

## Report Structure

| Section | Content | Source |
|---------|---------|--------|
| 1. Executive Summary | Status + causal story + actions | Claude (written LAST) |
| 2. CE Overview | Revenue, ROI(1), TR, CR, AOV | Engine (combined_entity_stats) |
| 3. Channel Breakdown | All channels by revenue | Engine (fct_orders) |
| 4. Paid Deep Dive | Search + PMax + Bing metrics, landing pages | Engine (ads_campaign_stats + pmax) |
| 5. Coverage | Campaign cohorts, budget/bidding, geo | Engine (google_ads_campaign_stats) |
| 6. External Dynamics | Demand, competition, money on table | Claude + Ahrefs MCP |
| 7. Funnel | LP → S → C → O conversion | Claude (Mixpanel query) |
| 8. Search Intelligence | Ad group coverage, search term clusters | Engine + CSV upload |
| 9. Red Flags | Consolidated issues | Claude |
| 10. Actions | Specific, sized, owned, timed | Claude |

## Prerequisites

- **Python 3.9+**
- **google-cloud-bigquery** package: `pip install google-cloud-bigquery`
- **BigQuery access** to `headout-analytics` project (EU location)
- **Authentication**: `gcloud auth application-default login`

### Optional
- **Ahrefs MCP** — for demand/volume trends (Section 6a)
- **Slack MCP** — for SP/supply context

## Quick Start

```bash
# Clone
git clone git@github.com:aaradhyaraiHO/perf-audit-skill.git
cd perf-audit-skill

# Install dependency
pip install google-cloud-bigquery

# Test connectivity
python3 -c "from google.cloud import bigquery; print(bigquery.Client(project='headout-analytics', location='EU').query('SELECT 1').result())"

# Run an audit
python3 perf_audit.py render \
  --ce-id 1173 --ce-name "GBTB" --market "Southeast Asia" \
  --l4w-start 2026-04-21 --l4w-end 2026-05-18 \
  --p4w-start 2026-03-24 --p4w-end 2026-04-20 \
  --ly-start 2025-04-28 --ly-end 2025-05-25 \
  --output perf-audit-gbtb-2026-05-21-v6.md
```

## Installation as Claude Code Skill

See [INSTALL.md](INSTALL.md) for full instructions. Quick version:

```bash
# In your project's .claude/settings.json, add:
{
  "skills": [
    {
      "path": "/path/to/perf-audit-skill/SKILL.md"
    }
  ]
}
```

Then use: `/perf-audit-v6 "Louvre Museum"`

## Running Without the Engine

If you prefer Claude to run queries directly (no Python):
1. Read `references/sql-reference.md` for all parameterized queries
2. Read `references/schema-guide.md` for table schemas
3. Read `references/metric-definitions.md` for formula reference
4. Claude runs queries via BQ CLI and builds the report manually

## File Map

```
SKILL.md              — Main skill instructions (Claude reads this)
DIAGNOSTICS.md        — 12 diagnostic hypothesis trees
EVAL.md               — 7-theme quality rubric + pre-ship gates

engine/               — Python package
  cli.py              — Entry point (data + render subcommands)
  metrics.py          — 13 metric formula functions
  sources/bq.py       — 20 BigQuery fetch functions
  render/audit_skeleton.py — Markdown table renderer

perf_audit.py         — Top-level entry point script

references/           — Standalone reference docs
  sql-reference.md    — All queries extracted from bq.py
  schema-guide.md     — BQ table schemas and join keys
  metric-definitions.md — Metric formulas with Omni validation

evals/                — Evaluation test cases
  cases/template.md   — Template for new eval cases
```
