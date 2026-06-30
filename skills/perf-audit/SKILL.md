---
name: perf-audit-v6
description: Deep paid performance audit for a CE — zoom-out-first channel overview, campaign cohort backbone, 3 temporal windows, search intelligence, and sized actions
# No allowed-tools pin: Slack/Ahrefs (and any MCP) server ids are environment-specific
# and differ per user, so a hard-coded id would silently block those tools on most
# installs. This skill inherits the session's tool permissions; Slack/Ahrefs tools are
# discovered dynamically at run time.
---

# Paid Performance Audit (v6.1)

Comprehensive paid-channel diagnostic for a CE. Python renders all BQ tables (including landing pages, keyword IS, campaign targeting). Claude writes narrative only.

**Audience:** Growth analyst + GM + Perf team
**Scope:** All paid channels. Non-paid issues detected and routed to `/ce-audit`.

## Stay on the latest version — do this first

Perf-Audit ships **inside the CE-RCA bundle** and is never updated on its own — running it
refreshes the **whole** bundle from the `ce-rca-skill` repo. Set `SKILL_DIR` to the directory
this SKILL.md was read from, then run the shared guard (two levels up). It self-guards: only
the canonical `~/.ce-rca` install is ever rewritten; a dev checkout or an umbrella-dispatched
run is a no-op.

```bash
SKILL_DIR="<absolute dir this SKILL.md was read from>"   # e.g. ~/.ce-rca/skills/perf-audit
bash "$SKILL_DIR/../../scripts/update_guard.sh" "<run_dir if you were dispatched by /ce-rca, else omit>"
```

- **`UPDATED <old> <new>`** — bundle refreshed in place (run folders untouched). Tell the user
  one line ("CE-RCA updated v`<old>` → v`<new>`") and **re-read `~/.ce-rca/skills/perf-audit/SKILL.md`**,
  continuing from the top.
- **`CURRENT` / `OFFLINE` / `SKIPPED …`** — proceed on the installed version (3-second timeout,
  never blocks).

## When to Use

- CE shows paid revenue decline or stagnation
- Weekly review flags a "Losing Ground" CE
- Before adjusting bids/budgets/targeting for a CE
- GM asks "what's going on with paid for X?"

## Usage

```bash
/perf-audit-v6 "Louvre Museum"
/perf-audit-v6 "Edge NYC"
/perf-audit-v6 "London Eye"
```

---

## Report Structure

```
1. Executive Summary (status + causal story + $ impact — written LAST, appears first)
2. CE Overview (Table 1 — rendered by code)
3. Channel Breakdown (revenue metrics — rendered by code)
4. Paid Deep Dive (Paid Value Shapley + Table 2 Search+PMax+Bing + Landing Pages + Product Mix/TGID + Campaign×Product *narrative* — tables rendered by code; campaign×product is narrative-only, full matrix in a backend comment)
5. Coverage + Matchmaking (cohort table, budget table, geo table — rendered by code)
6. External Dynamics (demand, competition, money on table)
7. Funnel (standalone paid-session BQ funnel — LP2S / S2C / C2O; deep decomposition deferred to the CE-RCA CVR-RCA tab)
8. Search Intelligence (Ad Group Coverage + Ad Group Audit/bid-headroom + CSV cluster analysis if uploaded)
9. Red Flags Summary
10. Conclusions (forwardable: lever + $ size + owner + constraint; not bid-prescriptive)
A. Evidence Appendix (A1-A3 monthly trends, A6 budget detail, A7 targeting — rendered by code)
B. Data Sources
```

---

## Execution Modes

### Mode 1: Full Engine (recommended)

Uses the Python engine (`perf_audit.py render`) to fetch BQ data and render the table skeleton — including the Section 9 coverage-gate "Signals to Close" table. Claude fills narratives and dispositions only.

### Mode 2: SQL-Only (no Python engine)

Claude reads `references/sql-reference.md`, runs queries inline via the BQ CLI, and builds the report (including the Section 9 gate table) manually. Use this when the Python engine isn't installed.

### Standalone HTML report (when run on its own, not under `/ce-rca`)

After the report markdown (`perf_audit_report.md`) is finalized (narratives filled, §B appended), produce a **browser-openable HTML report** with the CE-RCA bundle's beautifier + `--standalone`:

```bash
python3 <ce-rca-bundle>/scripts/render_perf_audit.py --run-dir <run_dir> --standalone
```

This writes **`<run_dir>/report.html`** — the same beautified Paid-Performance tab (verdict banner + styled tables + grey prose), wrapped by the shared `standalone_report` helper into a full document (Plotly CDN + visual-kit CSS + a lightweight title banner). **Graceful:** if the bundle renderer isn't reachable, the markdown remains the deliverable. **Under `/ce-rca` this is unnecessary** — the master runs the renderer without `--standalone` and `compose.py` builds the composite tab.

---

## Execution Steps

### Step 0 — Prompt for optional uploads (non-blocking)

Send this prompt before Step 1. Don't wait for response.

> **While I start pulling data, these optional inputs strengthen the analysis:**
>
> **Auction Insights CSVs** (adds competitor names + outranking share to Section 6b):
> 1. Google Ads → current account → select all `<CE Name>` campaigns → **Auction insights** tab → segment by **Week** → date range: **last 8 weeks** → **Download** → CSV
> 2. **Switch to the pre-consolidation account** → same CE campaigns → Auction insights → segment by **Week** → **same 8 weeks last year** → Download → CSV
>
> **Finding the LY account:** Query BQ:
> `SELECT DISTINCT customer_id, account_name FROM google_ads_campaign_stats WHERE campaign_target_combined_entity_id = '<CE_ID>' AND report_date < '2026-02-01' LIMIT 1`
>
> **Search Terms CSV** (adds cluster analysis to Section 8):
> Google Ads → Search terms report → filter to `<CE Name>` campaigns → last 4 weeks → Download CSV.
> If not available, Section 8 will use keyword IS data only.
>
> **Identifying CSVs:** File names are auto-numbered ("Auction insights report (12).csv") and meaningless. Read line 2 of each CSV — it contains the date range (e.g., "March 23, 2026 - April 19, 2026"). Match against L4W/P4W/LY date windows to identify CY vs LY.
>
> Share file paths anytime during the audit.

