---
name: ce-context
description: >
  CE Context for a Headout Combined Entity (CE) — the orientation layer of a CE
  RCA. Gathers everything we know about a CE *before* the metrics: the analyst's
  own context (focus, priors, known events, constraints, MMP-doc overview), the
  synthesised history of prior RCAs we've run on this CE, and live Slack standing
  context (CE mentions, supply/campaign/bug signals, known-issue probes). Owns the
  Slack collector for the whole CE-RCA run. Emits a "CE Context" tab fragment with
  a context timeline + the deterministic context tables. Run /ce-context <CE> for a
  standalone context report, or it is dispatched automatically by the /ce-rca
  umbrella right after the diagnosis pause.
---

# CE Context — orientation layer

This skill assembles the **context** for a CE — the three streams that orient an
RCA before any metric is read:

1. **User context** — the analyst's focus, hypothesis priors, known events,
   constraints, failure modes, important links, and an "About this CE" overview
   (often from an MMP doc). Captured at the `/ce-rca` Step-1 pause into
   `user_context.md`; on a standalone run, whatever the user provides.
2. **CE history** — a short synthesis of the prior RCAs we've already run on this
   CE (trajectory, recurring root causes, what was tried, what's still open).
3. **Slack standing context** — live Slack signals for this CE (CE mentions,
   supply / campaign / bug signals, and user-named channels + known-issue probes).

It **owns the Slack collector** for the entire CE-RCA run: under the umbrella it
fires Slack once, early, and CVR-RCA consumes the shared `slack_context.md` rather
than searching again (the `orchestration.json → slack_owner` handshake). The
output is `ce_context_report.html` — a visual-kit tab fragment (anchors
`cecontext-*`) with a **context timeline chart** on top and the deterministic
context tables below.

## Before you begin

Set `SKILL_DIR` to the absolute directory **this** SKILL.md was read from — every
`$SKILL_DIR/...` reference (the vendored guides, the renderer) depends on it.

```bash
SKILL_DIR="<absolute dir this SKILL.md was read from>"
```

The renderer lives at the **CE-RCA bundle** `scripts/render_ce_context.py`. When
dispatched by `/ce-rca`, that is `<ce-rca>/scripts/render_ce_context.py`; the
orchestrator passes its own scripts dir as `RENDER_SCRIPTS_DIR`. Standalone, the
renderer is optional (a standalone run may emit only `ce_context.md` if the
renderer isn't reachable — see Step E).

## Invocation

```
/ce-context <CE> [date-range]
```

`<CE>` is a CE id or name; `[date-range]` is optional (default last-30-vs-prior-30,
matching the suite). The CE-RCA umbrella does not type this — it dispatches this
skill as a sub-agent with everything pre-resolved (see "Orchestrated" below).

## Orchestrated vs standalone

- **Orchestrated (the umbrella case).** `CE_CONTEXT_RUN_DIR` is set in your prompt.
  Write **all** artifacts into that exact dir (no self-named folder). Read
  `<run_dir>/orchestration.json` for `user_slack_channels`, `slack_probes`, the
  `user_context` file path, and the run window; read CE identity/market/country and
  the windows from `<run_dir>/ce_health_report.json` + `<run_dir>/meta.json` (CE
  Health already ran). Do **not** re-resolve the CE or re-confirm the window.
- **Standalone (`/ce-context` directly).** `CE_CONTEXT_RUN_DIR` is unset. Resolve
  the CE with the **same `dim_combined_entities` lookup** the master uses
  (`headout-analytics.analytics_reporting.dim_combined_entities`, location EU;
  `combined_entity_id` is a STRING — quote it; by-id, or `LIKE` by-name). Default
  the window to last-30-vs-prior-30 unless the user named one. Self-name a run dir
  under `~/Documents/CE RCA Runs/` (`<ce-slug>-<post_start>-to-<post_end>`). There
  is no CE Health sidecar standalone, so **select the CE-metadata columns in that
  same dim lookup** and write them to **`<run_dir>/ce_context_meta.json`** so the
  standalone report header carries the full CE context (the Omni pill + the CE
  chips). Keys (omit any the dim row doesn't have):
  `combined_entity_name`, `combined_entity_type`, `market`, `country`,
  `combined_entity_category`, `combined_entity_subcategory`, `evolution_bucket`,
  `management_type`, `headout_status`, `top_page_url`, plus `ce_id`. The `--standalone`
  renderer reads this (preferring a CE Health sidecar's `metadata` when present) to
  build the header. Under the orchestrator this file is unnecessary — the header
  metadata comes from CE Health's sidecar.

**Everything degrades gracefully — never block.** A missing stream is skipped and
noted, never fatal (mirrors the suite's graceful-skip rule).

---

## Step 0 — Context intake (standalone only)

CE Context *is* the user-context layer, so on a standalone run it must **gather** the
analyst's context itself — there is no umbrella to write `user_context.md` first. Run
the **full onboarding questionnaire** per
**`$SKILL_DIR/../../references/context_intake_guide.md`** (emphasis: **full** — all four
buckets + the "anything else?" catch-all + aliases; **no 1e** — orientation, not
diagnosis), and write the answers into `<run_dir>/user_context.md` (the 8-slot contract).

**Standalone gate (run this step only when standalone):** skip Step 0 entirely if
`CE_CONTEXT_RUN_DIR` is set OR `<run_dir>/orchestration.json` exists OR
`<run_dir>/user_context.md` already exists — under the umbrella the orchestrator captured
context once at its Step 1 and you must not re-ask. Standalone (`/ce-context` directly),
run it.

Then **derive the Slack inputs for Step A from the answers**: `ce_aliases` from `##
Aliases`, and `slack_probes` from `## Constraints` + `## Known failure modes` (the same
mapping the umbrella does into `orchestration.json`). If `AskUserQuestion` or the guide is
unavailable, ask the same questions inline and record them the same way — never block.

---

## Step A — fire the Slack collector FIRST (fire-and-forget)

Spawn the Slack collector sub-agent **before** anything else, so `slack_context.md`
lands early — CVR-RCA reads it at its Step 2b, and you render it at Step E. Do
**not** wait for it. Its instruction file is `$SKILL_DIR/references/slack_context_guide.md`.
Pass:

```
ce_id, ce_name, market, country, pre_start, post_start, post_end
run_dir       → <run_dir>
output_path   → <run_dir>/slack_context.md
user_channels → orchestration.json `user_slack_channels` (orchestrated); else any channel named in the Step-0 intake (standalone); else omit
slack_probes  → orchestration.json `slack_probes` (orchestrated); else derived in Step 0 from `## Constraints` + `## Known failure modes` (standalone); else omit
ce_aliases    → orchestration.json `ce_aliases` (orchestrated); else `## Aliases` from Step 0 (standalone); else omit
```

**Graceful skip:** the collector self-guards on the Slack MCP (honesty rule in the
guide). If the MCP is absent it writes nothing; you simply render "Slack context
unavailable" at Step E. Never fabricate Slack content yourself.

---

## Step B — synthesise CE history (one row per prior RCA)

Follow `$SKILL_DIR/references/ce_history_guide.md` in your own context: find prior
RCA runs for this `ce_id` in `runs_root` (default `~/Documents/CE RCA Runs`,
excluding the current `run_dir`), read their **conclusions** (not raw analysis), and
write a **structured per-RCA digest** to `<run_dir>/ce_history.json` — one row per
prior run (most-recent-first): `window · pareto_finding · metric_impact · moved
(moved|didnt|partial|unknown) · why · report_link`. This answers, per past RCA:
*what did we find, what moved, did the fix land, and why*. If there are no prior
runs, write `{"ce_id": <id>, "rcas": []}` and move on (most first runs).

---

## Step C — read user context

Read the analyst's context from `<run_dir>/user_context.md`. **Orchestrated:** the path
named under `orchestration.json → user_context` (the umbrella wrote it at its Step 1).
**Standalone:** the file **Step 0 just wrote** from the intake questionnaire — read it the
same way. If a "Let Claude infer" / "Nothing to add" run left it empty (or absent), skip —
the tab just omits that block.

---

## Step D — synthesise Known Constraints (the bucketed Q&A)

This is the centerpiece of the CE Context tab. **Answer** a fixed checklist of
constraint questions from the evidence you now hold — `user_context.md` (Constraints
/ Known events / Known failure modes slots) **+** `slack_context.md` **+** the
`slack_probes` results. Emit `<run_dir>/ce_context_constraints.json`:

```json
{
  "buckets": [
    {"area": "Supply & availability", "status": "issue", "detail": "single-vendor; stockouts flagged May 2", "sources": [{"label": "Slack ↗", "href": "https://slack.../p..."}]},
    {"area": "PPC restrictions", "status": "none_known", "detail": "", "sources": []},
    {"area": "Notable price changes", "status": "issue", "detail": "raised prices Apr 8", "sources": [{"label": "user context", "href": "#"}]},
    {"area": "Landing-page (LP) constraints", "status": "unknown", "detail": "", "sources": []},
    {"area": "Vendor / selling-partner (SP) constraints", "status": "none_known", "detail": "", "sources": []}
  ]
}
```

Rules:
- **The five named buckets are a guaranteed minimum** — always emit all five
  (Supply & availability · PPC restrictions · Notable price changes · Landing-page
  (LP) constraints · Vendor / selling-partner (SP) constraints), even when nothing
  is found. They are the questions a stakeholder always wants checked.
- **`status` ∈ {`issue`, `none_known`, `unknown`}.** `issue` = a real constraint is
  present (give `detail` + `sources`); `none_known` = checked, nothing found;
  `unknown` = not investigable from the evidence available. Be honest — **never
  fabricate** an issue, and don't mark `none_known` for something you couldn't check
  (use `unknown`).
- **Append extra buckets** for any *other* constraint area the evidence surfaces —
  content/catalogue, tech/API, seasonality, budget, etc. Same shape; the list is not
  limited to the five. Name the bucket yourself.
- **Cite sources** — Slack permalinks for Slack-sourced answers, `"user context"`
  for analyst-provided ones. `detail` is one tight line.

---

## Step E — emit the context timeline JSON

Emit `<run_dir>/ce_context_timeline.json` — a **normalised, dated** event list the
renderer plots as a timeline. You are the right place to do this because only you
have read all the prose streams and can resolve dates (including relative ones like
"last week", using the run window).

```json
{
  "ce_id": 243,
  "ce_name": "Eiffel Tower",
  "window": {"pre_start": "YYYY-MM-DD", "pre_end": "YYYY-MM-DD",
             "post_start": "YYYY-MM-DD", "post_end": "YYYY-MM-DD"},
  "events": [
    {"date": "2026-04-08", "label": "Raised prices", "lane": "known_event", "link": null},
    {"date": "2026-05-02", "label": "Vendor API errors flagged", "lane": "slack", "link": "https://slack.../p..."},
    {"date_range": ["2026-03-01", "2026-03-31"], "label": "Prior RCA: CVR slid 4.1%→3.8%", "lane": "prior_rca", "link": null},
    {"date": "2026-04-15", "label": "MMP: assortment cap added", "lane": "mmp", "link": null}
  ]
}
```

Lanes (the timeline's rows): `prior_rca` (prior-run windows — read the dated folder
names / each run's `ce_health_report.json`), `slack` (dated lines in
`slack_context.md`), `known_event` (user-context "Known events", dates normalised),
`mmp` (dated callouts from the MMP-doc-derived "About this CE" / priors). Rules:

- **Only include events with a resolvable date.** Undated context ("usually breaks
  on inventory") stays in the tables — it gets no timeline marker.
- **Best-effort, never blocking.** If you cannot date anything, write
  `{"window": {...}, "events": []}` — the renderer omits the chart and shows tables
  only. Never invent dates to fill the timeline.
- Keep `label` short (≤ ~7 words). Include `link` when the source carries one
  (Slack permalinks), else `null`.

---

## Step F — render the tab fragment

Render the deterministic tab body. The renderer reads the three JSON artifacts
(`ce_history.json`, `ce_context_constraints.json`, `ce_context_timeline.json`) + the
`user_context.md` slots + `slack_context.md`, and emits the 7 sections in order:

```bash
python3 "<RENDER_SCRIPTS_DIR or $SKILL_DIR/../../scripts>/render_ce_context.py" --run-dir "<run_dir>"
```

This writes `<run_dir>/ce_context_report.html` with anchors `cecontext-about`,
`cecontext-timeline`, `cecontext-pastrca`, `cecontext-constraints`,
`cecontext-failuremodes`, `cecontext-links`, `cecontext-slack`. **A render failure is
non-fatal** — log it and continue; the composite simply won't carry a CE Context
tab. Standalone, if the renderer isn't reachable, leave the JSON + stream files on
disk and say so.

**Standalone runs — add `--standalone` to get an openable report.** Under the
orchestrator (`CE_CONTEXT_RUN_DIR` set) run the command above as-is — it emits the
**fragment** that `compose.py` embeds as the CE Context tab. When run **standalone**
(`/ce-context` directly), add the flag:

```bash
python3 "$SKILL_DIR/../../scripts/render_ce_context.py" --run-dir "<run_dir>" --standalone
```

`--standalone` ALSO wraps the fragment into a full, browser-openable
**`<run_dir>/report.html`** (the shared `standalone_report.wrap_fragment` adds the
`<html>` shell + Plotly CDN + visual-kit CSS + a lightweight CE banner). Tell the
user the report opens at `<run_dir>/report.html`. The default (no-flag) fragment is
still written, so the orchestrated path is unchanged.

---

## Return to the caller

Return **one line** summarising what landed, e.g.:

```
CE Context: about ✓ · timeline 6 events · 3 past RCAs · constraints 6 buckets (2 issues) · Slack ✓ → ce_context_report.html
```

or, with skips:

```
CE Context: no user context · timeline 0 events · no prior RCAs · constraints 5 buckets (none known) · Slack unavailable → ce_context_report.html
```

## Hard rules
- **Own Slack once.** Fire the collector exactly once (Step A). Under the umbrella,
  CVR-RCA skips its own spawn (it sees `slack_owner: "ce-context"`); you must
  therefore always fire it so the shared file exists.
- **No analysis.** This skill orients — it gathers and presents context. It never
  computes metrics, runs funnel queries, or draws RCA conclusions.
- **Graceful everywhere.** Every stream is independently skippable; a skip is noted,
  never fatal. Honesty rule on Slack: absent → "unavailable", never fabricated.
