---
name: ce-health
description: "CE briefing packet — metadata, vitals, channels, funnel, L12M trajectory, top TGIDs, Shapley driver diagnosis, and historical context. Usage: /ce-health <CE name or ID> --range l<N>w|l<N>m (e.g. l4w, l2m, week, month) OR --start YYYY-MM-DD --end YYYY-MM-DD. Atom skill invoked by perf-audit, weekly review, monthly review, or standalone."
allowed-tools: [Bash, Read, Write, mcp__plugin_weekly-growth-review_slack__slack_search_public_and_private]
---

# CE Health Briefing Packet

Get the full context on a CE before starting any depth analysis. Produces metadata, vitals across dynamic time windows, channel breakdown, funnel, L12M trajectory, top TGIDs, Shapley driver diagnosis, and historical context (past audits + Slack).

**Audience:** Any analyst, GM, or parent skill needing CE context.

## When to Use

- Before running `/perf-audit-v6` — understand the CE first
- Before a deep dive in weekly/monthly review — get the vitals
- GM asks "how's X doing?" — run this for a quick health check
- Any time you need CE context with dynamic date ranges

## Usage

```bash
/ce-health "Louvre Museum" --range l1w       # last 1 week
/ce-health 252 --range l4w                   # last 4 weeks
/ce-health "Eiffel Tower" --range l3m        # last 3 months
/ce-health 189 --range l6m                   # last 6 months
/ce-health 252 --range week                  # alias for l1w
/ce-health 252 --range month                 # alias for l1m
/ce-health 189 --start 2026-03-06 --end 2026-04-05  # custom dates
```

**Range syntax:** `l<N>w` (N weeks) or `l<N>m` (N months). Any number works.
**Aliases:** `week` = `l1w`, `month` = `l1m`, `3m` = `l3m`, `6m` = `l6m`

---

## Execution Steps

### Step 1 — Resolve CE

If user gave a name (not a numeric ID), resolve it:
```bash
cd ~/analytics && python3 -c "
from google.cloud import bigquery
client = bigquery.Client(project='headout-analytics', location='EU')
rows = list(client.query(\"\"\"
    SELECT combined_entity_id, combined_entity_name, market
    FROM analytics_reporting.dim_combined_entities
    WHERE LOWER(combined_entity_name) LIKE LOWER('%<CE_NAME>%')
    LIMIT 5
\"\"\").result())
for r in rows: print(f'{r.combined_entity_id}: {r.combined_entity_name} ({r.market})')
"
```

If multiple matches, pick the best one or ask the user.

### Step 2 — Run the renderer

```bash
cd ~/analytics && python3 scripts/ce_health.py \
  --ce-id <CE_ID> \
  --range <RANGE> \
  --output thoughts/shared/ce-health/<slug>-<date>.md
```

Or with custom dates:
```bash
cd ~/analytics && python3 scripts/ce_health.py \
  --ce-id <CE_ID> \
  --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
  --output thoughts/shared/ce-health/<slug>-<date>.md
```

### Step 3 — Read the output

Read the generated markdown file. All 8 sections are pre-rendered.

### Step 4 — Search Slack for CE context

Run **two searches** for the CE name:

```
slack_search_public_and_private("<CE Name> after:<6 months ago>")
slack_search_public_and_private("<CE Name> MMP after:<12 months ago>")
```

Look for: MMP execution status, assortment changes, SP issues, perf team notes, product restructuring, operational incidents, strategic initiatives.

**CRITICAL: Write findings back into the report file.** Replace the `*Slack context: searched by SKILL.md after script renders.*` line in Section 8 with a structured summary under a `### Slack Context` heading. Group by: MMP & Assortment, Supply & Operations, Strategic. The report file must be self-contained — a reader should not need to search Slack again.

### Step 4b — Read MMP docs found in Slack

If Slack results contain links to Google Docs or Sheets (MMP plans, execution trackers, assortment docs), **read them** using the `gws` CLI:

```bash
# For Google Docs:
gws docs documents get --params '{"documentId": "<DOC_ID>"}'

# For Google Sheets:
gws sheets spreadsheets values get --params '{"spreadsheetId": "<SHEET_ID>", "range": "Sheet1"}'
```

Extract the doc ID from the URL (`docs.google.com/document/d/<DOC_ID>/...` or `docs.google.com/spreadsheets/d/<SHEET_ID>/...`).

Look for: MMP plan details (what was planned vs executed), assortment decisions, pricing changes, SP terms, launch timelines. Add a `### MMP Context` subsection to Section 8 with:
- **MMP status:** Completed / In Progress / Planned
- **Key decisions:** assortment changes, pricing, SP terms
- **Open items:** anything pending that affects CE health

If `gws` is unavailable or the doc can't be read, note the link in Section 8 for manual review.

### Step 5 — Prompt user for additional context

Present the briefing packet and ask:

> **Add your context:** Any thoughts, links, Slack threads, or hypotheses before we go deeper?

Wait for user input. They may add links, paste data, or say "looks good, proceed to perf audit."

---

## Report Sections

| # | Section | What it shows |
|---|---------|---------------|
| 1 | CE Metadata | Name, market, category, management type, status |
| 2 | CE Vitals | Revenue, ROI(1), TR, CR, AOV, Orders × 4 windows |
| 3 | Channel Breakdown | Per-channel revenue split with v6.1 taxonomy |
| 4 | Funnel | LP2S, S2C, C2O overall × 4 windows |
| 5 | L12M Trajectory | Monthly CE health + paid performance (always) |
| 6 | Top TGIDs | Top 10 experiences by revenue with deltas |
| 7 | Shapley | $ attribution per driver (Traffic, CVR, AOV, TR, CR) |
| 8 | Historical Context | Past audits + Slack discussions |

## Window Structure (4 windows)

Every range produces 4 comparison windows:

- **Current** — the period being analyzed
- **Prior** — same duration immediately before (sequential: WoW/MoM)
- **LY Current** — same period last year (YoY)
- **LY Prior** — prior period last year (seasonal context)

Column labels adapt per range:
- `week`: TW, LW, LY TW, LY LW
- `month`: TM, LM, LY TM, LY LM
- `3m`: T3M, L3M, LY T3M, LY L3M
- Custom: actual date ranges as labels

## Requirements

- Python 3.9+
- BigQuery access: `headout-analytics` project
- Slack MCP: `slack_search_public_and_private` (for Step 4)

## Related Skills

- `/perf-audit-v6` — Deep paid-channel diagnostic (call after CE Health if paid is the driver)
- `/cvr-rca` — Funnel CVR root cause analysis (call if CVR is the Shapley primary driver)
- `/availability-diagnostics` — Supply/inventory health check