**Under an orchestrator (CE-RCA):** do **not** send this prompt. The orchestrator
collects the Auction Insights / Search Terms CSVs up-front at its own input pause and
hands you their paths (saved under `<run_dir>/uploads/`), or the literal `none` if the
analyst skipped. Skip the interactive prompt entirely and **consume the provided
files** for §6b / §8, degrading gracefully if `none` (§6b → no competitor table, §8 →
keyword-IS only). Identifying CY-vs-LY is unchanged (read line 2's date range).
Standalone behavior is unchanged — send the prompt as above.

### Step 0b — Context intake (standalone only)

Standalone, also gather the analyst's context — it is what makes Step 5b reconciliation and
the "constraints filter the recommended actions" rule (Step 3) actually fire. Today, with no
umbrella, no `user_context.md` exists so Step 5b is a clean no-op. Run the onboarding
questionnaire per **`$SKILL_DIR/../../references/context_intake_guide.md`**, emphasis
**perf-audit** (lead the **PPC / Paid · budget · campaign** buckets — the off-the-table
levers and changes the paid audit consumes; still ask all four), and write the answers to
`<run_dir>/user_context.md` (the 8-slot contract).

- **Standalone gate (run Step 0b only when standalone):** skip entirely if
  `<run_dir>/orchestration.json` exists OR `CE_CONTEXT_RUN_DIR` is set OR
  `<run_dir>/user_context.md` already exists — under `/ce-rca` the orchestrator captured
  context once and you must not re-ask.
- **Two halves, and the no-steer guardrail:** ask the **factual buckets (1a–1d) up front**
  (recall, before the numbers) while the engine renders in Step 2; **defer the grounded
  hypothesis (1e) until after Step 2's tables are rendered** (the reveal), appending it to
  `## Hypothesis priors`. As always in perf-audit, user context **never steers the Section
  2–7 data narrative** — constraints only *filter the actions* (Step 3 / Section 10) and
  priors are *reconciled* at Step 5b. A "nothing to add" run leaves the slots empty and the
  report is identical to today's bare run.

### BQ Quick Reference

When writing ad-hoc BQ queries for this audit, use these column names (NOT guessed names):

| Table | Key columns |
|-------|------------|
| `fct_orders` | `DATE(created_at)` for date filter, `combined_entity_id` (STRING — use quotes: `= '252'`), `channel_name`, `channel_grouping`, `campaign_name`, `amount_revenue_usd` (net revenue, NOT `order_value_completed_usd`). No `order_status` filter needed. |
| `google_ads_campaign_stats` | `report_date`, `sum_spend`, `count_clicks`, `count_impressions`, `campaign_target_combined_entity_id` (STRING), `campaign_name`, `campaign_status`, `current_campaign_budget`, `current_campaign_target_roas` |
| `google_ads_campaign_budget_stats` | `report_date`, `campaign_id`, `daily_budget` |
| `mixpanel_user_page_funnel_progression` | `event_date`, `combined_entity_id` (STRING), `page_url`, `user_id`, `has_select_page_viewed`, `has_checkout_started`, `has_order_completed` |

### Step 1 — Resolve CE + compute dates

Resolve the CE name to an ID:
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

Compute date windows (L4W = last 4 complete Mon-Sun weeks):
```bash
cd ~/analytics && python3 -c "
from datetime import date, timedelta
today = date.today()
end = today - timedelta(days=today.weekday() + 1)  # last Sunday
start = end - timedelta(days=27)  # 4 weeks back
ly_end = end - timedelta(days=364)
ly_start = start - timedelta(days=364)
p4w_end = start - timedelta(days=1)
p4w_start = p4w_end - timedelta(days=27)
print(f'L4W: {start} to {end}')
print(f'P4W: {p4w_start} to {p4w_end}')
print(f'LY:  {ly_start} to {ly_end}')
"
```

### Step 2 — Run renderer (produces skeleton with all BQ tables)

**Mode 1 (Full Engine):**
```bash
SKILL_DIR="$(dirname "$(readlink -f SKILL.md)")"
python3 "$SKILL_DIR/perf_audit.py" render \
  --ce-id <CE_ID> --ce-name "<CE Name>" --market "<Market>" \
  --lp-url "<LP_URL>" \
  --l4w-start <L4W_START> --l4w-end <L4W_END> \
  --p4w-start <P4W_START> --p4w-end <P4W_END> \
  --ly-start <LY_START> --ly-end <LY_END> \
  --output perf-audit-<slug>-<date>-v6.md
```

**Mode 2 (SQL-Only):** Read `references/sql-reference.md`. Run each query for the 3 windows (L4W, P4W, LY) and build the tables — including the Section 9 gate — manually.

**LP URL:** Omit `--lp-url` on first run. After the skeleton renders, the Landing Pages table (Section 4) shows the top LP by clicks — use that URL. Backfill the header manually if needed. The LP URL is NOT in `dim_combined_entities` — it varies by CE (e.g., `pompeii-tickets.com/` not `headout.com/pompeii-tickets/`).

This fetches all BQ data and outputs a markdown skeleton with pre-formatted tables and `<!-- ... -->` markers. All tables (CE overview, channels, Google Search, cohorts, budget with portfolio type, geo, landing pages, money-on-table, campaign targeting, appendix) are rendered by code.

### Step 3 — Read skeleton + DIAGNOSTICS.md, fill narratives

Read the skeleton file. All tables are pre-formatted — do NOT reformat them. Read `DIAGNOSTICS.md` for hypothesis trees. Walk the trees against the data.

Replace every `<!-- ... -->` marker with analysis following the narrative rules below.

**Section ordering with reading instructions:**

**1. Section 2 (CE Overview) — read Table 1:**
- Read Revenue row: L4W vs LY (direction + magnitude). MoM direction (recovering or declining?).
- Read ROI(1): improved or compressed? If ROI improved but revenue dropped → volume problem, not efficiency.
- Read Orders: if orders dropped more than revenue → AOV rose (fewer, more valuable customers).
- Connect: "The question for the next section is whether this is demand, paid, or non-paid driven."

**2. Section 3 (Channel Breakdown) — read Channel table:**
- Sort by Δ LY column. Which channels lost the most revenue in absolute $?
- Sum the top 3 losers — do they explain the total CE decline from Section 2?
- Check paid vs non-paid split: if non-paid channels (Organic, Direct) lost more than paid → the issue is broader than ads.
- Note any channel with >50% YoY growth (emerging channel signal).

**3. Section 4 (Paid Deep Dive) — read Paid Value Shapley FIRST, then Table 2 + LP tables + Product Mix:**
- **Paid Value Decomposition (Shapley) — read this before anything else in Section 4.** The engine has already computed how much of the paid CM1 change each driver owns (Clicks × CVR × Avg CM1, $ and % of Δ), for both MoM and YoY. **This is your verdict on driver ordering — do not re-derive it from the tables.** Lead the Section 4 narrative (and the Executive Summary) with the driver that has the largest |contribution|. If clicks own 90%+ of the Δ, the headline is volume — never bury it under a small CVR move. If Avg CM1 leads, the value-per-conversion moved (take rate / product mix) → go straight to the TR/CR tree and the Product Mix table. The Shapley settles "which driver"; the rest of Section 4 explains "why."
- Read CPC column: L4W vs LY. But do NOT conclude on blended CPC alone — note it and defer to Section 5 per-language analysis.
- Read CVR: if CVR declined alongside CPC flat/up → not quality traffic improvement. (But weight it by the Shapley — a CVR move with small Shapley share is not the story.)
- Read Clicks: magnitude of YoY loss. If >30% → significant volume problem.
- Check LY CM1 vs LY Paid Rev: if CM1 > Rev, flag as data anomaly with footnote.
- LP Ad Performance table: compare CTR across language LPs. Language LPs with 2x+ CTR vs generic → validates dedicated LP strategy.
- LP On-Site Funnel table: read LP2S and S2C columns. Which stage has the largest YoY delta? If S2C is dominant leak (>5pp) across multiple pages → product-level issue, not page-specific.
- **Product Mix (TGID) table:** read the Δ Share column. Flag any experience with |Δ Share| > 5pp. A new hero (🆕) or a decayed/dropped (⚠️ / share → ~0) product means revenue, CVR, and RPC moved because the **assortment changed**, not because the funnel or traffic quality changed. Cross-check with the Shapley: if a low-AOV / low-TR product gained share, that *mechanically* drags blended Avg CM1 — which is then the Shapley's Avg CM1 driver. Name the products. Route lost heroes to Supply, new low-economics products to Product/pricing.
- **Campaign × Product (paid) — narrative only, no table in the report.** The full join renders into a *backend comment*; you read that comment and write 2-3 sentences of insight, you do NOT reproduce the table. It answers *which campaign sells which product at what margin*. Read it for mismatches: a high-spend/high-volume campaign concentrated in a **low-TR product** (e.g. dining TGIDs at TR ~10% vs ticket TGIDs at ~24%) drags blended economics and is usually the concrete source of the Avg CM1 Shapley driver and the TR decline. Also flag a hero product spread thin across many small campaigns (dedicated-campaign opportunity). ROI can't split by product (spend is campaign-level), so judge per-product economics on **TR and CM1/Ord**, not ROI. Name campaign + product + margin; route low-margin concentrations to Product/pricing, mis-targeted spend to Perf. Full matrix is in the backend comment.

**4. Section 5 (Coverage) — read Cohort table:**
- **First: Language CPC × Scale scan.** For each cohort with >$1K spend, read CPC (L4W vs LY) and Clicks (L4W vs LY). Classify each: CPC↑+Scale↓ = competition, CPC↑+Scale↑ = healthy, CPC flat+Scale↓ = SIS compression. Write the scan table.
- Then: Top 3 by CM1 share. For each, what drove RPC change: CVR vs AOV vs TR?
- Read SIS and Rank Lost columns: if rank-lost > 60% with budget-lost < 5% → tROAS is the constraint. Compute recommendation using formula (actual ROI × 0.9, floor 130%).
- Read Budget Summary: Individual vs Portfolio aggregates. Are portfolio campaigns underperforming or expected long-tail?
- Read Geo table: largest gap between Click Share and Customer Share → under-served feeder markets.

**5. Section 6 (External Dynamics):**
- 6a: Run Ahrefs for 3-5 CE keywords across top markets. If demand growing but clicks falling → capture problem (confirms Section 5 competition scan).
- 6b: Connect Section 5 language scan to competition analysis. The per-language CPC × scale patterns ARE the competition evidence. Then apply 3-lens tree (see DIAGNOSTICS.md §4). If auction insights CSV available, parse and build Δ of Δ table.
- 6c: Read Money on Table (pre-rendered). Top 3 cohorts by opportunity — note which are rank-constrained vs budget-constrained.

**6. Section 7 (Funnel) — standalone paid-session funnel:**
- See Step 4 below. The perf audit forms the funnel hypothesis from its *own* paid-session funnel data (Section 7) and sizes the leak, but **defers the deep funnel decomposition (device / experience / C2O sub-stages / LY gap) to the CE-RCA CVR-RCA tab** — do NOT invoke a separate `/cvr-rca` funnel investigation from the perf audit. Note the hypothesis and the verdict (`defer to CVR-RCA`).

**7. Section 8 (Search Intelligence):**
- Read Ad Group Coverage table (pre-rendered). Which AG types have most clicks? Language gaps?
- **Ad Group Audit table (pre-rendered):** the ad-group-level detail under the type rollup. Opportunity is **bid headroom vs each ad group's tROAS target** (there's no impression-share at ad-group grain). Lead with the flags: name the **Scale** ad groups (ROI ≥ target ×1.15 at material spend → algorithm under-bidding a profitable group; Perf can raise budget / lower tROAS, you name the lever not the number) and the **Leak** ad groups (ROI <130% at material spend → state the $ at risk, route to LP/quality/match-type or trim). **Cross-check Leaks against §4 Campaign × Product** — a broad below-target pattern is usually the systemic TR/RPC constraint (same root as the rest of the audit), not N independent ad-group problems; a single low-TR product can explain a low-ROI ad group (Product call, not paid). Ad group × product (experience_id) is unavailable (no `ad_group_id` on `fct_orders`) — Type is the intent proxy.
- If CSV uploaded: cluster, build cross-reference, flag wasted spend.

