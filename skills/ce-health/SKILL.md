---
name: ce-health
description: "CE briefing packet — metadata, vitals, channels, funnel, L12M trajectory, top TGIDs, Shapley driver diagnosis, and historical context. Usage: /ce-health <CE name or ID> --range l<N>w|l<N>m (e.g. l4w, l2m, week, month) OR --start YYYY-MM-DD --end YYYY-MM-DD. Atom skill invoked by perf-audit, weekly review, monthly review, or standalone."
# No allowed-tools pin: Slack/MCP server ids are environment-specific and differ per
# user, so a hard-coded id would silently block Slack on most installs. This skill
# inherits the session's tool permissions (like the ce-context sub-skill, which owns
# the primary Slack search). Slack tools are discovered dynamically at run time.
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
/ce-health 189 --start 2026-03-06 --end 2026-04-05  # custom dates (pre = preceding equal window)
/ce-health 189 --start 2026-05-01 --end 2026-05-31 --pre-start 2026-03-01 --pre-end 2026-03-31  # explicit baseline
```

**Range syntax:** `l<N>w` (N weeks) or `l<N>m` (N months). Any number works.
**Explicit baseline:** by default the pre window is the equal-length block
immediately before `--start/--end`. Pass `--pre-start/--pre-end` to override it
with **any** baseline — non-contiguous or unequal-length (e.g. post = May vs
pre = March). Only valid alongside `--start/--end`; both must be given together.
**Aliases:** `week` = `l1w`, `month` = `l1m`, `3m` = `l3m`, `6m` = `l6m`

---

## Execution Steps

### Step 0 (pre) — Stay on the latest version

CE Health ships **inside the CE-RCA bundle** and is never updated on its own — running it
refreshes the **whole** bundle from the `ce-rca-skill` repo. Set `SKILL_DIR` to the directory
this SKILL.md was read from, then run the shared guard (two levels up). It self-guards: only
the canonical `~/.ce-rca` install is ever rewritten; a dev checkout or an umbrella-dispatched
run is a no-op.

```bash
SKILL_DIR="<absolute dir this SKILL.md was read from>"   # e.g. ~/.ce-rca/skills/ce-health
bash "$SKILL_DIR/../../scripts/update_guard.sh" "<run_dir if you were dispatched by /ce-rca, else omit>"
```

- **`UPDATED <old> <new>`** — bundle refreshed in place (run folders untouched). Tell the user
  one line ("CE-RCA updated v`<old>` → v`<new>`") and **re-read `~/.ce-rca/skills/ce-health/SKILL.md`**,
  continuing from the top.
- **`CURRENT` / `OFFLINE` / `SKIPPED …`** — proceed on the installed version (3-second timeout).

### Step 0 — Context intake (standalone only)

Standalone, gather the analyst's context **up front** — it is what the per-section
one-liners are enriched from (the CE-Health-insights sub-agent reads it at Step 6) and
what the report's `user_context` subsection embeds. Run the onboarding questionnaire per
**`$SKILL_DIR/../../references/context_intake_guide.md`**, emphasis **ce-health** (LIGHT —
About-this-CE + known events + constraints; a briefing is orientation, so **no 1e
driver-hypothesis**), and write the answers to `<run_dir>/user_context.md` (the 8-slot
contract). Establish the `<run_dir>` now (the canonical-name dir Step 2 / Step 3b use) so
the file and the rendered artifacts share one directory.

**Standalone gate (run Step 0 only when standalone):** skip entirely if
`CE_CONTEXT_RUN_DIR` is set OR `<run_dir>/orchestration.json` exists OR
`<run_dir>/user_context.md` already exists — under `/ce-rca` the orchestrator captured
context once at its Step 1 (and runs the insights loop itself at its Step 3a/3b), so this
skill must neither re-ask nor re-run the loop. A "nothing to add" run leaves the slots
empty and the packet renders exactly as a bare run does.

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

### Step 3b — Beautified standalone HTML report (optional; needs the CE-RCA bundle)

The markdown above is the portable deliverable. For a **polished, browser-openable
HTML report** (metric cards, Plotly charts, the corrected Shapley waterfall), run the
CE-RCA bundle's renderer with `--standalone`. It needs the sidecar + markdown under
the **canonical names** `ce_health_report.{md,json}` in one run dir, so emit them that
way (the engine writes the `.json` sidecar next to the `--output` `.md`):

```bash
# 1) write the artifacts with canonical names into a run dir
python3 <ce-health-engine>/ce_health.py --ce-id <CE_ID> --range <RANGE> \
  --output <run_dir>/ce_health_report.md
