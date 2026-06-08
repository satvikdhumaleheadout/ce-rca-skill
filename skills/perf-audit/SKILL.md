---
name: perf-audit-v6
description: Deep paid performance audit for a CE — zoom-out-first channel overview, campaign cohort backbone, 3 temporal windows, search intelligence, and sized actions
allowed-tools: [Bash, Read, Write, mcp__claude_ai_Ahrefs__keywords-explorer-volume-history, mcp__claude_ai_Ahrefs__keywords-explorer-overview, mcp__plugin_weekly-growth-review_slack__slack_search_public_and_private]
---

# Paid Performance Audit (v6.3)

Comprehensive paid-channel diagnostic for a CE. Python renders all BQ tables (including landing pages, keyword IS, campaign targeting). Claude writes narrative only.

**Audience:** Growth analyst + GM + Perf team
**Scope:** All paid channels. Non-paid issues detected and routed to `/ce-audit`.

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
4. Paid Deep Dive (Table 2 Search+PMax+Bing + Landing Pages — rendered by code)
5. Coverage + Matchmaking (cohort table, budget table, geo table — rendered by code)
6. External Dynamics (demand, competition, money on table)
7. Funnel (BQ query, Claude renders)
8. Search Intelligence (CSV-based if uploaded, cluster-first)
9. Red Flags Summary
10. Recommended Actions ($ sized, defensible)
A. Evidence Appendix (A1-A3 monthly trends, A6 budget detail, A7 targeting — rendered by code)
B. Data Sources
```

---

## Execution Modes

### Mode 1: Full Engine (recommended)

Uses the Python engine to fetch BQ data and render table skeleton. Claude fills narratives only.

### Mode 2: SQL-Only (no Python engine)

Claude reads `references/sql-reference.md`, runs queries inline via BQ CLI, and builds the report manually. Use this when the Python engine isn't installed.

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
> Share file paths anytime during the audit.

### Step 1 — Resolve CE + compute dates

Resolve the CE name to an ID:
```bash
python3 -c "
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
python3 -c "
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

This fetches all BQ data and outputs a markdown skeleton with pre-formatted tables and `<!-- ... -->` markers. All tables (CE overview, channels, Google Search, cohorts, budget with portfolio type, geo, landing pages, money-on-table, campaign targeting, appendix) are rendered by code.

**Mode 2 (SQL-Only):**
Read `references/sql-reference.md`. Run each query for the 3 windows (L4W, P4W, LY). Build tables manually.

### Step 3 — Read skeleton + DIAGNOSTICS.md, fill narratives

Read the skeleton file. All tables are pre-formatted — do NOT reformat them. Read `DIAGNOSTICS.md` for hypothesis trees. Walk the trees against the data.

Replace every `<!-- ... -->` marker with analysis following the narrative rules below.

**Section ordering:**
1. Fill Section 2 narrative (CE Overview — ROI trend, revenue trajectory)
2. Fill Section 3 narrative (Channel Breakdown — which channel drove delta)
3. Fill Section 4 narrative (Paid Deep Dive — CPC justified? Landing page CTR comparison)
4. Fill Section 5 narrative (Coverage — cohort drivers, coverage gaps, geo analysis)
5. Fill Section 6 (demand from Ahrefs, competition with CPC 3-lens, CSV competitor tables if provided)
6. Fill Section 7 (run funnel BQ query, render table, write narrative)
7. Fill Section 8 (search intelligence — if CSV uploaded, cluster search terms; otherwise keyword IS summary)
8. Fill Section 9 (Red Flags — consolidate from all sections)
9. Fill Section 10 (Actions — specific, sized, owned, timed)
10. Fill Section 1 (Executive Summary — write LAST after all other sections)

### Step 4 — Funnel query (BQ, not in renderer)

```sql
SELECT COUNT(*) as lp, COUNTIF(has_select_page_viewed = TRUE) as s,
  COUNTIF(has_checkout_started = TRUE) as c, COUNTIF(has_order_completed = TRUE) as o
FROM `headout-analytics.analytics_reporting.mixpanel_user_funnel_progression`
WHERE combined_entity_id = '<CE_ID>'
  AND session_date BETWEEN '<START>' AND '<END>'
  AND (acqusition_source LIKE '1 - %' OR acqusition_source LIKE '2 - %')
```
Run for L4W, P4W, and LY. Render funnel table in Section 7.