**8. Section 9 (Red Flags) — consolidate from all sections:**
- Re-read your narratives from Sections 2-8. Extract every issue flagged. Rank by severity (HIGH = revenue impact + worsening, MEDIUM = notable but stable, LOW = monitor).

**9. Section 10 (Conclusions):**
- One forwardable conclusion per CONFIRMED HIGH signal minimum. Each row: lever + sized opportunity ($/L4W) + owner + constraint. State the math; name the lever but don't prescribe the bid magnitude (see Section 10 rules).

**10. Section 1 (Executive Summary) — write LAST:**
- Re-read Sections 2-10. Lead with the language-level story (which languages are competing, which are growing). State tROAS recommendations with formula. Connect funnel findings. Reference competition if auction data available.

### Step 4 — Funnel query (standalone BQ, not in renderer)

The perf audit owns a **standalone paid-session funnel** — it does NOT invoke `/cvr-rca`. The deep funnel decomposition (device / experience / C2O sub-stages / LY gap) belongs to CE-RCA's own CVR-RCA tab; the perf audit only forms and sizes the funnel hypothesis from paid-session data here.

Run this query for L4W, P4W, and LY, then render the funnel table in Section 7:

```sql
SELECT COUNT(*) as lp, COUNTIF(has_select_page_viewed = TRUE) as s,
  COUNTIF(has_checkout_started = TRUE) as c, COUNTIF(has_order_completed = TRUE) as o
FROM `headout-analytics.analytics_reporting.mixpanel_user_funnel_progression`
WHERE combined_entity_id = '<CE_ID>'
  AND session_date BETWEEN '<START>' AND '<END>'
  AND (acqusition_source LIKE '1 - %' OR acqusition_source LIKE '2 - %')
```

Validate direction: compare the paid-session CVR delta (o/lp, L4W vs LY) against the cohort table TOTAL CVR delta (Section 5) — direction must agree. Then write the Section 7 narrative (see Section 7 rules below), forming the funnel hypothesis and recording `defer to CVR-RCA` for the deep decomposition.

### Step 4b — Create Google Sheet (8 tabs) — full data dump

Produce a Google Sheet with the full backing data — the report shows the top rows of each table; this is the complete dump for the analyst to slice. Surface the link in the report (Section B), not chat.

**Sheet creation — try in order, stop at first success:**

1. **`gws` CLI** (preferred): `gws sheets spreadsheets create ...` then `gws sheets spreadsheets values update ...` for each tab.
2. **Sheets API via gcloud token**: Use `gcloud auth print-access-token` + `urllib` to call Sheets API v4 directly. Requires Sheets API scope on the project.
3. **MCP Google Drive**: `create_file` (Google Drive MCP) with `contentMimeType: text/csv` and `base64Content` — creates one Google Sheet per CSV (auto-converts). Upload all 8 tabs as separate sheets.
4. **Local fallback**: Save CSVs to `.cache/perf-audits/<slug>-<date>/` and note paths in Section B for manual import.

Always save CSVs to `.cache/perf-audits/<slug>-<date>/` regardless of which upload method succeeds — they're the durable backup.

**Tab definitions:**
- **Tab 1 (Search Term Clusters)**: Cluster aggregates — Clicks, Spend, Conv, CVR, CPC, RPC, Spend Share. Empty with note if no Search Terms CSV.
- **Tab 2 (Keywords)**: Top 50 keywords by spend — cluster tag, campaign, match type, clicks, spend, CVR, ROI.
- **Tab 3 (Keyword Universe)**: Ahrefs volume data — keyword, monthly volume, trend, competition. Note gap if Ahrefs unavailable.
- **Tab 4 (Auction Insights)**: CY L4W + P4W weekly competitor data from CSV. Empty if no Auction Insights CSV.
- **Tab 5 (Campaign Detail)**: Primary source is `fct_orders` grouped by channel × campaign for ALL rows — includes non-paid channels, cross-CE attributed campaigns, and LY-only campaigns ($0 L4W). **For the Channel column, use the custom channel CASE statement from the engine** — it lives in `engine/sources/bq.py` (the `_fetch_channel_window_v2` channel taxonomy CASE: maps `channel_name` + `campaign_name` patterns into detailed channels — Google Search, Google PMax, Bing, Google Cross-sell, etc.). Do NOT use raw `channel_grouping` (gives only broad 'Paid'/'Organic'). Base columns: Channel, Campaign (or "(no campaign)" for non-paid), L4W Rev, L4W Ord, L4W AOV, P4W Rev, P4W Ord, LY Rev, LY Ord, Δ LY ($), Δ LY (%), Δ P4W ($), Δ P4W (%), L4W Share. Then LEFT JOIN `google_ads_campaign_stats` on campaign name to enrich paid rows with: L4W Spend, L4W ROI, Status (Active/Paused), Type (Individual/Portfolio). Non-paid and unmatched rows show "—" for enriched columns. Do NOT filter or drop any fct_orders rows — cross-CE campaigns are expected. Sorted by L4W Rev DESC.
- **Tab 6 (Landing Page Funnel)**: Full LP breakdown from `mixpanel_user_page_funnel_progression` using `COUNT(DISTINCT user_id)`. Columns: Page URL, L4W Users, L4W CVR, L4W LP2S, L4W S2C, L4W C2O, LY Users, LY LP2S, LY S2C, LY C2O, Δ LP2S, Δ S2C, Δ C2O. Top 7-8 by users in report (Section 4), full dump here. Note: Mixpanel collapses language variants (/it/, /de/, /fr/) into root URL. Do NOT use `mixpanel_user_funnel_progression` (session-level, inflated rates) or `COUNT(*)`.
- **Tab 7 (Campaign × Product)**: Full paid (campaign × product) matrix — the report shows the top 15, this is every pair. The engine already computes it: `from engine.sources.bq import fetch_campaign_product_mix; fetch_campaign_product_mix(<CE_ID>, <L4W_START>, <L4W_END>)["all"]`. Columns: Campaign, Channel, TGID, Experience, Orders, Net Rev, Share %, AOV, TR %, CM1, CM1/Ord. Paid scope only (Google/Bing campaign-attributed orders, same channel CASE as Tab 5). Sorted by Net Rev DESC. ROI is intentionally absent — spend is campaign-level, so per-product margin is read via TR / CM1/Ord, not ROI.
- **Tab 8 (Ad Group Audit)**: Full ad-group set — the §8 report table shows the top 15, this is all of them with MoM as its own columns. Engine computes it: `from engine.sources.bq import fetch_ad_group_audit; fetch_ad_group_audit(<CE_ID>, <L4W_START>, <L4W_END>, <P4W_START>, <P4W_END>, top_n=999)["all"]`. Columns: Ad Group, Type, Language, Status, Impressions, Clicks, Spend, Conversions, CM1, CPC, CVR %, CTR %, ROI %, tROAS %, vs Target pp, Δ Spend MoM %, Δ ROI MoM pp, Flag (Scale/Leak/On-target/Long-tail). Sorted by Spend DESC.