# 2) wrap the beautified tab into an openable report.html
python3 <ce-rca-bundle>/scripts/render_ce_health.py --run-dir <run_dir> --standalone
```

`--standalone` writes **`<run_dir>/report.html`** (the shared
`standalone_report.wrap_fragment` adds the `<html>` shell + Plotly CDN + visual-kit
CSS + a lightweight CE banner, around the same beautified fragment the CE-RCA
composite embeds). **Graceful:** if the bundle renderer isn't reachable (e.g. running
purely in `~/analytics` without the bundle), skip this — the markdown from Step 2
remains the deliverable. (Under the `/ce-rca` orchestrator this is unnecessary — the
master renders the fragment without `--standalone` and `compose.py` builds the tab.)

**Standalone, the FINAL render runs at Step 6** — after the CE-Health-insights loop writes
`ce_health_insights.json`, so the report embeds the context-enriched per-section one-liners.
This Step-3b invocation is just an optional early preview (deterministic callouts only); if
you ran Step 0 (so a `user_context.md` exists), prefer producing `report.html` at Step 6.

### Step 4 — Search Slack for CE context

First **discover the Slack MCP tool dynamically** — never hard-code a server
namespace, it differs per user. Search by tool name:

```
ToolSearch("+slack search")
```

Call the tool by the **exact name ToolSearch returns** (your Slack MCP sets the
prefix, e.g. `mcp__<server-id>__slack_search_public_and_private`; the base name is
always `slack_search_public_and_private`). **If ToolSearch returns no Slack tool, no
Slack MCP is connected** — leave Section 8's Slack line as "Slack context unavailable"
and skip the searches (never fail the run).

Then run **two searches** for the CE name:

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

### Step 5 — Confirm context + proceed

The analyst's context was captured up front at **Step 0** (standalone) or by the umbrella
(orchestrated), so this is just a light confirm, not the main intake. Present the briefing
packet and ask:

> **Anything to add before we go deeper?** Links, Slack threads, or a correction — or "looks good, proceed to perf audit."

If they add anything material, fold it into `<run_dir>/user_context.md` (the same slots)
so Step 6's enrichment picks it up. Then proceed.

### Step 6 — CE Health insights (per-section one-liners) + final render (standalone only)

This is the **"Python computes, Claude phrases"** loop that gives each section a grounded,
context-enriched one-liner — ported from the umbrella so it runs standalone too. **Standalone
gate:** run this only when standalone (the same gate as Step 0); under `/ce-rca` the master
runs it at its Step 3a/3b and renders the tab, so **skip** here.

1. **Facts pack (deterministic).** Compute the numbers backbone the insights agent phrases:
   ```bash
   python3 "$SKILL_DIR/../../scripts/render_ce_health.py" --emit-facts --run-dir "<run_dir>"
   ```
   This writes `<run_dir>/ce_health_facts.json` (per-section numbers + flags; no bq).
2. **CE-Health-insights sub-agent.** Spawn one sub-agent: read
   `$SKILL_DIR/../../references/ce_health_insights_guide.md` and follow it exactly. Run dir:
   `<run_dir>`. Inputs: `ce_health_facts.json` + whatever context artifacts are present —
   standalone that is **`user_context.md`** (from Step 0) and `slack_context.md` if Step 4
   wrote one; `ce_context_*` files are umbrella-only and simply absent here (the guide reads
   "what's present"). It writes `<run_dir>/ce_health_insights.json` — a per-section
   `{insight, sentiment}` map; every data claim traces to the facts pack, enriched with the
   analyst's constraints/events via a `↗` tie-in.
3. **Final render embeds the insights.** Run the `--standalone` render from Step 3b **now**
   (after the insights file exists) so `_load_insights` embeds each one-liner as the
   section-top callout:
   ```bash
   python3 "$SKILL_DIR/../../scripts/render_ce_health.py" --run-dir "<run_dir>" --standalone
   ```
   **Graceful:** a failed/absent sub-agent → `ce_health_insights.json` missing → the render
   falls back to the deterministic §3/§9/§7 callouts (never blanks or breaks the tab), i.e.
   exactly today's standalone behaviour.

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