### Step 5 — Self-eval

Read `EVAL.md`. Run quick checks, score the report.

### Step 6 — Decision transcript

Write a **decision-tree transcript** to **`transcript_perf_audit.md`** in the run directory — the
`<run_dir>` you were told to use under an orchestrator (it's also in `orchestration.json` →
`run_dir` if present); standalone, write it in the same directory as your `--output` report.
**The filename must be exactly `transcript_perf_audit.md`** (an umbrella orchestrator collects
`transcript_<skill>.md` files into a Transcript tab and **renders them as markdown**, so it shows
the *reasoning* behind the audit — not the report's tables).

It has **two layers**, mirroring CVR-RCA's transcript:

**1. A tree-map** at the top showing the audit's branch structure at a glance. **Wrap it in a
` ```text ` code fence** so the `├─ │ └─` alignment survives markdown rendering. Root = the overall
verdict; one branch per audit lens, each marked CONFIRMED / RULED OUT / the call + one-line evidence;
`LEAF` = the headline finding.

````markdown
# Perf-Audit Transcript — CE [id] · [name]
Windows: L4W [dates] · P4W [dates] · LY [dates] | Mode: [full engine | SQL-only]

## Tree map
```text
ROOT: [overall paid verdict in one line]
├─ Traffic quality (SIS / CPC / CVR)   → [CONFIRMED / RULED OUT] ([one-line evidence])
├─ Campaigns + portfolio (tROAS/budget) → [CONFIRMED / RULED OUT] ([evidence])
│   └─ [sub-branch if a specific campaign/cohort drove it] → [evidence]
├─ Coverage + matchmaking (lost IS, geo) → [CONFIRMED / RULED OUT] ([evidence])
├─ Funnel (LP2S / S2C / …)              → [CONFIRMED / RULED OUT] ([evidence])
├─ Search intelligence (terms/Ahrefs)   → [RULED OUT / N/A — no CSV] ([why])
└─ LEAF: [the headline finding / money-on-the-table call]
```

## [Branch] Traffic quality
[What you examined, the numbers that decided it, what it rules in/out — a few lines.]

## [Branch] Campaigns + portfolio
[…]

## [further branches as needed — one `##` per lens you actually explored]

## Verdict
[The executive-summary takeaway in a sentence or two, plus what you skipped/ruled out and why
— uploads not provided, sections N/A, dead ends.]
````

**2. Detail sections** (the `##` blocks under the tree) — plain markdown; conclusions and the
deciding numbers, **not** a re-render of the report's tables. Only include branches you actually
explored; mark anything skipped (e.g. no auction-insights CSV) as `RULED OUT / N/A` in the tree.

---

## Narrative Rules

### Reasoning Flow — Natural Language

Every section follows: **frame → test → conclude**. No labeled templates (`**Hypothesis:**`, `**Verdict:**`). Natural analyst prose.

1. Opening framing (1-2 sentences setting expectations from prior sections)
2. Narrative + data (walk DIAGNOSTICS.md trees, testing branches)
3. Closing conclusion (clear "so what")

Each section's opening connects to the prior section's finding. Section 4 closes with a causal chain linking all conclusions.

### Executive Summary — Write LAST (Section 1)

- **Status**: CRITICAL / WARNING / HEALTHY
- **Actions table** (immediately after status):

  | Action | Expected Impact | Confidence | Why |
  |---|---|---|---|

  Confidence: Certain > High > Medium > Directional. Keep "Why" crisp — max 1-2 sentences with key numbers.

- **Causal story**: 2-3 sentences connecting root cause → symptom → $ impact
- **Channel attribution**: which channel(s) drove the delta (from Section 3)
- Every metric labeled with source: "(BQ, paid)" or "(GAds)"

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

### Section 5 Narrative Rules (Coverage + Matchmaking)

After the pre-rendered cohort table:
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

If auction insights CSVs provided:
- **SIS Trajectory** (delta of deltas): Split each 8-week CSV into L4W + P4W halves. Required footnote: `* LY vs CY SIS not directly comparable (account consolidation changed denominator). Delta of Delta compares MoM pace — reliable signal.`
- **Competitive Position** (CY L4W snapshot): All auction metrics, no deltas.

Without CSVs: Fall back to cohort SIS/rank-lost data from Section 5. Note "Competitor names unavailable."

### Section 7 (Funnel) Rules

- Filter to largest cohort only (e.g., Google Search English). Label explicitly.
- 3-window table: L4W, P4W, LY with MoM deltas
- MoM tells if leak is accelerating (URGENT) or recovering (monitor)
- Quantify leaks in $ and sessions
- Connect device split to funnel leaks if mobile CVR gap >0.5x desktop

### Section 8 (Search Intelligence) Rules

The skeleton renders an **Ad Group Coverage** table from BQ (aggregated by type: Tickets, Generic, Tour, DSA with languages and metrics). This is always available.

**If search terms CSV uploaded, build three analyses:**

**8a. Search Term Clusters** — classify each search term (first match wins):
1. COMPETITOR (klook, viator, getyourguide, tiqets, musement, civitatis...)
2. INFORMATIONAL (timings, hours, orari, horaire, directions, parking, free, gratis, map, history...)
3. TICKETS (ticket, biglietti, billet, entradas, eintrittskarten, price, buy, book, admission, prenota, reserv...)
4. TOURS (tour, guided, walking, day trip, excursion, escursione, ausflug, visite guidee, gita...)
5. ATTRACTION (CE name variations, sub-attractions, archaeological, ruins, scavi...)
6. GENERIC/OTHER (everything else — often non-English terms)

Render cluster table: | Cluster | Terms | Clicks | Spend | CVR | CPC | Conv | Spend Share |

**8b. Ad Group x Cluster Cross-Reference** — this is the key coverage check. Use the CSV's ad group column (column 4) to build:

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

**8c. Wasted Spend Flags** — only flag terms with >=100 clicks and 0 conversions. Require 6+ months poor performance for negative keyword recs. Show LY comparison if available.

**8d. Keyword Volumes** — per cluster from keyword planner if available. Sizes the opportunity.

**If no CSV:** Use the rendered Ad Group Coverage table + cohort SIS data. Note "Search terms CSV not provided — abbreviated analysis. Ad group coverage from BQ only."

Cluster-first, not search-term-first. Ad group coverage against experience clusters is the actionable layer.

### Action Rules (Section 10)

| # | Action | Owner | Est. Impact | Timeline | Evidence |

- SPECIFIC, $ SIZED, OWNED, TIMED, linked to evidence
- Lowest-hanging fruits first: reactivation → bid optimization → keyword opportunities → negatives → structural
- Minimum 5 actions, target 7-10
- Competitive response required when competitor IS > ours
- Verify: largest campaign ROI addressed, bid actions match actual strategy

### Bing Depth Rule

Default: summary row in Channel Breakdown only. Deep dive only if Bing revenue moved >50% YoY OR >$5K absolute change. Markets for Bing deep dive: France, UK, US (high browser adoption + revenue contribution). APAC: skip Bing entirely.

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
8. **Money-on-table sizing**: SIS gap x RPC, tourist % x CVR x AOV, or cluster volume x CVR
9. **ROI = CM1 / Spend.** One metric, from BQ. Don't define it in reports.
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
- [ ] Funnel filtered to largest cohort, 3 windows, MoM delta
- [ ] Portfolio campaigns correctly identified (Individual vs Portfolio in budget table)
- [ ] No budget flags unless >10% budget-lost
- [ ] No "competition" without evidence
- [ ] Every action: specific, $ sized, owned, timed, evidence link
- [ ] Minimum 5 actions, target 7-10
- [ ] Executive Summary (Section 1) written LAST with causal chain
- [ ] Report length matches status (SHORT/STANDARD/FULL)

---

## File Naming

- Report: `perf-audit-<slug>-<YYYY-MM-DD>-v6.md` (or `perf_audit_report.md` when an orchestrator
  sets `--output`).
- Decision transcript: `transcript_perf_audit.md` (Step 6) — fixed name, in the run directory.

## Requirements

### BigQuery Access
- Project: `headout-analytics`
- Engine: `perf_audit.py` (render subcommand)

### Ahrefs (optional)
- `keywords-explorer-volume-history` + `keywords-explorer-overview`

### Slack (optional)
- `slack_search_public_and_private` for SP context

## Related Skills

- `/ce-audit` — Full CE health check (supply, CX, organic, competitive)
- `/market-weekly-review` — Market-level weekly review
- `/availability-diagnostics` — Inventory and availability analysis