If any engine fetch function used above is unavailable (import fails), that tab degrades with a "data unavailable" note rather than failing the whole step. (Both `fetch_campaign_product_mix` and `fetch_ad_group_audit` are present in this bundle's `engine/sources/bq.py`.)

**After creating, append to Section B (Data Sources) of the report.** `render_data_sources()` renders §B as a static table in the engine skeleton; **append the link block to the §B section of the rendered report file (the `--output` `perf_audit_report.md`)** — directly below the §B table — after the Sheet is created:
```
**📊 Full data dump:** [Perf Audit — <CE Name> (<date>) ↗](<sheet_url>)
- Tab 1: Search Term Clusters
- Tab 2: Top 50 Keywords
- Tab 3: Keyword Universe
- Tab 4: Auction Insights
- Tab 5: Campaign Detail
- Tab 6: Landing Page Funnel
- Tab 7: Campaign × Product
- Tab 8: Ad Group Audit
```
This renders in the composite's Paid-Performance tab. **Graceful:** if no Sheets/Drive access and the local-CSV fallback was used, list the local `.cache/...` paths in §B instead of a link — never block the run.

### Step 5 — Self-eval

Read `EVAL.md`. Run quick checks, score the report.

### Step 5b — Context reconciliation (conditional, additive — feeds the Section 9 gate)

Your paid-side picture is complete (Sections 2–8 narrated, the funnel hypothesis formed,
the self-eval run). **Before** the Section 9 coverage gate disposes its signals and Step 6
wraps them in the transcript, reconcile that completed picture against whatever **context
lenses** the run directory carries. This is the perf-audit analogue of CVR-RCA's Step 2b —
same four-pattern logic, perf's own language — and it is **purely additive**: it changes
*how a gate signal closes* (and the citation it carries), never how the paid audit was run.

**The hard rule — reconcile only here, never earlier.** The paid audit forms its own
hypotheses and reaches its own dispositions from paid data first; the lenses then
corroborate or surprise a *completed* picture. A lens never steers a Section 4/5/6/7
narrative or the funnel hypothesis. (User context is the one early-read exception, below.)

**Read whichever lenses are present in the run directory — and ONLY these three:**

- **`ce_health_report.md`** — the **widest / upstream** lens. The CE-RCA umbrella ran CE
  Health first; it decomposed the CE's revenue move via Shapley across Traffic / CVR / AOV /
  Completion / Take Rate and carries CE-level facts the paid audit doesn't see (per-channel
  revenue, per-TGID RPC, L12M trajectory). Always present under the umbrella.
- **`user_context.md`** — the analyst's **intent**: Focus, Hypothesis priors, Known events,
  and any **constraints** (levers that are off the table). Present only when the umbrella (or
  a standalone caller) captured it.
- **`slack_context.md`** — **operational colour** (deploys, assortment/cap changes, pricing
  levers, supplier moves) collected by the orchestrator's Slack sub-agent. Present only when
  it ran.

**Do NOT read CVR-RCA's `findings.md`, `transcript.md`, or `perf_audit`-peer output.** The
Perf↔CVR weave is the **Summary's** job, not perf-audit's — perf-audit reads *upstream*
lenses (CE Health, user context, Slack), never its *peer*. Reading the peer would make the
two tabs circular; the neutral Summary synthesiser owns that cross-reference. (This is also
why perf-audit still never invokes `/cvr-rca` — the standalone funnel and `defer to CVR-RCA`
verdict are unchanged.)

**Reconcile widest-first, then together.** Read the lens that can most change your
interpretation first — **CE Health (widest, upstream — can reframe the whole paid finding)
→ Slack (operational colour)**, with user context closed alongside (it was already read at
Step 0/Step 1 as intent). A reframe from the widest lens should land *before* you would have
let the paid finding stand as the headline. Then reconcile the lenses together: a signal two
lenses agree on is stronger (raise confidence, no new query); a gap two lenses both flag is a
priority check (still one bounded query max).

**The four-pattern model, in perf's language — apply per signal:**

- **A — Corroborate.** A lens names the **same campaign, date, segment, TGID, or stage** as a
  signal the audit already reached. Close that Section 9 gate signal **CONFIRMED** and carry
  the cross-citation on its disposition. Example: the cohort scan flagged a CPC↑+Scale↓
  competition signal on the German cohort and CE Health shows that cohort's RPC fell on the
  same TGID — that is corroboration from a different altitude. Cite it
  `(CE Health: DE-cohort RPC −X% ↗)` on the gate row and in the Section 9 / Executive Summary
  subtext.
- **B — Mechanism.** A lens explains the **why** the paid data lacked. The audit timed *that*
  the paid CVR or clicks moved; a lens names the cause (a deploy, an assortment cap change, a
  pricing lever, a supplier API migration, a TGID launch/removal). Weave the mechanism into
  the relevant narrative subtext and carry it onto the gate disposition. No second query
  needed — the paid signal already exists; the lens supplies its cause.
- **C — Reframe.** **CE Health's Shapley names a non-paid headline driver** of the CE's
  revenue move — AOV, Completion Rate, or Take Rate (factors the paid audit doesn't own). The
  paid finding is **real but not the headline**: say so explicitly in the Executive Summary
  and the relevant gate disposition, and **point the reader to the CE Health tab** for the
  dominant driver (`see CE Health: [driver] ↗`). This keeps a correct-but-secondary paid
  finding from being mis-presented as *the* reason CE revenue moved. (If CE Health's Shapley
  says paid/CVR drove the move, the paid audit *is* the headline — proceed at full confidence.)
- **D — Testable gap.** A lens names a date, mechanism, segment, or TGID the audit didn't
  cover. Pursue only if it passes three filters: (a) specific (a date / mechanism / TGID, not
  "things are slow"); (b) within the audit windows or causally upstream; (c) about this CE or
  its market category. If it passes, run **one bounded check** against the paid data (a cohort,
  campaign, or paid-session funnel cut), then dispose the gate signal CONFIRMED / RULED OUT.
  If it can't be checked from the paid data, close it **DATA GAP** with the lens cited as the
  prompt. Maximum one query per gap signal.
- **Reject.** The signal only restates the symptom ("paid revenue is down", "CVR fell") or
  fails the Pattern D filters. One line in the transcript — `Lens signal '[summary]' — not
  pursued: [reason in ~5 words]` — and nothing in the report.

**This feeds the v6.2 coverage gate — it is not a parallel mechanism.** The reconciliation
evidence is exactly **what disposes each Section 9 "Signals to Close" row** (CONFIRMED /
RULED-OUT / DATA-GAP) and the citation that row carries. Do not create a separate
reconciliation table, a new section, or a new output file. The Section 9 gate
(filename/location/format unchanged) is the formal record; the **Step 6 gate-driven
transcript** then reflects the lens evidence on each disposed signal, because it mirrors the
gate row-for-row. Nothing else in the report structure changes.

**User-context handling (the dual-consumption + proportional rule):**

- **Constraints filter / annotate recommended actions.** A constraint in `user_context.md`
  (e.g. *no same-day changes*, *PPC restriction in market X*, *no ticket-only recommendations*)
  means you **never recommend the disallowed lever** in Section 10 / the Executive Summary
  actions table. If a sized opportunity points at a disallowed lever, annotate it as
  constrained and offer the nearest allowed lever instead — never surface an action the
  analyst has ruled out.
- **Known events corroborate paid timing.** A Known event with an in-window date that aligns
  with a paid CPC / clicks / CVR break is a **Pattern A** corroboration of *when* the paid
  signal moved — cite `(per user context)` on the gate row.
- **Priors get closed, proportionally.** Each Hypothesis prior is resolved CONFIRMED /
  RULED-OUT / DATA-GAP, same discipline as the gate's own signals. **Proportional output:** a
  ruled-out prior gets **one line** (`Checked [prior] against paid data — ruled out: [reason]`);
  a confirmed prior is woven into the finding it supports. Never inflate a prior's emphasis to
  match how strongly the analyst asserted it — the **paid data decides the weight**, and the
  report still leads with the data-driven primary driver.

**Provenance / standalone-safe citations:** cite a corroboration **only when its lens is
present**:

- CE Health → `(CE Health: … ↗)` linking to a real `#cehealth-*` anchor (e.g.
  `#cehealth-driver-diagnosis-shapley`, `#cehealth-top-tgids`). Emit the anchor only when
  `ce_health_report.md` was actually present — never leave a dangling anchor.
- User context → `(per user context)` for a corroboration, `(prompted by user context)` for a
  prior you tested. No tab anchor — user context isn't a tab; it's a plain parenthetical.
- Slack → `[Author · date](thread-url)` to the real thread.

**Standalone-safe — the clean no-op.** A standalone perf-audit run has **none** of these
lenses in its directory. With no lens present, Step 5b finds nothing to reconcile, runs **no
queries**, emits **no citations**, and the Section 9 gate + Step 6 transcript + the whole
report are **identical to today**. There is no `#cehealth-*` / Slack / `(per user context)`
citation anywhere unless the corresponding lens was actually read. Perf's language and
styling guidelines, the standalone funnel (no `/cvr-rca`), and the gate/transcript contract
all stay intact.

### Step 6 — Decision transcript (gate-driven)

Write a **decision transcript** to **`transcript_perf_audit.md`** in the run directory — the
`<run_dir>` you were told to use under an orchestrator (it's also in `orchestration.json` →
`run_dir` if present); standalone, write it in the same directory as your `--output` report.
**The filename must be exactly `transcript_perf_audit.md`** (an umbrella orchestrator collects
`transcript_<skill>.md` files into a Transcript tab and **renders them as markdown**, so it shows
the *reasoning* behind the audit — not the report's tables).

**The transcript wraps the Section 9 coverage gate.** The Section 9 "Signals to Close" table is the
**formal record** — the engine enumerates every material mover and each must be closed as
**CONFIRMED / RULED OUT / DATA GAP**. The transcript is that gate's **narrative wrapper**: for every
enumerated signal in the gate, record the **hypothesis → check → disposition** exactly as you entered
it in the gate, so the last-tab sub-tab shows the reasoning behind each gate disposition. Do not
invent signals the gate didn't enumerate, and do not silently drop one the gate did — every gate row
gets a line here. (Gate = the formal record; transcript = its narrative wrapper.)

It has **two layers**, mirroring CVR-RCA's transcript:

**1. A tree-map** at the top showing the audit's branch structure at a glance. **Wrap it in a
` ```text ` code fence** so the `├─ │ └─` alignment survives markdown rendering. Root = the overall
verdict; one branch per enumerated gate signal (or lens), each marked CONFIRMED / RULED OUT / DATA GAP
+ one-line evidence; `LEAF` = the headline finding.

````markdown
# Perf-Audit Transcript — CE [id] · [name]
Windows: L4W [dates] · P4W [dates] · LY [dates] | Mode: [full engine | SQL-only]

## Tree map
```text
ROOT: [overall paid verdict in one line]
├─ Traffic quality (SIS / CPC / CVR)   → [CONFIRMED / RULED OUT / DATA GAP] ([one-line evidence])
├─ Campaigns + portfolio (tROAS/budget) → [CONFIRMED / RULED OUT / DATA GAP] ([evidence])
│   └─ [sub-branch if a specific campaign/cohort drove it] → [evidence]
├─ Coverage + matchmaking (lost IS, geo) → [CONFIRMED / RULED OUT / DATA GAP] ([evidence])
├─ Funnel (LP2S / S2C / …)              → [CONFIRMED / RULED OUT / DATA GAP] ([evidence; deep decomp = defer to CVR-RCA])
├─ Search intelligence (terms/Ahrefs)   → [RULED OUT / DATA GAP — no CSV] ([why])
└─ LEAF: [the headline finding / money-on-the-table call]
```

## [Signal / Branch] Traffic quality
[Hypothesis you formed, the check (the data cut / number), and the disposition
(CONFIRMED / RULED OUT + the number that ruled it out / DATA GAP) as entered in the gate.]

## [Signal / Branch] Campaigns + portfolio
[…]

## [further branches as needed — one `##` per enumerated gate signal you disposed]

## Verdict
[The executive-summary takeaway in a sentence or two, plus what you ruled out / marked DATA GAP and why
— uploads not provided, sections N/A, dead ends.]
````

**2. Detail sections** (the `##` blocks under the tree) — plain markdown; conclusions and the
deciding numbers, **not** a re-render of the report's tables. Each `##` block mirrors a gate signal:
state the **hypothesis**, the **check** (the data cut / number) behind it, and the **disposition**
(CONFIRMED / RULED OUT + the number that ruled it out / DATA GAP) as entered in the Section 9 gate.
Only include signals the gate enumerated; mark anything skipped (e.g. no auction-insights CSV) as
`RULED OUT / DATA GAP`. For the funnel branch, record the funnel hypothesis you formed from
paid-session data and the `defer to CVR-RCA` verdict for the deep decomposition — do not re-derive the
deep funnel here.

---

## Narrative Rules

### Reasoning Flow — Natural Language

Every section follows: **frame → test → conclude**. No labeled templates (`**Hypothesis:**`, `**Verdict:**`). Natural analyst prose.

1. Opening framing (1-2 sentences setting expectations from prior sections)
2. Narrative + data (walk DIAGNOSTICS.md trees, testing branches)
3. Closing conclusion (clear "so what")

Each section's opening connects to the prior section's finding. Section 4 closes with a causal chain linking all conclusions.

**Plain language — applies to EVERY section, not just the summary.** Write for a GM/Perf lead in plain, concrete cause→effect prose (model the `/cvr-rca` report's exec summary). Short sentences. State the mechanism literally. Avoid:
- Clever abstractions — e.g. "clicks are the *mechanism*, not the cause." Say it plainly: "clicks fell −62%, but they fell *because* take rate dropped," then give the literal chain.
- Jargon-dense clauses — "the signature of a tROAS the algorithm can no longer hit." Say: "the pattern you get when revenue per click falls below what the ROI target needs, so the algorithm stops competing."
- Metaphors ("the bleed", "the engine is hemorrhaging") and \$10 words where a plain one works.
A line that sounds smart but takes two reads is a rewrite, not a keeper.

### Materiality Threshold — ±5% Rule

**Ignore deltas within ±5%.** Do not write narrative about metrics that moved less than 5%. If all metrics are within ±5%, say "no material movement" and move on. This prevents the model from building full stories around noise (e.g., CVR +0.16pp = +5.6% → borderline, don't lead with it).

When multiple metrics moved >5%, lead with the **largest double-digit mover first**. Do not bury a 30% click increase under a 5% CVR improvement.

### Revenue Driver Ordering — anchored to the computed Shapley

**The Paid Value Decomposition (Shapley) in Section 4 is the source of truth for driver attribution.** The engine decomposes the paid CM1 change into Clicks × CVR × Avg CM1 (exact contributions, $ and % of Δ, MoM + YoY). You do not infer the ordering from prose — you **read it from the Shapley and narrate it.** This is the core discipline ported from CVR-RCA: attribution is computed, not argued.

Order the narrative by the Shapley's |contribution|, which conceptually follows:

1. **Clicks/traffic** — volume. Almost always the largest driver.
2. **Average CM1** (= paid CM1 / conversions) — value per paid conversion. It *moves with* AOV × CR × TR (price, completion, take) and product mix, minus direct-cost mix — so when it leads, the value-per-conversion moved, not volume. (Note: this is the *paid* Avg CM1; the TGID table's "Net Rev/Order" is the cost-free cousin AOV × CR × TR. Don't conflate them.) If Avg CM1 leads, go to the TR/CR tree + Product Mix (TGID) table.
3. **CVR** — conversion rate.

**Rules:**
- Lead with whichever driver has the largest |contribution| in the Shapley. State its share (e.g. "clicks drove 98% of the +$8.4K MoM CM1 gain").
- A driver whose Shapley share is small is NOT the story, even if its raw metric moved — note it and move on (respects the ±5% threshold).
- **Never lead with CVR when the Shapley says clicks or Avg CM1 own more.** The Eiffel Tower failure mode: revenue +16% MoM, CVR +5.6% (noise), clicks +30% — leading with CVR buried the real story. The Shapley makes that mistake structurally hard.
- Offsetting drivers are common and informative: if clicks are +98% but Avg CM1 is −67% (mix shift to a cheaper product), say both — the net is small but the underlying forces are large and worth flagging.
- **Net ≈ flat blocks:** when the Shapley flags a block "net ≈ flat; large offsetting drivers" (the share column switches to *share of gross*), do NOT report the near-zero net as "stable." The story is the offset itself — e.g. "paid CM1 was flat MoM, but that masks a volume pullback (clicks −$17K) almost exactly cancelled by higher value per conversion (avg CM1 +$19K) — the mix shifted up-market." Name what drove each side (tie the avg CM1 side to the TGID table).
- **Shapley is arithmetic, not causal — the largest factor can be a downstream symptom.** Clicks is almost always the largest *arithmetic* mover, but a take-rate / completion-rate drop can be the *cause* of that click loss (TR↓ → avg CM1↓ → algorithm can't hit tROAS → SIS↓ → clicks↓; see "Take Rate + Completion Rate = Bidding Inputs" below + DIAGNOSTICS §7b). **When TR or CR moved >5% AND clicks fell, trace clicks back through the §7b chain before declaring clicks the driver.** The tell: if CPC *fell* alongside the click loss (internal algorithm retreat, not external competition) and ROI held roughly flat, the root is the upstream TR/CR constraint — volume was *traded* for efficiency, not lost to demand. In that case narrate the causal root as the lead and clicks as its *mechanism*; don't let the arithmetic-largest factor bury the cause. (Eiffel YoY: clicks owned the largest Shapley share, but TR −7.7pp → CPC −12% → SIS collapse / ~80% rank-lost was the root, with paid ROI holding ~139%.)

### Take Rate + Completion Rate = Bidding Inputs

Take rate and completion rate are not just reporting metrics — they directly control the algorithm's ability to bid. When TR or CR drop:
- CM1 per booking drops → avg CM1 drops
- The algorithm can't hit its tROAS target at the same bid level
- It retreats from auctions → SIS drops → clicks drop → revenue drops

This causal chain (TR↓ → avg CM1↓ → can't bid → SIS↓ → clicks↓) must be surfaced whenever TR or CR moved >5%. Do not diagnose SIS compression without checking if TR/CR is the upstream cause.

### Executive Summary — Write LAST (Section 1)

- **Status**: CRITICAL / WARNING / HEALTHY
- **Conclusions table** (immediately after status — NOT actions):

  | # | Conclusion | Owner | Sized Opportunity | Evidence |
  |---|-----------|-------|------------------|----------|

  State findings, not prescriptions. "EN SIS 17% with 83% rank-lost, avg CM1 $X constrains bidding" — not "reduce tROAS to 140%."

- **Causal story**: 2-3 sentences following the **driver ordering** read directly from the Section 4 Paid Value Shapley. Lead with the driver owning the largest |contribution| and cite its share (e.g. "paid CM1 −$50K YoY, clicks owned 97% of it"). If a product-mix shift drove Avg CM1, name the TGID. Do not let the prose pick a different lead than the Shapley.
- **Channel attribution**: which channel(s) drove the delta (from Section 3)
- **Funnel findings**: If the standalone paid-session funnel (Section 7) sized a material leak (e.g. an S2C or C2O LY gap), it MUST appear in the actions table as a sized, owned action, flagged for the CVR-RCA tab to decompose. Example: "Fix S2C ~9pp LY gap (~670 lost checkouts/L4W) — sized from paid-session funnel; deep locus deferred to CVR-RCA tab"
- Every metric labeled with source: "(BQ, paid)" or "(funnel)" or "(GAds)"

### Conditional Reporting

If CE diagnosis is HEALTHY across all signals:
- Output Sections 1-4 + condensed Section 10 (top 3 actions only)
- Skip deep dive sections (5-9)
- Total report: <200 lines

If WARNING or CRITICAL → full 10-section report.

### Portfolio Campaign Awareness

- `Type = Individual` → individual target ROAS campaign (bid_strategy_name is null)
- `Type = Portfolio` → shared budget + shared target ROAS across many campaigns
- Do NOT flag portfolio campaigns as "dormant" — they share budget dynamically
- Monthly cadence: high-performers graduate from portfolios to individual campaigns

### tROAS / ROI Relationship

tROAS is a **bidding lever**, not a metric to match:
- **Higher tROAS** → Google bids conservatively → less volume, higher efficiency
- **Lower tROAS** → Google bids aggressively → more volume, lower efficiency

Google's Smart Bidding doesn't hit targets exactly. A 160% target delivering 147% actual ROI is **normal algorithm variance** (~15% buffer). Rules:
- Do NOT recommend reducing tROAS when actual ROI is within 15% of target — that's expected behavior
- Lowering tROAS tells Google to bid MORE aggressively (more spend, lower efficiency) — only recommend when volume is the bottleneck, not efficiency
- If actual ROI is significantly below target (>15% gap), investigate quality score, landing page, or competition — the problem is rarely the tROAS setting itself
- For portfolio campaigns: the target applies to the portfolio as a whole, not individual campaigns. One campaign at 147% and another at 175% averaging to 160% is working as designed

### tROAS Recommendation Methodology

When recommending a tROAS change (only when rank-lost > budget-lost AND volume is the bottleneck):

1. **Target = current actual ROI × 0.90** (10% headroom for algorithm variance). Example: English actual ROI 157% → recommend tROAS ≤ 141%, round to 140%.
2. **Floor = 130%** — never recommend below this (breakeven risk).
3. **Ceiling = current tROAS** — if actual ROI is within 15% of target, don't change.
4. **Floor-hitting edge case:** If all cohorts compute to ≤130% (actual ROI 131-144% × 0.9 = 118-130%), don't just recommend "130% for everything." Instead: (a) flag that TR or RPC decline is making current tROAS targets structurally unachievable, (b) recommend 130% as a short-term bridge, (c) identify the upstream fix (TR recovery, product mix, S2C). The insight is that tROAS is a symptom — the root cause is why RPC can't support higher targets.
5. **State the math in the action table:** "Reduce EN tROAS 155% → 140% (actual ROI 157% × 0.9 = 141%)"
6. **Per-language, not blanket.** Each cohort has different ROI and competition. English at 157% gets a different target than German at 163%.
6. **Never recommend below LY ROI floor** unless there's a specific volume recovery rationale.

### Section 5 Narrative Rules (Coverage + Matchmaking)

After the pre-rendered cohort table, **always do the language competition scan first:**

**Language-level CPC × Scale scan (required before cohort breakdown):**

For each language cohort with >$1K spend, state CPC direction and scale direction YoY:

| Language | CPC Δ LY | Clicks Δ LY | Signal |
|----------|----------|-------------|--------|
| English | +14% | -62% | Competition — CPC up, scale halved |
| German | +9% | +6% | Healthy — moderate CPC rise, scale stable |
| Italian | +70% | +48% | Scaling aggressively |
| Spanish | +17% | -76% | Competition + pullback |

This tells the reader immediately: which languages are losing to competition, which are growth engines. The executive summary should lead with this framing — not "reduce tROAS across the board."

Then:
1. **Top 3 cohort driver breakdown** — for top 3 by revenue share, explain what drove RPC: CVR vs AOV vs TR. Lead with ROI.
2. **L12M trajectory per cohort** — reference appendix A3 when it changes interpretation
3. **Coverage gaps** — present as lowest-hanging fruits first:
   - PMax not existing (check child accounts)
   - Language/geo targeting gaps (campaign targeting table in appendix A7)
   - Dormant campaigns (benchmark tROAS vs active cohorts)
   - Geographic gaps (geo table in skeleton)
4. **Portfolio campaigns** — use Type column in budget table. Don't flag portfolio campaigns as underperforming if ROI is within 15% of target.
5. **Tourist mix context** (1-2 sentences from LLM knowledge, labeled as "est.")

### CPC 3-Lens Tree (Section 6b)

Apply in order:
1. **Quality traffic?** — CVR improved alongside CPC → Google buying better clicks. GOOD.
2. **AOV structural?** — ticket price rose → everyone bids more. Structural.
3. **Competition?** — ONLY state if: auction insights show new competitors OR SIS declining MoM. Never say "competition" without evidence.

Separate CPC story from SIS story. CPC can be justified (quality clicks) while SIS decline is concerning (showing in fewer auctions).

### Competitor Tables (CSV-dependent)

If auction insights CSVs provided, parse and build two tables:

**Step-by-step CSV processing:**

CSV format: Row 1 = title ("Auction insights report"), Row 2 = date range, Row 3 = headers. Data starts Row 4. Columns: Week, Display URL domain, Impression share, Overlap rate, Position above rate, Top of page rate, Abs. Top of page rate, Outranking share. Percentage values have "%" suffix — strip before computing. "--" means no data for that week.

1. Read CY CSV. Skip rows 1-2. Parse headers from row 3. Group rows by "Week" column date.
2. Split into L4W (last 4 weeks by date) and P4W (first 4 weeks). If not exactly 8 weeks, split into equal halves.
3. Read LY CSV. Same parsing. Split into L4W and P4W.
4. For each competitor ("Display URL domain"), compute average SIS per half-window. Skip "--" values. Average = mean of non-null weekly SIS values.
5. Compute Δ P4W = L4W avg SIS − P4W avg SIS (MoM pace) for CY and LY separately.
6. Compute Δ of Δ = CY Δ P4W − LY Δ P4W. Positive = competitor accelerating. Negative = decelerating.
7. Compute same for all other metrics (Overlap rate, Position above, Top of page, Abs top, Outranking share) for the Competitive Position table.

**Table 1 — SIS Trajectory (delta of deltas):**

```
| Competitor | LY P4W | LY L4W | LY Δ P4W | P4W | L4W | Δ P4W | Δ of Δ |
|-----------|--------|--------|----------|-----|-----|-------|--------|
| viator.com | 46.4% | 44.7% | -1.7pp | 51.2% | 54.5% | +3.3pp | **+5.0pp ↑** |
| Headout (You) | 27.3% | 35.3% | +8.0pp | 24.9% | 22.0% | -2.8pp | **-10.8pp ↓** |
```

Required footnote: `* LY vs CY SIS not directly comparable (account consolidation changed denominator). Δ of Δ compares MoM pace within each year — the reliable signal.`

**Fallbacks:**
- LY CSV unavailable: show CY-only table (P4W, L4W, Δ P4W) without Δ of Δ. Note "LY auction insights unavailable — MoM only."
- LY CSV from different account (pre-consolidation): expected — Step 0 instructs downloading from the old account. Competitor names should still match across accounts. If a competitor appears in CY but not LY, show "— (new)" for LY columns.
- CSV covers different weeks (not 8): split into equal halves regardless. Note the actual date range.
- Partial LY data (fewer competitors or fewer weeks): use what's available. Note gaps inline (e.g., "LY data: 4 weeks only").

**Table 2 — Competitive Position (CY L4W snapshot):**

```
| Competitor | SIS | Overlap Rate | Position Above | Top of Page % | Abs Top % | Outranking Share |
```

Full period averages from CY CSV. No deltas — this is a snapshot.

Without CSVs: Fall back to cohort SIS/rank-lost data from Section 5. Note "Competitor names unavailable — auction insights CSV not provided."

### Section 6a (Demand) Rules — via Ahrefs

**Keyword selection:** Pick 3-5 keywords representing the CE's core search intent across top markets:
- CE name in the primary market language (e.g., "pompei biglietti" for IT)
- CE name in English (e.g., "pompeii tickets" for GB/US)
- CE name in top non-English markets (e.g., "pompeji tickets" for DE, "billets pompei" for FR)
- Use the search term cluster data (Section 8) to identify the highest-volume terms per language.

**Ahrefs calls:**
```
mcp__claude_ai_Ahrefs__keywords-explorer-volume-history(
  keywords=["pompei biglietti", "pompeii tickets", "pompeji tickets"],
  country="IT"  // 2-letter ISO code for primary market
)
```
Run for each relevant country (primary market + top 2-3 feeder markets from geo table).

**Table format:**
```
| Keyword | Country | Jan | Mar | May | Trend |
|---------|---------|-----|-----|-----|-------|
| pompei biglietti | IT | 6,761 | 8,465 | 8,532 | +26% from Jan |
```

Show 3 months minimum (Jan → current) to capture seasonal ramp. If Ahrefs unavailable, note "Ahrefs demand data unavailable" and skip to Section 6b.

**Narrative:** Connect demand trend to paid click trend. If demand is growing but clicks are falling → capture problem (SIS). If demand is declining → market contraction, not a paid issue.

### Section 7 (Funnel) Rules — standalone paid-session funnel

The perf audit owns its funnel and does **NOT** invoke `/cvr-rca`. Use the standalone paid-session
funnel query from Step 4 (`mixpanel_user_funnel_progression`, paid sessions only). The deep funnel
decomposition (device / experience / C2O sub-stages / LY gap) is **deferred to the CE-RCA CVR-RCA tab**
— the perf audit only forms and sizes the funnel hypothesis here.

**Validation:** Compare the paid-session funnel CVR Δ (o/lp, L4W vs LY) against the cohort table TOTAL
CVR Δ (Section 5). Direction must agree. Note magnitude gap (~0.1-0.2pp expected — different data
sources: clicks vs LP users).

**Narrative structure:**
1. Headline: which funnel stage (LP2S / S2C / C2O) carries the CVR change — name it before details
2. Direction + magnitude: CVR improved/declined by Xpp, driven by [stage] — consistent with cohort table CVR trend
3. LY structural gap: if S2C or C2O is Xpp below LY, is it narrowing or persisting? Seasonal or structural?
4. Form the funnel hypothesis (which stage, how large the leak, ~sessions/L4W) and record `defer to CVR-RCA` for the deep decomposition (device / experience / C2O sub-stages). Do NOT decompose those here — that's the CVR-RCA tab's job.

**Do NOT decompose the deep funnel here** (device, experience, C2O sub-stages, LY-gap attribution) —
that belongs to the CE-RCA CVR-RCA tab, which uses the richer `mixpanel_user_page_funnel_progression`
table. The perf audit's job is to size the leak and hand the hypothesis over.

### Section 8 (Search Intelligence) Rules

The skeleton renders an **Ad Group Coverage** table from BQ (aggregated by type: Tickets, Generic, Tour, DSA with languages and metrics). This is always available.

**If search terms CSV uploaded, build three analyses:**

**Important:** Before clustering, filter the CSV to `Campaign type = 'Search'` rows only. PMax terms appear in the CSV but inflate GENERIC/OTHER to ~98% of spend, making the cluster analysis useless. Filter first, then classify.

**8a. Search Term Clusters** — classify each search term (first match wins):
1. COMPETITOR (klook, viator, getyourguide, tiqets, musement, civitatis...)
2. INFORMATIONAL (timings, hours, orari, horaire, directions, parking, free, gratis, map, history...)
3. TICKETS (ticket, biglietti, billet, entradas, eintrittskarten, price, buy, book, admission, prenota, réserv...)
4. TOURS (tour, guided, walking, day trip, excursion, escursione, ausflug, visite guidée, gita...)
5. ATTRACTION (CE name variations, sub-attractions, archaeological, ruins, scavi...)
6. GENERIC/OTHER (everything else — often non-English terms)

Render cluster table: | Cluster | Terms | Clicks | Spend | CVR | CPC | Conv | Spend Share |

**8b. Ad Group × Cluster Cross-Reference** — this is the key coverage check. Use the CSV's ad group column (column 4) to build:

| Search Cluster | Matched AG Type | AG Clicks | Cluster Clicks | On-Target % | Action |
|---------------|----------------|-----------|----------------|-------------|--------|
| TICKETS | Tickets | X | Y | Y/X% | — |
| ATTRACTION | Generic | X | Y | Y/X% | — |
| TOURS | Tour | X | Y | Y/X% | Weak if <30% |
| INFORMATIONAL | (none) | — | Y | — | Flag if >$500 spend |
| COMPETITOR | (none) | — | Y | — | Flag if >$200 spend |

On-Target % = what fraction of the AG type's clicks come from matching search intent. Low on-target means the AG is catching overflow from other intents via broad match.

**Actionable findings from this table:**
- AG type with <30% on-target → broad match overflow, consider tightening match types
- Search cluster with no matched AG → potential new ad group if volume justifies
- High-CVR cluster landing in wrong AG type → dedicated ad group could improve ad relevance + CTR
- Language present in one AG type but missing in another → language coverage gap

**8c. Wasted Spend Flags** — only flag terms with ≥100 clicks and 0 conversions. Require 6+ months poor performance for negative keyword recs. Show LY comparison if available.

**8d. Keyword Volumes** — per cluster from keyword planner if available. Sizes the opportunity.

**If no CSV:** Use the rendered Ad Group Coverage table + cohort SIS data. Note "Search terms CSV not provided — abbreviated analysis. Ad group coverage from BQ only."

Cluster-first, not search-term-first. Ad group coverage against experience clusters is the actionable layer.

### Section 10 — Conclusions (forwardable, not bid-prescriptive)

Section 10 states **conclusions** — but they must be **forwardable**: a Perf lead should be able to hand any row to a teammate and act on it. The line we don't cross is dictating a *bid magnitude*; everything else (the lever, the size, the owner, the constraint) belongs.

**Format — a table, every row carries lever + sized opportunity + owner + constraint:**

| # | Conclusion (lever) | Sized Opportunity | Owner | Constraint / why | Evidence |
|---|--------------------|-------------------|-------|------------------|----------|

Example row: "English SIS 17% → recover auctions | +$15K/L4W at +10pp SIS | Perf | rank-lost 80%, 0% budget-lost; RPC/TR is the ceiling, not the tROAS number | §5, §6c". That's actionable AND doesn't prescribe "set tROAS to 140%."

**Bid constraint (prompt-level rule):** keep the *lever, size, and owner* (forwardable), but do NOT prescribe a specific bid/tROAS number or recommend cutting bids >5% — name the lever and let Perf set the magnitude. "Recover SIS on English (+$15K/L4W), Perf to set the bid — constraint is RPC/TR" ✓; "lower tROAS to 140%" ✗. Never recommend a vague non-action ("monitor", "investigate") — every row has a sized lever and an owner.

**What to include:**
- Which metrics are the material movers (>5% threshold)
- The causal chain (e.g., TR↓ → avg CM1↓ → SIS↓ → clicks↓)
- Sized opportunity where applicable (SIS × RPC, funnel gap × sessions)
- What is NOT the problem (rule out noise — e.g., "CVR +5.6% is within noise, not a driver")
- Owner routing (Perf, Product, Supply, SEO) for each conclusion

### Bing Depth Rule

Default: summary row in Channel Breakdown only. Deep dive only if Bing revenue moved >50% YoY OR >$5K absolute change. Markets for Bing deep dive: France, UK, US (high browser adoption + revenue contribution). APAC: skip Bing entirely.

### Mixed Product Lines Within One CE

Some CEs contain campaigns for different product types (e.g., Eiffel Tower has tower ticket campaigns AND Madame Brasserie restaurant campaigns). These have different economics (different TR, AOV, keyword intent). When you see campaign names suggesting mixed products:
- Note it in Section 5 coverage narrative: "This CE contains mixed product lines (tower tickets + dining). Blended metrics are influenced by mix shift."
- Do NOT break out separate analysis per product — treat them as portfolio campaigns.
- If one product dominates (>80% of spend), analyze as a single-product CE. Note the minority product as context.

---

## Perf Infra Context (read before interpreting campaigns)

- **Geo consolidation (Feb 2026):** City-specific → region-specific accounts. Paused geo campaigns (EN-RoW, EN-RoA) are INTENTIONAL.
- **tCPA → tROAS transition:** Dec 2025 (Phase 1), Jan (Phase 2), Feb (Phase 3). PMax first, Bing March 2026.
- **PMax structure:** City/country-level, NOT CE-specific. Use fct_orders attribution for per-CE PMax metrics.
- **145% tROAS standard** for Pro+ CEs. CM1-based bidding.
- **Portfolio campaigns:** Long tail CEs grouped under shared-budget portfolios (160% target). See Portfolio Campaign Awareness section.
- **SIS YoY is NOT like-for-like:** Account consolidation + broad match + tROAS expanded eligible-impression denominator. Use **MoM as primary SIS signal**. YoY directional only.
- **Language/geo config checks:** Automated daily by perf scripts. Zero manual fixes needed. Don't flag config issues in the audit.

---

## Date Range Calculations

**L4W (default):** Last 4 complete weeks (Monday–Sunday), aligned to ISO weeks.
**P4W:** The 4 weeks immediately before L4W.
**LY:** Same ISO weeks last year (364 days back).

---

## Global Rules

1. **Insights-first**: narrative leads every section
2. **Source labeling**: every metric labeled "(BQ, paid)" or "(GAds)"
3. **Revenue distinction**: "Revenue (BQ)" vs "Conv Value (GAds)"
4. **Competitive claims require evidence**
5. **L12M for recommendations**: any pause/merge must cite 12-month performance
6. **Report length proportional to health**: SHORT (<200 lines) for healthy, STANDARD (200-400) for warning, FULL (400-700) for critical
7. **Question-answer framework**: every section answers explicit questions or acknowledges gaps
8. **Money-on-table sizing**: SIS gap × RPC, tourist % × CVR × AOV, or cluster volume × CVR
9. **ROI = CM1 ÷ Spend.** One metric, from BQ. Don't define it in reports.
10. **BQ is the YoY baseline, not GAds conv_value.** GAds switched from revenue to CM1 in Oct 2025.
11. **Budget commentary only when budget IS the constraint.** Only surface when budget-lost IS >10%.
12. **Succinct footers.** One line max. State scope, not methodology.

---

## Anti-Patterns — NEVER DO THESE

1. NEVER reference budget utilization as self-suppression (44% of budget is fine)
2. NEVER equate unused budget with lost clicks
3. NEVER say "portfolio setting bids low" if tROAS is 160%+
4. NEVER recommend reducing tROAS to "match" actual ROI — lowering tROAS increases spend, not efficiency. Only recommend lowering when volume is the bottleneck.
5. NEVER flag portfolio campaigns as "dormant" — they share budget dynamically
6. NEVER show blended funnel — filter to largest cohort
7. NEVER recommend reactivating paused geo campaigns without checking consolidation
8. NEVER flag PMax as missing without checking child account migration
9. NEVER say "competition" without citing auction insights or SIS MoM data
10. NEVER recommend pausing a language campaign based on L4W only — show L12M
11. NEVER start a section with a table — narrative first
12. NEVER invent "GAds ROI vs BQ ROI" — there is ONE ROI
13. NEVER compare campaign count YoY (consolidation merged 2-3 per language into one)
14. NEVER flag YoY SIS drops as CRITICAL (denominator expansion, use MoM)
15. Don't confuse GMV (`order_value_completed_usd`) with revenue (`amount_revenue_usd`)
16. NEVER flag position segments or search partners (dropped — not actionable)
17. NEVER flag language/geo config issues (automated daily by scripts)
18. If CM1 > Paid Revenue for any window after rendering, flag as a data issue — the renderer already corrects PMax `sum_conversion_value` (GMV) via `revenue_percentage`, so this should be rare. If it still occurs, the gap should be <5%. If larger, investigate PMax attribution.

---

## Quality Checklist

- [ ] Skeleton tables untouched (not reformatted)
- [ ] Every `<!-- ... -->` marker replaced with narrative
- [ ] Section 2-3-4 narratives flow: CE Overview → Channel mix → Paid drill-down
- [ ] Top 3 cohort driver breakdown present (CVR vs AOV vs TR)
- [ ] L12M trajectory referenced from appendix A1/A2
- [ ] CPC explanation uses 3-lens tree
- [ ] Competitor tables present if CSVs provided (SIS Trajectory + Competitive Position)
- [ ] Money on table sized in $/L4W
- [ ] Funnel: standalone paid-session funnel run (no /cvr-rca), leak sized, direction validated against cohort CVR, deep decomposition deferred to CVR-RCA tab
- [ ] Portfolio campaigns correctly identified (Individual vs Portfolio in budget table)
- [ ] No budget flags unless >10% budget-lost
- [ ] No "competition" without evidence
- [ ] Every action: specific, $ sized, owned, timed, evidence link
- [ ] Section 10 has conclusions (not prescriptive actions). No bid changes >5% recommended.
- [ ] Driver ordering: clicks first, then avg CM1, then CVR. No CVR-led stories when clicks moved more.
- [ ] Paid Value Shapley read FIRST in Section 4; narrative leads with the largest-|contribution| driver and cites its share %. Prose does not contradict the computed attribution.
- [ ] Product Mix (TGID) Δ Share checked; any |Δ Share| > 5pp (new hero / decayed product) named and routed. Cross-checked against the Avg CM1 Shapley driver.
- [ ] Campaign × Product table read; any high-volume campaign concentrated in a low-TR product named + routed (or "all campaigns map to healthy-TR products"). Judged on TR / CM1/Ord, not ROI.
- [ ] Ad Group Audit read; Scale + Leak ad groups named with the lever ($ at risk for Leaks, bid-headroom for Scale) and Leaks cross-checked against §4 (systemic TR vs genuine per-AG fix). Or "ad groups on-target."
- [ ] ±5% threshold: no narrative about metrics that moved <5%
- [ ] Executive Summary (Section 1) written LAST with causal chain
- [ ] CM1 ≤ Paid Revenue in all windows (footnote if not)
- [ ] Language CPC × Scale scan in Section 5 (not just blended CPC)
- [ ] tROAS recommendations state the formula (actual ROI × 0.9, floor 130%). If all hit floor, flag TR/RPC as root cause.
- [ ] A2 vs A3 consistency: if any month shows CVR 0% or ROI <10% in A2 but normal ROI in A3, flag as possible tracking outage
- [ ] Report length matches status (SHORT/STANDARD/FULL)

---

## File Naming

`thoughts/shared/perf-audits/perf-audit-<slug>-<YYYY-MM-DD>-v6.md`

## Requirements

### BigQuery Access
- Project: `headout-analytics`
- Script: `perf_audit.py` (render subcommand)

### Ahrefs (optional)
- `keywords-explorer-volume-history` + `keywords-explorer-overview`

### Slack (optional)
- `slack_search_public_and_private` for SP context

## Related Skills

- `/ce-audit` — Full CE health check (supply, CX, organic, competitive)
- `/market-weekly-review` — Market-level weekly review
- `/availability-diagnostics` — Inventory and availability analysis
