# CE-RCA Skill — Changelog

This file tracks every meaningful change pushed to this repository. Each entry
is written for stakeholder consumption — what changed, why it matters.

---

## [v2.11.1] — 2026-06-10 — Summary vitals wrap to 6/row (ROI to next line, no overshoot)

**Summary:** With the CVR card added (v2.11.0) the Summary had **7** vitals cards forced onto one row (`repeat(7,1fr)` inline), overshooting the Summary tab's narrower container. They now cap at **6 equal columns** so the 7th (ROI(1)) wraps to a second row — every card the same size, nothing clipped.

### What changed
- **`references/visual_kit.md`** (additive block) — new `.metric-cards.summary-vitals { grid-template-columns: repeat(6, 1fr); }` (＋ a `max-width:800px` → 3-col rule). Two-class selector, so it beats base `.metric-cards`; additive-only, no existing class touched.
- **`references/summary_guide.md`** (block #2) — the vitals grid now uses `class="metric-cards summary-vitals"` with **no inline `grid-template-columns`** (inline would override the cap). 7 cards → 6 on row 1 + ROI(1) on row 2; 6 cards (CVR absent) → one row.

### Blast radius
- **`ce-rca` master only** — additive CSS + guide; no `compose.py`/template/sub-skill change. Verified the `.summary-vitals` rule reaches the composite's injected `<style>` and the guide carries no inline 7-col override.

---

## [v2.11.0] — 2026-06-10 — Omni metric reconciliation (funnel parity) · Summary provenance guard · Summary CVR card

**Summary:** Aligns the report's funnel/metric definitions with the **Omni dashboard** (the source of truth) so the same metric reads the same number across tabs and matches Omni. Verified on CE 3593 (Apr10–Jun08): the CVR-RCA funnel now lands at **LP 50,548 / CVR 6.14% / LP2S 42.9% / S2C 34.5% / C2O 41.52%** vs Omni's 50,543 / 6.1% / 42.89% / 34.48% / 41.52% (the ~5-user residual is the deliberately-skipped 30-day completion window — negligible). Five changes:

**(1) Drop the page-type whitelist** from the CVR-RCA funnel queries (`q1_base`, `q2_dimensions`, `q3_trend`) and CE Health's `fetch_monthly_cvr` — Omni applies none, so the LP population now matches (was 48,227 → 50,548). **(2) Exclude PERFORMANCE_MAX in the funnel section only** — added to CE Health's funnel-by-dimension, landing-page, and §4/§6 funnels (CVR-RCA already excluded it); the §3 Channel Breakdown still reports PMax as its own channel. **(3) Unify the LY window to −364 days** (52-week, DOW-aligned) — fixed CE Health's custom-date path (was a calendar-year −365 shift that drifted LY ~1 day); the month path stays calendar-aligned by design. **(4) SIS = impression-weighted** `SUM(impressions)/SUM(eligible)` in `fetch_market_benchmarks` (was `AVG(search_impression_share)`). **(5) Reconcile `fetch_all_paid_metrics`** to the core fct_orders convention (`NOT IN ('Dummy','Cancelled - Fraudulent') AND user_type='Customer'`).

Plus a **Summary provenance guard** (`summary_guide.md`): three rules — don't relabel a metric, attribute to the source tab, keep source precision — to stop the mis-transcription class (e.g. an ROI delta surfacing as a CVR delta). And the **Summary §2 vitals now include the CVR card** at position 3, mirroring the CE Health tab order (Revenue · Orders · CVR · AOV · Take Rate · Completion · ROI(1)).

### What changed
- **`skills/cvr-rca/references/q1_base.sql`, `q2_dimensions.sql`, `q3_trend.sql`** — removed the `page_type IN (...)` whitelist; PMax exclusion retained.
- **`skills/ce-health/engine/sources/bq.py`** — PMax exclusion added to `_fetch_funnel_by_dim` + `fetch_lp_funnel`; whitelist dropped from `fetch_monthly_cvr`; SIS → SUM/SUM in `fetch_market_benchmarks`; `fetch_all_paid_metrics` status/user_type filter reconciled.
- **`skills/ce-health/ce_health.py`** — PMax exclusion in `fetch_ce_funnel` + `fetch_tgid_funnel`; custom-date LY shift −365 → −364; §4 funnel labeled "cross-session · excludes PMax"; §2 vitals predicted-vs-actual note; Shapley revenue-basis comment.
- **`references/summary_guide.md`** — provenance guard after the cardinal rule; §2 vitals add the CVR card (position 3) and mirror CE Health order/decimals.
- **`skills/cvr-rca/references/report_structure.md`** — "excludes PMax" basis pill on the funnel section heading.

### Blast radius
- CVR-RCA funnel SQL + CE Health engine/render + the Summary/report guides. No `compose.py` / template / perf-audit change. The 30-day completion window and funnel-table grain were deliberately left unchanged (see thoughts/omni-reconciliation.md).

---

## [v2.10.0] — 2026-06-10 — Shapley CVR-basis correctness fix · CVR in vitals + a CVR card · foreground CE Health · scoped auto-update

**Summary:** Four fixes, headlined by a **correctness fix** to the CE Health driver decomposition. **(1) Shapley CVR basis (CORRECTNESS).** The CE-level Shapley used a **clicks** basis (`traffic = paid clicks`, `cvr = orders / clicks`) that could disagree in **sign** with the funnel/vitals CVR — so the driver ranking could show CVR as a drag while conversion had actually improved. It's rewritten to the **funnel basis** matching the §7 corrected 6-factor decomposition: `traffic = funnel (LP) users`, `cvr = converted_users / users` (the funnel CVR), `orders_per_converter = orders / converted_users` (when converter counts are available), plus `aov` / completion / take-rate from vitals. The guaranteed invariant — verified on CE 252/month — is that the multiplicative Shapley CVR factor's sign equals the direction of the funnel CVR: with funnel CVR rising 4.08% → 4.52%, the CVR factor flipped from the old **−$2.3K** to **+$10.0K**, and the decomposition total ($16,966.74) is unchanged. **(2) CVR in vitals + a CVR card.** The engine now carries the funnel CVR (orders/users) on each window's `vitals` dict in the sidecar (`vitals.current.cvr`, etc.), and the CE Health tab's §2 gains a **CVR metric card** alongside the other rate cards. **(3) Foreground CE Health.** The orchestrator now runs CE Health as a single foreground call (it's fast — internally parallelized) instead of the background/two-phase/poll-for-preview dance; the `--preview-marker` machinery is left in the engine but unused. **(4) Scoped auto-update.** The auto-update only fires for the canonical `~/.ce-rca` install; a dev/local copy now skips the version check and proceeds, avoiding a false "out of date" alarm and a denied-curl dead-end.

### What changed
- **`ce_health.py` (engine, re-vendored)** — `fetch_ce_funnel` emits `cvr` (orders/users ×100); `compute_shapley_for_ce` rewritten to the funnel basis (traffic = funnel users, cvr = converted_users/users, + `orders_per_converter`); `calc_shapley_decomposition` factor list gains `orders_per_converter`; `vitals[*].cvr` merged from the funnel before the sidecar write; the §7 engine table labels updated (Traffic = Users, new Orders/User factor). The Shapley engine `calc_shapley_decomposition` math is unchanged — only the factor dicts fed to it.
- **`scripts/render_ce_health.py` §2** — a **CVR card** added to the top vitals cards (order: Revenue · Orders · CVR · AOV · Take Rate · Completion · ROI(1)), via `card()` + `pp_delta`, reading `vitals[*].cvr`; grid widens to 7 cards; None-safe for older sidecars without `cvr`.
- **`SKILL.md`** — version block: `SKILL_DIR` = the dir this file was read from; version check/update gated to `SKILL_DIR == ~/.ce-rca`. Step 0d: one foreground CE Health run (no `--preview-marker`, no poll/PREVIEW_READY/FULL_READY/bounded-fallback). Step 1: read CVR from `sidecar.vitals[*].cvr`. Step 2: FULL_READY gate removed.
- **`VERSION`** 2.9.1 → 2.10.0.

### Blast radius
- CE Health engine (re-vendored into the bundle) + `render_ce_health.py` §2 + `SKILL.md` (Step 0/1/2 + version block) + changelog. **No** `compose.py` / template / CVR-RCA / perf-audit change. The full CE Health `.md` is unchanged **except §7** (now the funnel-basis Shapley, converging with the §7 render) **and** the new CVR card in §2 of the rendered tab.

---

## [v2.9.1] — 2026-06-10 — Summary vitals cards mirror the CE Health tab (order + formatting)

**Summary:** The Summary tab's vitals cards used their own order/labels/decimals (e.g. ROI shown 3rd as `159.7%`, AOV `$334.59`, label "CR"), which didn't match the CE Health §2 cards right below them. They now mirror CE Health exactly.

### What changed
- **`references/summary_guide.md`** (block #2) — prescribes the **exact CE Health order** (Revenue · Orders · AOV · Take Rate · Completion · ROI(1)), **verbatim labels** ("Completion", "ROI(1)" — not "CR"), and **matching decimal places** (Revenue money `$286.5K`; Orders comma-int; AOV `$`+0-dp `$335`; Take Rate/Completion 1-dp `21.7%`/`86.2%`; ROI(1) 0-dp `162%`). Values are CE Health's vitals, so the two tabs read identically.

### Blast radius
- **`summary_guide.md` only** — guide/authoring change, no code/template/sub-skill change. Verified on CE 3593: Summary vitals labels, order, decimals, and values match the CE Health §2 cards exactly.

---

## [v2.9.0] — 2026-06-10 — Latency: parallelized CE Health + preview-first two-phase + batched Step-0

**Summary:** The diagnosis preview now appears far sooner, with **zero change to the final report**. Three moves: **(1) Parallelized CE Health.** Its ~30 independent BigQuery queries used to run one-after-another (~73s on CE 252/month); they now run concurrently on an 8-worker thread pool, dropping wall-clock to **~11s (~6.6×)**. Results are slotted back into the exact same places, so the rendered `ce_health_report.md` and `.json` are unchanged. **(2) Preview-first two-phase emit.** Behind a new opt-in `--preview-marker` flag, CE Health computes the headline numbers (vitals + Shapley driver ranking) first, writes an early JSON sidecar, and signals `PREVIEW_READY` — so the orchestrator can show you the CE Health diagnosis while the rest of the report finishes in the background. It then rewrites the complete report and signals `FULL_READY`. Standalone CE Health (no flag) is byte-for-byte unchanged. **(3) Faster orchestrator start.** `/ce-rca` launches CE Health in the background, shows the preview as soon as it's ready, and only blocks for the full report right before dispatching the deep dives (which need the complete report as context) — with a safety fallback so a stuck run never hangs. The independent setup steps were also batched into fewer commands.

**Blast radius:** CE Health engine (re-vendored into the bundle) + the `/ce-rca` orchestrator steps + changelog. No change to the renderer, composer, templates, CVR-RCA, perf-audit, or any query — the final `ce_health_report.md` + `.json` are **verified byte-identical** to before (plain and with `--preview-marker`).

---

## [v2.8.1] — 2026-06-10 — CE Health: Driver Diagnosis + Funnel default-open; waterfall full-width fix

**Summary:** Two CE Health tweaks. **(1)** Driver Diagnosis (Shapley) and Funnel now open by default (alongside Vitals + Revenue Trajectory). **(2)** Fixed the revenue waterfall rendering at ~700px with whitespace on the right: it's a genuine bug, not a model error — Plotly draws the chart while it's in a hidden/collapsed container (so `autosize` falls back to a default width) and the section-expand toggle never resized it. The collapse toggle now resizes a section's Plotly charts when it's expanded, so the waterfall spans the full card and any later-expanded chart self-heals.

### Blast radius
- `scripts/render_ce_health.py` only. Verified on ce-243 (shapley/funnel open, width:100%, resize-on-expand present).
- **Noted (follow-up):** `render_ce_health.py` reads inputs from the run-dir root, so re-rendering an *organized* (v2.4.0) run fails — harmless live (render precedes the Organize step) but worth making layout-aware via `compose.py`'s existing `resolve()`.

---

## [v2.8.0] — 2026-06-10 — Hardening: chart-render confirmation + Summary text + render de-rigidifying

**Summary:** A real run surfaced four issues plus a request to make the recent presentation changes scalable rather than one-off rigid. This release is **presentation/robustness only — no engine change**. The two chart issues (truncated CE Health waterfall, missing CVR-RCA 90-day annotations) shared one root cause — non-active tab panes are `display:none` at load, so Plotly draws into a 0-width container — and the composite **already** resizes each pane's charts on tab activation, so no template change was needed. The Summary guide text was de-cleverised, and the CE Health renderer's hardcoded column **positions** and **channel names** were replaced with header-name lookups so it survives column reorders and other markets.

### What changed
- **Chart render in hidden tabs (#3 + #4) — confirmed already handled.** `templates/report.html`'s `activateTab()` resizes every `.js-plotly-plot` in a pane after it becomes visible (`Plotly.Plots.resize`, idempotent, guarded), and runs on every activation path — button click, cross-tab `↗` anchor routing, and the load-time hash handler. So the CE Health waterfall renders full-width and the CVR-RCA 90-day `Post period` + event annotations position the first time each tab is opened. No separate load-time handler to supersede; **the template was left unchanged**.
- **Summary text — `references/summary_guide.md`.** §3 renamed *"Long-term context — is the move real?"* → **"Short-term vs long-term context"** (the "is the move real?" framing dropped from the heading and the reading-flow table; the pre→post Δ + YoY Δ table content/guidance kept). §4 headline callout now instructs a **plain heading** — just *"The Story"* or a one-line factual headline of the move (e.g. "Revenue −28%, traffic-led") — the clever `<h2>The Story — <metaphor>` instruction and example are gone; the What-moved / Why / Action `callout-item`s stay. The hardcoded "flagship TGID 3909" in the examples is now a `<top-TGID>` placeholder so it reads as illustrative.
- **De-rigidified `scripts/render_ce_health.py`** (every existing graceful fallback preserved). Hardcoded column **indices** were replaced with the existing `_col_idx` header-name lookup: the funnel cards locate the current/prior windows by header (not `1, 2`); the L12M linear + YoY-hover parsing builds header→index maps (Month/Revenue/Orders/ROI/TR/CR/AOV; Month/Clicks/CVR/Paid-ROI) instead of fixed `r[1..6]`, omitting any absent column rather than crashing; the channel and lead-time tables locate their name/band + Share columns by header rather than position 0. **Channel rules** were generalised: cross-sell leakage now sums **every** "*Cross-sell" channel (not just Google + Bing); the **highest-share** channel is treated as primary (only flagged "not search-led" when no search channel leads) instead of hardcoding "Google Search"; benchmarked channels keep their norms while unmapped channels degrade silently. Magic thresholds (80% concentration, 8% low-S2O, the near-flat delta band) are now documented, tunable module constants.

### Blast radius
- `ce-rca` only: `references/summary_guide.md` + `scripts/render_ce_health.py`. No template / `compose.py` / engine / sub-skill change; CE Health anchor ids unchanged. Verified on CE 3593 + CE 243.

### Deferred
- A persistent (cross-run) CE-context store; perf-audit consuming `user_context.md` (carried from v2.7.0).

---

## [v2.7.0] — 2026-06-09 — Wave C: CE context capture → structured Historical Context (per-run)

**Summary:** Refines *what* CE context the Step 1 pause captures (answering the questions a GM would have about a CE) and *how §8 of the CE Health tab presents it* — entirely **per-run** (no persistent store), **additive**, and **backward-compatible**: a bare-"continue" run produces a byte-identical report. The richest source wins — an MMP doc is mined for CE overview, hypotheses, constraints, and known failure modes, so the analyst types almost nothing.

### What changed
- **Step 1 prompt inlined.** The optional-input prompt (MMP doc · hunch · known events · constraints · known failure modes · where-to-look) is now written verbatim into `SKILL.md`, and the old `references/input_guide.md` is **deleted** — one less file to open, the prompt is where you read it.
- **8-slot `user_context.md`.** The captured-context template expands to **About this CE · Focus / direction · Hypothesis priors · Known events · Constraints · Known failure modes · Important links · Sources** (only slots with content are written). Step 2 derives a **`slack_probes`** array from the Constraints + Known-failure-modes slots and writes it into `orchestration.json` (omitted when empty).
- **MMP-doc extraction enriched.** The context-ingestion sub-agent now pulls **About-this-CE overview + Hypothesis priors + Constraints + Known failure modes + Important links** from a doc (previously priors/events only). The ad-hoc-Sheet data-lens path is unchanged.
- **CVR-RCA Slack agent — probe-driven standing-context search (the one cross-skill touch).** The Slack sub-agent reads `slack_probes` and, for each, runs a CE-scoped `"{ce_name}" AND <probe>` query over a **~90-day standing lookback from `post_end`** (and reads user-pasted thread links directly), writing a new **"Standing context — known-issue checks"** bucket — each probe reported found-with-links or none-found. With no `slack_probes`, the probe search is skipped and the agent behaves exactly as before (the three window-tied searches are unchanged).
- **Structured §8.** The CE Health tab's Historical Context block now **splits `user_context.md` by its slot headings** and renders each as its own labelled sub-block (About this CE · Constraints · Known failure modes · Analyst priors & focus · Known events · Important links) — **Constraints** as warning chips, **Important links** as a small `link · what-it-gives` table. The Slack-signals embed (now carrying the standing-context bucket), the synthesised Historical-trajectory narrative, and the Past-RCAs index are all kept. Any missing slot is omitted; a file with no recognizable slots falls back to the verbatim embed; a bare-continue run is byte-identical.

### Blast radius
- `ce-rca` (`SKILL.md`, `references/context_ingest_guide.md`, `scripts/render_ce_health.py`) **+** one CVR-RCA sub-skill touch (`references/slack_context_guide.md`, edited in the canonical CVR source and re-vendored via `scripts/vendor.sh`). No `compose.py` / template / CE-Health-engine / perf-audit change; CE Health anchor ids unchanged.

### Deferred
- A persistent (cross-run) CE-context store; perf-audit consuming `user_context.md` the same way (owner hand-off).

---

## [v2.6.0] — 2026-06-09 — CE Health Wave B: new data (multi-year, vendor, funnel-by-dimension, MoM TGIDs)

**Summary:** Wave A reorganised CE Health on the data it already had; **Wave B adds the data it was missing** — multi-year trajectory, a vendor breakdown, funnel cuts by channel/language, and correct month-over-month TGID economics. Engine work lives in `ce-health-skill-main` (re-vendored into the bundle); the renderer presents it.

### What changed
- **Multi-year trajectory + CVR.** Monthly lookback extended 13 → 36 months, plus a new monthly **CVR** series (CVR-RCA's definition). The Revenue Trajectory section gains a **Predicted-Revenue × CVR YoY pivot**; a `history_months` / `has_ly` flag drives a compact "(new)" treatment for young CEs.
- **Vendor Breakdown (new section).** Per-vendor revenue, share, orders, AOV, CR, take rate + **fulfilment type** — the supply/sales landscape. Uses Omni's measure definitions (`amount_revenue_usd`; TR = rev/completed-gross; CR = completed/gross); since vendor is booking-grain, each order is attributed to its **primary booking's vendor** to avoid fan-out double-counting.
- **Funnel by dimension.** The Funnel section gains a **"Break funnel down by"** dropdown — Landing page (existing) plus new **Channel** and **Language** cuts (LP2S/S2C/C2O/CVR per value).
- **TGID corrections.** Every TGID delta is now **MoM (pre/post)**, not YoY — fixing the unlabeled, confusing "+142%". **RPC** is redefined to **S2O × AOV × TR** (interim per-select-view proxy). Experience names are emitted **untruncated** (full name on hover). Revenue is labelled **Predicted Revenue** (headline) vs **Actual Revenue** (Driver Diagnosis).
- **Renderer hardening.** `section()`'s header match is now single-line, so same-prefix sections (e.g. "Funnel" vs "Funnel by Language") can't collide. New display order inserts **Vendor Breakdown at position 7** (Lead Time / Historical / Countries → 8/9/10).

### Blast radius
- `ce-health-skill-main` engine (`ce_health.py` + `engine/sources/bq.py`), re-vendored via `scripts/vendor.sh`, **+** `ce-rca/scripts/render_ce_health.py`. No `compose.py` / template / other-sub-skill change. Verified end-to-end on CE 243 + CE 3593 through the **vendored** engine.

### Deferred
- Exact RPC formula (interim S2O×AOV×TR in place); funnel **platform** + **page-type** cuts; the historical-context per-CE memory subsystem (Wave C).

---

## [v2.5.4] — 2026-06-09 — CE Health tab: Driver Diagnosis to position 3 + waterfall un-truncated

**Summary:** Two presentation tweaks. **(1)** The Shapley **Driver Diagnosis** moves up to **position 3** (right after Revenue Trajectory) so "what drove revenue" reads early — new order: CE Vitals → Revenue Trajectory → Driver Diagnosis → Channel Breakdown → Funnel → Top TGIDs → Lead Time → Historical → Customer Countries (titles renumbered; anchor ids unchanged, so all `↗` links still work). **(2)** The revenue **waterfall was clipping on the right** — the first/last x-ticks are shortened to **Pre / Post** (dates stay in the chart subtitle) and the margins widened, so the last bar's label and the x-axis labels render fully.

### Blast radius
- `scripts/render_ce_health.py` only — no compose/template/sub-skill/engine change. Verified on ce-243 + ce-3593.

---

## [v2.5.3] — 2026-06-09 — CE Health tab: reverted the non-functional TGID metric selector

**Summary:** Reverted **only** the TGID "metric selector" feature (one of the four v2.5.2 refinements) from `scripts/render_ce_health.py`. It rendered the column checkboxes unchecked and the show/hide toggle didn't work, so it's been removed and **parked for a later wave**. **All other CE Health table changes are retained** — nothing else was touched.

### What changed
- **Removed the TGID metric selector.** Deleted the `_tgid_metric_selector` function (the checkbox bar above the TGID main table), its `.ceh-msel` CSS, and its toggle `<script>`, plus the selector wiring in `build_tgid_main`. The supporting `styled_table` additions (`table_id` / `col_data` params, the `#ceh-tgid-main` id, and the `data-col` attributes) were also removed cleanly since nothing else used them — no inert leftovers.

### Retained (unchanged)
- Section titles 1..9 in display order (Vitals = "1."); the derived **S2O = S2C × C2O** colour-scaled column inside the Funnel Metrics group; the **CR<80% red** highlight; blue group dividers; grouped header bands; sticky/frozen identity columns; landing-page URL ellipsis + hover; collapsible sections; all Plotly charts.

### Validation
- Re-rendered + recomposed ce-243 and ce-3593 into `report_v2.html`. Confirmed: `ast.parse` clean; **no `COLUMNS`/`Columns` checkbox bar, no `.ceh-msel`, no `_tgid_metric_selector`, no `ceh-tgid-main`/`data-col` residue** in the output; the TGID table still has the S2O colour-scaled column, the CR<80% red rule, blue dividers, grouped headers, and sticky columns; section titles still read 1..9 with Vitals = "1."; landing-URL `title=` hover intact; collapse JS + Plotly charts intact; other tabs unaffected (selector-related diff against the prior reports = 0 lines). Ran both CEs.

### Deferred (later wave)
- A working TGID column show/hide control — parked until the toggle behaviour can be implemented correctly.

---

## [v2.5.2] — 2026-06-09 — CE Health tab: four presentation refinements

**Summary:** A second small polish pass on the CE Health tab — four targeted, presentation-only refinements, all in `scripts/render_ce_health.py`. **No `compose.py` / template / shared-`visual_kit` / sub-skill / engine change.**

### What changed
1. **Section titles renumbered to display order.** The tab was reordered in Wave A, but the section headers still showed CE Health's original numbers (so the reader saw "2." at the top, then "3", "4", "6", "9", "8", "7", "11"). The visible numbers now run a clean **1..9 in the order the sections actually appear** — CE Vitals = "1.", then Revenue Trajectory, Channels, Funnel, Top TGIDs, Lead Time Cohorts, Historical Context, Driver Diagnosis, Customer Countries. The underlying anchor ids are untouched, so every cross-tab "↗" jump still lands correctly.
2. **A derived S2O column in the TGID table.** S2O isn't in the source data, so it's computed per row as **S2C × C2O** and shown inside the Funnel Metrics group with the same green→amber→red colour scale already used for S2C and C2O. A note flags that this is a presentation approximation pending an exact engine figure (Wave B). The existing "CR below 80% → red" highlight still works.
3. **A column selector for the TGID table.** A compact checkbox bar above the table lets the reader hide/show individual metric columns (the TGID and Experience identity columns stay frozen). Everything starts visible; toggling is instant and doesn't disturb the collapsible sections, frozen columns, grouped header bands, or dividers.
4. **Landing-page URLs truncate with hover.** Long landing-page URLs now show with an ellipsis but reveal the full URL on hover. (This works because landing URLs are complete in the source — unlike experience names, which are truncated upstream and left for a later engine fix.)

### Validation
- Re-rendered + recomposed ce-243 and ce-3593 into `report_v2.html`. Confirmed: parses clean; section titles read 1..9 in display order with CE Vitals = "1." and the anchor-id set byte-identical to before; the TGID table has an S2O column inside Funnel Metrics with a colour scale; the CR<80% red rule is intact; the all-checked column selector renders above the TGID table and its toggle script is syntactically valid (`node --check`); landing-URL cells carry hover titles; collapsible sections, frozen columns, dividers, and grouped headers all intact; all Plotly charts present; other tabs unaffected (non-CE-Health source artifacts byte-identical).
- **Not attempted (left for Wave B):** experience-name full-text-on-hover — the name is truncated in the CE Health source itself (a literal "…"), so the renderer cannot recover it.

---

## [v2.5.1] — 2026-06-09 — CE Health tab: seven presentation refinements

**Summary:** A follow-up polish pass on the CE Health tab requested after Wave A — seven targeted, presentation-only refinements, all in `scripts/render_ce_health.py`. **No `compose.py` / template / shared-`visual_kit` / sub-skill / engine change.**

### What changed
1. **Primary driver from the Shapley, not the largest vitals Δ.** The renderer used to label the metric with the biggest change as the "primary mover", which kept flagging *Revenue* (the outcome, not a cause). It now reads the §7 six-factor Shapley decomposition — computed once and shared with the §7 waterfall, so no extra query — and names the factor with the largest contribution. A "Primary driver (Shapley): {factor} ({±$})" note appears under the vitals comparison; if that factor is one of AOV / Take Rate / Completion / Orders, that row is also bolded. Traffic and CVR (which have no vitals row) show the note only. Revenue is never auto-bolded. If the supporting query fails, the note is simply omitted (no guessing).
2. **Collapsible section headers** now read as real, clickable headers — larger bold title, bigger chevron, vertical padding, a subtle hover highlight, and a light divider.
3. **Cryptic "step down" funnel flag** replaced with a plain "↓ X.Xpp vs prior", shown only when a funnel stage is materially below the prior period.
4. **Funnel cards** relabelled to the standard shorthand **LP2S / S2C / C2O** (the LP Users volume card is unchanged).
5. **TGID Experience names** truncate with an ellipsis but show the full name on hover.
6. **"new" / "—" cell clutter cleaned up.** A trailing "—" ("no prior") is dropped to show just the value; a trailing "new" becomes a small muted badge instead of inline text. Normal up/down deltas still render as the two-line coloured cell.
7. **Window-agnostic period label.** The change badges hardcoded "MoM", which is wrong for a custom date window. The label is now derived from the run's window type — "MoM" for a calendar month, "vs prior" otherwise — and used on the vitals cards, funnel cards, and the vitals note.

### Validation
- Re-rendered + recomposed ce-243 and ce-3593 (both custom-window runs, both with a new experience) into `report_v2.html`. Confirmed: parses clean; Shapley primary-driver note present (ce-243 → "Orders / User" bolds the Orders row; ce-3593 → "Traffic" note-only); Revenue never auto-bolded; headers larger/clickable; no "step down" text; LP2S/S2C/C2O cards; experience cells carry hover titles; zero "K new" / "% —" literals; **rendered deltas read "vs prior" — no "MoM" on either custom-window run**; all Plotly charts intact; other tabs unaffected.

---

## [v2.5.0] — 2026-06-09 — CE Health revamp, Wave A (presentation-only)

**Summary:** BGMs reading the CE Health tab wanted it reorganised around a CE's *contours* — vitals → revenue trajectory → channels → funnel → supply/sales landscape — and asked for collapsible sections so a long tab is navigable. Wave A delivers everything achievable **on the data CE Health already produces**, entirely in the renderer (`scripts/render_ce_health.py` + fragment-scoped CSS/JS). **No engine, no new BigQuery queries, no `compose.py` / template / shared-`visual_kit` / sub-skill change.**

### What changed
- **Collapsible sections (central, via `block()`).** Every section now has a clickable header (a `<button>`, so the cross-tab anchor router never intercepts it) with a chevron; the body collapses/expands. A small fragment-scoped script — scoped to `#tab-cehealth` — toggles on header click and **auto-expands a section when a link targets it** (e.g. a `↗` from the Summary tab) on both click and page-load, since the template's router otherwise swallows `:target`. **Vitals and Revenue-trajectory open by default; everything else starts collapsed.**
- **Page reorder.** Vitals → Revenue trajectory → Channels → Funnel → TGID → Lead-time → Historical → Driver diagnosis → Customer countries.
- **Vitals.** Cards reordered to lead with Revenue (Revenue · Orders · AOV · Take Rate · Completion · ROI); the comparison table marks the metric that moved most as the "primary mover".
- **Revenue trajectory** moved up, and the monthly revenue chart now shows Revenue, Orders, ROI, TR, CR and AOV together on hover.
- **Channels.** Revenue and Share moved to the left (current state first), automatic benchmark flags on Share (Google Search should lead at ~50%; PMax/Bing ~10%; Organic ~5%; combined cross-sell over 10% flags keyword leakage), and a 2–3 line plain-English summary that stays visible while the section is collapsed.
- **Funnel.** Four KPI cards (LP→Select, Select→Cart, Cart→Order, LP Users, with month-over-month change) over the year-over-year detail table; the Landing Pages table is folded in as a funnel lens; the worst-moving step is flagged.
- **TGID.** One main table with blue dividers between the Order-Metrics and Funnel-Metrics groups (RPC moved into Funnel), lead-time-bucket columns split into a separate "TGID × Lead-time mix" table, the ~80%-of-revenue concentration highlighted green, a Concentrated/Normal/Fragmented classification label, low-completion and conversion-rate conditional shading, and a high-traffic-low-conversion flag.
- **Lead-time** cohorts kept beside the TGID block with a one-line callout on the dominant booking window (e.g. long-lead skew).

### Decisions
- **Presentation-only and rule-based.** Every summary/flag is deterministic Python on data already on disk — no new queries, no LLM text. Summaries are shown only for Channels and Lead-time (per stakeholder ask); all other sections are collapsible with no summary.
- **Deferred to Waves B/C:** multi-year YoY table, funnel by-dimension/platform, vendor breakdown, exact S2O/RPC from orders, the "+142%" fix, and the historical-context memory subsystem.

### Validation
- Re-rendered + recomposed ce-243 (a growing CE with cross-sell leakage) and ce-3593 (a declining CE) into `report_v2.html`. Programmatic checks confirm collapsible sections, the correct default-open set and page order, blue group dividers, the separate lead-time table, folded-in Landing Pages, funnel KPI cards, channel/lead-time summaries, no leftover raw "$X -Y%" cells, all Plotly charts intact, and **non-CE-Health tabs byte-identical** to the prior renderer (apples-to-apples compose).

---

## [v2.4.0] — 2026-06-09 — Structured run folder (report.html at top, everything else in subfolders)

**Summary:** A finished CE-RCA run left ~25 files dumped flat in the run folder — the deliverable (`report.html`) buried among transcripts, JSON stages, fragments, logs, and machine plumbing. Opening the folder, you couldn't tell what mattered. v2.4.0 makes the run folder self-evident: **`report.html` is the only top-level file; everything else is grouped into by-type subfolders.**

### What changed
- **New orchestrator step — "Organize" (SKILL.md Step 4f):** after composing the report, a silent, idempotent tidy moves intermediates into `transcripts/ · tabs/ · reports/ · data/ · logs/`, leaving `report.html` at the top. The CVR-RCA transcript is renamed `transcript.md → transcripts/transcript_cvr_rca.md` so it reads as its owner's. Commands are run-dir-relative and glob-safe (use `find` for `*` patterns).
- **`compose.py` is now layout-aware:** a `resolve()` helper + `_SUBDIR` map resolve every input **subfolder-first, root-fallback** (tab fragments, `meta.json`, and transcript collection). The report composes identically whether the run is organized or flat — **older runs and standalone sub-skill runs are unaffected** (verified A/B: flat vs organized compose produce a byte-identical `report.html`).
- **`logs/_run_log.md` from the start** (Step 0c) so the actively-appended orchestrator log never needs moving.
- **Docs/paths updated:** `references/followup_guide.md` (reads from the subfolders; Follow-ups card appended to `tabs/followups.html`) and `references/composition_rules.md` (documents the layout + layout-aware resolution).

### Decisions
- **Orchestrator owns the layout** — zero edits to CVR-RCA / perf-audit / CE-Health, so their **standalone** behavior is unchanged; their flat outputs are reorganized only inside a CE-RCA run.
- **Backward-compatible** — flat/older run folders still compose correctly (root fallback).
- **Portable** — all logic lives in versioned skill files (relative paths, no per-machine config), so every install produces the identical structure on every run.
- **Blast radius: `ce-rca` master only** — no `templates/` / CSS / sub-skill change.

---

## [v2.3.0] — 2026-06-09 — CE-RCA-level evaluator (maintainer on-demand quality tool)

**Summary:** CVR-RCA already grades its own investigation every run; the CE-RCA orchestrator had no equivalent — nothing scored how well the *whole* RCA came together (right direction, right skills dispatched, faithful cross-tab synthesis, complete coverage, actionable next steps). v2.3.0 adds that rubric. It is a **quality-tracking tool for maintainers**, run **on demand** against any finished run-dir — **deliberately NOT wired into the GM run flow** (GMs never see it, and we don't want to spend ~150K tokens + minutes on every GM run for a record the GM never consumes).

### What changed
- **New `evals/evaluator.md`** — the CE-RCA rubric. 7 orchestration-level themes (Direction & Dispatch · Cross-Tab Synthesis & Corroboration · CE-Level Diagnostic Correctness · Coverage & Completeness · Actionability & Ownership · Report Integrity & Navigability · Evidence Integrity), each 1–5 → **/35**, with grounded failure-mode tags (`MISSING_INSTRUCTION`/`AMBIGUOUS_INSTRUCTION`/`EXEC_ERROR`/`DATA_LIMIT`) and a meta-review note. It scores the **orchestration seams**, not any sub-skill's internal investigation (each self-evaluates).
- **On-demand usage** — a maintainer spawns a dedicated evaluation sub-agent against any finished run-dir; it reads only on-disk artifacts (no live context needed) and writes `<run_dir>/ce_rca_evaluation.md`. `SKILL.md` documents this under "Maintainer tool — on-demand CE-RCA evaluation." The GM run flow is unchanged (Follow-ups stays Step 5).
- **Naming hygiene.** CVR-RCA's bare `evaluation.md` is renamed at Step 4b → **`cvr_rca_evaluation.md`** (orchestrator `mv`, exactly like the existing `report.html → cvr_rca_report.html`), so each eval reads as its owner's and the CE-level eval never collides.

### Decisions
- **Off the GM auto-path** — the eval's value accrues to maintainers from a *sample* of runs, not to GMs on every run; and because it reads only persisted artifacts it can run after the fact, losing nothing by being decoupled.
- **Dedicated sub-agent**, not inline — keeps it self-contained and reusable against any run-dir.
- **Not a tab** — internal artifact only; `compose.py`, `templates/`, `composition_rules.md` untouched.
- **Blast radius: `ce-rca` master only** — no sub-skill change (the CVR eval rename is an orchestrator `mv`).

---

## [v2.2.4] — 2026-06-08 — Install-time BigQuery access check (verify auth, not just `bq`)

**Summary:** The installer checked that `bq` *exists* but not that the user could actually *run a query* — so someone with `bq` installed but no `gcloud` auth (or no `headout-analytics` access) got a clean install and a confusing failure on their first `/ce-rca`. v2.2.4 adds a real 1-row BigQuery smoke query at install time and tells the user exactly how to fix auth if it fails.

### What changed
- **`INSTALL.md`** (Step 1) — after the `bq`/`python3` presence checks, runs `bq query --use_legacy_sql=false --project_id=headout-analytics --format=none 'SELECT 1'`. **`QUERY OK`** → "you're ready"; **`QUERY FAILED`** → install still completes but the user is prominently warned that the skill won't run until they `gcloud auth application-default login` (and have `headout-analytics` access), with the exact remedy. Installer is instructed not to claim "ready" on failure.
- **`VERSION`** → `2.2.4`.

### Notes
- Validated the smoke query is fast and non-interactive: ~6s `QUERY OK` when authed, ~4s `QUERY FAILED` for a bad project (no hang, no prompt — `</dev/null` + `--project_id` avoid bq's interactive init).
- Doc/installer-only; no skill-flow or sub-skill change.

---

## [v2.2.3] — 2026-06-08 — Follow-ups delta colouring made automatic (scalable, not author-dependent)

**Summary:** v2.1.1 asked Claude to hand-class each delta cell in Follow-ups tables — which is fragile: a real run coloured the first table but left a later one (`−0.14pp`) plain, and the "near-flat → plain text" nuance made it look broken. v2.2.3 makes delta colouring **deterministic at compose time** so every table is consistent regardless of what the author tagged.

### What changed
- **`scripts/helpers.py` — new `autocolor_delta_cells()`** — a sign-based pass over `<td>` cells: a value starting with a sign (`−3.13pp`, `+0.6pp`, `-15%`, `+$111.3K`, `(−$708.8K)`) is coloured **red** (minus) / **green** (plus). Plain counts (`6,447`), levels (`21.6%`), and `—` placeholders have no sign and stay neutral. **Author intent wins** — a `<td>` already carrying `.neg`/`.pos`/`.delta-flat` is left untouched, so semantic cells a parser can't infer (a *positive* "lost checkouts" count marked `.neg`) are preserved.
- **`scripts/compose.py`** — applies it to the **Follow-ups** `html-fragment` only (scoped by `spec["id"] == "followups"`), right after reading the fragment. No other tab is affected.
- **`references/followup_guide.md`** — the colour rule is relaxed: *don't* hand-class signed deltas (the composer does it, consistently); only hand-class the semantic exceptions (a positive number that's actually bad). The brittle "near-flat → plain" threshold is removed — a small `−0.14pp` is still red by sign.

### Why it matters
The previous approach depended on the LLM remembering to tag every cell on every run → inconsistent across tables. Now it's automatic and uniform, while still letting the author override for loss-type columns. **Blast radius: `ce-rca` master only** — `helpers.py` + one scoped line in `compose.py` + guide; no template / shared CSS / sub-skill change (uses the existing shared `.neg`/`.pos`). Verified: 12-case unit test of the colourer + an integration compose where both a signed-delta table and the previously-plain `−0.14pp` table render coloured, loss columns stay author-red, counts/levels stay neutral, no double-classing, idempotent.

---

## [v2.2.2] — 2026-06-08 — §8 Historical Context: no empty box, flatter layout

**Summary:** Fixes the empty bordered box at the top of CE Health §8 and tidies its layout. After v2.1.2 made `_clean_history_md` strip CE Health's placeholders unconditionally, a CE whose §8 markdown is *only* placeholders (e.g. Antelope Canyon) left an empty `md-content` block still being rendered. §8 now renders each sub-section only when it has real content.

### What changed (`scripts/render_ce_health.py` only)
- **No empty box** — the CE Health §8 markdown block is emitted only when content survives cleaning; the prior-runs / context / Slack sub-sections likewise render only when present. If *nothing* is present (first-ever run, no Slack, no context), §8 shows a single muted line ("No prior RCAs or added context for this CE yet.") instead of empty cards.
- **Flatter headers** — dropped the redundant "User-Provided & Recent Context" parent wrapper; each piece (Analyst context / User data / Recent Slack signals) now carries its own subhead directly. The "what the RCA found → Summary ↗" link shows only when the analyst actually supplied context (not for auto-Slack).
- **Cleaner prior-run headline** — extraction skips title/scaffold lines and shows a blank cell instead of a stark "—" when no headline is found.

### Blast radius
- `render_ce_health.py` only — no `compose.py` / template / sub-skill change. Verified on Antelope Canyon (CE 3593): empty box gone, flat subheads, prior-run row + Slack render.

---

## [v2.2.1] — 2026-06-08 — Post-install onboarding brief

**Summary:** After install, the user now gets a tight, structured "how to use" brief instead of a bare version line — so a first-time growth manager knows what CE-RCA does, how to run it, the three input checkpoints, what they get, and that they can ask follow-ups.

### What changed
- **`INSTALL.md`** (Step 6 summary only) — replaced the terse confirm with a structured onboarding card: **What it does · How to run · What it'll ask you (window → direction → optional context) · What you get (the 5 tabs) · Ask follow-ups after (with the time-window-is-a-new-run caveat) · Stays current automatically.** Doc-only; no flow/script change.
- **`VERSION`** → `2.2.1`.

---

## [v2.2.0] — 2026-06-08 — Public zero-auth distribution (revert token gating)

**Summary:** Reverts the v2.1.0 private-token gating in favour of the simpler **public** model — the repo is made public and install/auto-update go back to zero-auth `curl`/`raw` (no token to mint, save, or rotate). Tighter access control is deferred.

### What changed
- **`SKILL.md`** auto-update — back to the public `raw.githubusercontent.com/.../VERSION` check + public `archive/refs/heads/main.zip` re-download (kept the semver guard so a non-semver/offline body → `unknown` → run installed).
- **`INSTALL.md`** — removed the token-presence check and token-authed download; Step 2 is the public curl-zip again (with the post-download success check retained).
- **`README.md`** — Install section back to the one-paste public `INSTALL.md` URL; removed the "Getting your access token" section.
- **`VERSION`** → `2.2.0`. Repo visibility flipped to **public**.

### Decisions / notes
- **Simplicity over restriction for now** — zero-friction for growth managers; "make it safer later" (token or org-gating) is deferred. The `*.token` / `.ce-rca-token` `.gitignore` lines are left in place harmlessly for whenever access control returns.
- Rollback point: tag **`backup-pre-v2.2.0`** at v2.1.2 (`3391603`); the token-based commit remains at `backup-pre-v2.2.0`'s parent / tag `backup-pre-v2.1.0` if ever needed again.

---

## [v2.1.2] — 2026-06-08 — Colour-coded deltas across all CE Health tables + §8 prompt removed

**Summary:** Extends the delta-colouring polish to **every** CE Health table (v1.8.2 only did §3 + §6) and removes a stray interactive prompt from §8 that doesn't belong in a report.

### What changed
- **`scripts/render_ce_health.py`** — `split_deltas=True` is now applied to the remaining CE Health tables: **§2 Full 4-window comparison, §4 Funnel, §9 Lead Time Cohorts, §10 Landing Pages, §11 Customer Countries** (and the §7 verbatim-fallback table). Their `Δ … (MOM / YoY / LY)` and `pp` columns now render green (up) / red (down) / amber (near-flat, `|Δ|<1pp` or `<5%`) like §3 — consistent colour across the whole tab.
- **Parenthetical-preserving fix** — `_cell_split` previously dropped a trailing parenthetical when colouring a lone delta, so a cell like `+31% (+$32.1K)` lost the `(+$32.1K)`. It now colours the **whole token**, preserving the figure (verified: `-66% (-$708.8K)`, `+62% (+$111.3K)` intact).
- **§8 "Add your context" removed** — CE Health's interactive CLI prompt (`> **Add your context:** …`) was leaking into the rendered §8. `_clean_history_md` now drops it (alongside the existing "None found" placeholders) and runs **unconditionally**, so §8 never shows the prompt. Slack / user context is already surfaced below via the user-context subsection.

### Blast radius
- **`render_ce_health.py` only** — no `compose.py` / template / shared `visual_kit.md` / sub-skill change. The scoped `#tab-cehealth` `.ceh-chg` CSS already existed (v1.8.2). Graceful degradation intact: non-delta cells and unexpected shapes render plainly. Verified on CE 243 + CE 3593 (deltas coloured in §2/§4/§9/§10/§11, parentheticals preserved, no "Add your context").

---

## [v2.1.1] — 2026-06-08 — Colour-coded delta cells in Follow-ups tables

**Summary:** Follow-up answer tables rendered their delta / lost-checkout columns in plain black (e.g. `−3.13pp`, `202 (64%)`), unlike the CE Health tables where declines are red and gains green. v2.1.1 makes Claude colour those cells when it authors a Follow-ups card — matching the rest of the report at zero engine cost.

### What changed
- **`references/followup_guide.md`** — the entry-card table template + a new rule instruct colouring every directional cell: **`.neg`** (red, bold) for declines/losses (negative Δ, "lost checkouts", drops), **`.pos`** (green, bold) for gains, **plain text** for near-flat, plus **`.num`** on numeric cells for right-aligned tabular figures. The sign convention follows the *business outcome direction* (more lost checkouts / falling rate = red).

### Why no code change
- `.neg` / `.pos` / `.num` already live in the shared `visual_kit.md` (unscoped), so they render inside the Follow-ups `.md-table` identically to the CE Health tab. Verified: the classes survive verbatim into the composite and their red/green CSS is present. **No `compose.py` / template / sub-skill change.**

---

## [v2.1.0] — 2026-06-08 — Private-repo distribution via fine-grained read-only token

**Summary:** Keeps the repo **private** while preserving no-GitHub-CLI install + auto-update. Access is gated by a **read-only, repo-scoped fine-grained token** the user mints once and saves to `~/.ce-rca-token`; all downloads/version-checks authenticate with it via the **GitHub API** (which works on private repos, unlike `raw.githubusercontent.com` / the public codeload zip).

### What changed
- **`SKILL.md`** auto-update — version check now uses the **Contents API** with the saved token (`Authorization: Bearer`, `Accept: application/vnd.github.raw`) and a semver guard (401/empty/JSON → `unknown` → run installed). The in-place re-download uses the token-authed **`zipball`** endpoint and **auto-detects** the SHA-suffixed extracted folder via `find`.
- **`INSTALL.md`** — added a required token-presence check (`~/.ce-rca-token`, chmod 600) before install; Step 2 download switched to the token-authed `zipball` + auto-detect dir + a post-download success check with a clear "re-mint the token" failure path.
- **`README.md`** — Install section rewritten to the token bootstrap snippet (`<YOUR_TOKEN>` placeholder → saved to `~/.ce-rca-token` → fetch INSTALL.md via Contents API); new **"Getting your access token"** section (mint a fine-grained PAT: this repo only, Contents: Read-only, expiry) + security notes (read-only, one repo, local-only, never committed, revocable).
- **`.gitignore`** — defensively ignores `*.token` / `.ce-rca-token`.
- **`VERSION`** → `2.1.0`.

### Decisions / notes
- **Token never lives in the repo** — only in the user's pasted bootstrap snippet (shared privately) and their local `~/.ce-rca-token`. The repo references the file, not a value.
- **One token, paste once** — the same `~/.ce-rca-token` is reused by install *and* every auto-update.
- Access control is now **token lifecycle** (rotate/revoke from GitHub settings) — no code change to widen/restrict. Flipping the repo public later would also work (token simply becomes optional).
- Rollback point: tag **`backup-pre-v2.1.0`** at v2.0.0 (`a278083`); deeper rollback still at `backup-pre-v2.0.0` (v1.2.0).

---

## [v2.0.0] — 2026-06-08 — Public bundle distribution + auto-update on every run

**Summary:** Packages CE-RCA for one-paste, no-GitHub-CLI distribution (mirroring CVR-RCA) and makes the bundle **keep itself current automatically** — replacing CVR-RCA's minimum-version *nudge* with a true always-latest *self-update*. Also the first push that ships the full self-contained bundle (the vendored `skills/` tree + all accumulated reference/scripts work) to the repo.

### What changed
- **`SKILL.md`** — new **"Stay on the latest version"** step in *Before you begin* (runs before Step 0, no Step-0 renumber): fetches the published `VERSION` (`raw.githubusercontent…/main/VERSION`, 3s timeout), semver-compares via `python3`, and if the local bundle is behind, **re-downloads the latest in place, announces one line, and re-reads the fresh SKILL.md**. Offline / unreachable → proceeds on the installed bundle.
- **Always-latest, no gate** — **`MIN_VERSION` removed**; there is no minimum-version stop. The only check is "is a newer version published?" → auto-upgrade.
- **`VERSION`** → `2.0.0`.
- **`README.md`** — corrected the stale "companions installed separately" section to the **bundled** model; added an **Install** section (one-paste raw `INSTALL.md` URL) and the auto-update note.
- **`INSTALL.md`** — added the "stays up to date automatically" note to the completion summary (install flow itself unchanged: public curl-zip → `~/.ce-rca`).
- **`.gitignore`** — excludes `thoughts/` (internal planning, not for distribution).
- **`scripts/vendor.sh`** — re-run so the shipped `skills/{cvr-rca,perf-audit,ce-health}` are the latest vendored snapshots.

### Decisions / notes
- **No-CLI install** is the design target (growth managers) — zero-auth curl-zip + raw version read. This requires the repo to be **public**; until it's flipped public the version fetch returns `unknown` and the skill simply runs the installed bundle (graceful degradation).
- **"Latest CE-RCA" = latest vendored sub-skills as of the release** — there is no separate per-sub-skill version check; one bundle version governs everything (simpler than CVR-RCA's companion model).
- Rollback point preserved as tag **`backup-pre-v2.0.0`** at the prior `main` (v1.2.0).

---

## [v1.9.0] — 2026-06-08 — Transcript tab: markdown-rendered + perf-audit decision tree

**Summary:** The Transcript tab showed each skill's reasoning, but as a raw monospace dump — and perf-audit's was a flat list of per-section verdicts. v1.9.0 (a) renders each transcript as proper **markdown** (styled headings, tables, prose), and (b) turns perf-audit's transcript into a real **decision tree** like CVR-RCA's.

### What changed
- **`scripts/compose.py`** — `build_transcript_tab()` renders each sub-tab via `render_markdown_tab` (heading ids namespaced `tr-<skill>-…`) instead of an HTML-escaped `<pre>`. ASCII tree-maps stay aligned because the skills now **fence** them — the renderer already emits ` ``` ` blocks as verbatim `<pre><code>`.
- **`templates/report.html`** — dropped `.transcript-raw`; added a `.subtab-pane .md-content pre` style (monospace, scroll, chrome) for the fenced trees. No JS change.
- **CVR-RCA (source → v1.29)** — its transcript `## Tree map` is now wrapped in a ` ```text ` fence (so markdown rendering keeps the `├─ │ └─` alignment). Re-vendored.
- **perf-audit (source → v6.3.0)** — Step 6 transcript rewritten into a CVR-RCA-style **fenced tree-map + detail sections** (root verdict → per-lens branches CONFIRMED/RULED OUT → LEAF), not a flat verdict list. Re-vendored.
- **`references/registry.md`** — both sub-skill changes flagged for **upstreaming**.

### Decisions / notes
- **Both sub-skills changed** (not just perf-audit) — markdown rendering flattens an unfenced tree, so CVR-RCA had to fence its tree-map too.
- **Old unfenced transcripts** in pre-existing run folders render with a flattened tree — accepted (historical); new runs are fenced.
- Transcript tab still **always-last**; collection mechanism (glob `transcript_*.md`) unchanged.

---

## [v1.8.2] — 2026-06-08 — Beautified CE Health tables (value+delta cells, grouped headers)

**Summary:** CE Health's data-dense tables crammed a value and its delta into a single cell (e.g. `$195.7K -63%`, `95.8% +3.7pp`), which scanned poorly. v1.8.2 renders those cells as a **bold value with a smaller colour-coded delta beneath** (green up / red down / amber near-flat) and gives the **Top TGIDs** table **grouped header bands** (Revenue · Order Metrics · Funnel Metrics · Lead-time mix), matching the polished CVR-RCA tables.

### What changed
- **`scripts/render_ce_health.py`** — the shared `styled_table()` gains two opt-in flags: `split_deltas` (parse a trailing delta → two-line coloured cell; colour a lone-delta cell) and `groups` (an ordered `(label, span)` grouped header band, drawn only when the spans match the column count). Applied to **§6 Top TGIDs** (deltas split + grouped bands, the two frozen identity columns preserved) and **§3 Channel Breakdown** (Δ columns coloured). The CSS (`.ceh-val` / `.ceh-chg` / `th.ceh-group`) ships as a `<style>` **scoped to `#tab-cehealth`**, emitted with the fragment.

### Decisions
- **In-cell-delta tables only** (§3, §6) get the treatment; the already-columnar Δ-column tables (§2/§9/§10/§11) are left as-is.
- **Grouped bands on the Top TGIDs table only.**
- **Scoped style, not the shared kit** — zero cross-tab/cross-skill bleed, and it survives re-vendoring (`vendor.sh` only syncs `skills/`).

### Blast radius
- `render_ce_health.py` only — no `compose.py` / template / shared `visual_kit.md` / sub-skill change. Graceful degradation: cells without a delta and unexpected column shapes render plainly (no broken band). Verified on CE 243 + CE 3593 (two-line cells + grouped bands render, 0 leftover `value delta` literals, section anchors intact).

---

## [v1.8.1] — 2026-06-08 — Follow-ups tab: beautified + two render bugs fixed

**Summary:** The Step 5 "report-as-playground" Follow-ups tab worked, but a real run (Antelope Canyon) showed it rendering poorly — a backlink that wasn't clickable, a raw SQL block, and a garbled table. Root cause for the first two was the authoring guide, not the engine. v1.8.1 fixes both and **beautifies** the tab to match the rest of the report.

### What was wrong
- **Backlink dead.** The guide's citation example used `(per CVR RCA ↗)(#block-cascade)` — that isn't valid markdown, so the renderer produced no link (the tab-switch JS and the CVR-RCA anchors were fine all along; there was just nothing to click).
- **SQL block as junk.** The entry format embedded a `<details><summary>Query</summary>…` block, but the markdown renderer only passes through HTML comments — so it printed as literal text. It's also unwanted.
- **Fragile/plain tables.** The minimal markdown renderer mangled tightly-packed tables and the tab looked unstyled next to the others.

### What changed
- **The Follow-ups tab is now a styled `html-fragment`** (`followups.html`), authored with the **same visual-kit chrome as the Summary tab**: each Q&A is an `.analysis-block` card — question title, a coloured `.delta-*` tag pill (`from existing data` / `new query` / `cross-tab` + date), the answer, and tables via `.md-table`. Robust rendering, visually consistent, no fragile markdown parser.
- **Backlinks fixed.** Cross-tab citations now use a real `<a class="ref-link" href="#<anchor>">↗</a>` against a documented anchor-id list — so clicking one switches to the target tab and scrolls to the section (the target card glows). Same mechanism the Summary tab uses.
- **SQL block removed.** Even for a `new query` answer, the card shows only the result (prose + table); the `new query` tag pill is the provenance. No SQL in the report.
- **`compose.py`** — the `followups` tab-spec becomes `type: html-fragment`, `source: followups.html` (still conditional, still positioned before the Transcript tab).
- **`references/followup_guide.md`** rewrites the entry format to the HTML card template + a valid anchor-id reference list; **`references/composition_rules.md`** documents the new shape.

### What did not change
- **`ce-rca` master only** — no new CSS (every class already exists in `visual_kit.md`), no `templates/report.html` change, no sub-skill change. Routing, the pivot rule, and the TGID-data caveat are untouched. A run with no promoted follow-ups stays byte-identical.

### Why it matters
The playground is the adoption surface — stakeholders judge it by how the answers *look* in the report. This makes promoted Q&A render as clean, linked, on-brand cards instead of raw text.

---

## [v1.8.0] — 2026-06-08 — Input/context layer v2 (freedom-based ingestion)

**Summary:** The Step 1 pause becomes a real context intake. Instead of free text only, an analyst can point the RCA at what they already know — a focus/hunch, known dates, a GM "MMP" doc, an ad-hoc Google Sheet, a Slack channel — and Claude reads it, infers intent, and folds it through the whole run. Context-frugal and additive: nothing raw bloats the agent's context, and a bare "continue" behaves exactly as before.

### What changed
- **Intake + clickable guide** — Step 1 shows a compact input menu and a link to `references/input_guide.md` (authored once, surfaced as an openable link, **never loaded into context**), plus a one-line echo-back of the parsed intent + what was read, proceeding unless corrected.
- **Context-frugal ingestion sub-agent** (`references/context_ingest_guide.md`) — reads docs/Sheets in its own context and returns a lean distillate; the orchestrator persists it, split by nature: narrative/history → `user_context.md` priors/events (steers at L0); tabular data → a `user_data_<slug>.md` lens (corroborates at Step 2b). Raw content never reaches the orchestrator.
- **Sheets via `scripts/read_sheet.py`** — Sheets API over your existing gcloud auth (ADC), works for private sheets with no key file; Drive MCP CSV export is the fallback. One-time setup documented in INSTALL.
- **Shared across the orchestration** — `orchestration.json` carries the user-data lens + an optional user-named Slack channel (read by CVR-RCA's existing Slack agent — one pass). The Summary tab reads user context + Slack and tags user-provided corroboration.
- **CE Health §8 "Historical Context" finally earns its name** — it was always "None found" (CE Health's filesystem search for past perf-audits/weekly-reviews finds nothing in the packaged bundle). It now carries real institutional memory:
  - a synthesised **"Historical trajectory"** — a new **fire-and-forget CE-history sub-agent** (Step 0e) reads the prior RCAs for this CE *in its own context* and writes a short `ce_history.md` (trend across runs, recurring root causes, what was tried, what's still open). Synthesis happens off the main loop, so your context never bloats with old reports.
  - a deterministic **"Past RCAs for this CE"** index (prior runs matched by `ce_id`, window + headline + link), plus any user-provided + recent Slack context, with a `↗` to the Summary for "what we found against it".
  - The dead "None found" lines are replaced when real content exists; a first-ever run renders §8 as before. `ce_history.md` is designed to later seed hypotheses and growth recommendations (deferred).
- **Provenance + event markers** (companion cvr-rca v1.28.0) — a distinct "(per user-provided … ↗)" citation tag; known-event dates mark the CVR-RCA daily/90-day trend charts (the analysis window is never moved).

### Deferred / noted
- CE Health L12M event marker (monthly axis makes a dated marker coarse — low value).
- perf-audit consuming user context (owned by another team — hand-off).
- Slack + the user-named channel currently depend on CVR-RCA being dispatched (it always is today); elevating Slack to an orchestrator-level lens is future work.

## [v1.7.2] — 2026-06-08 — Beautified Summary tab (scannable, not a wall of text)

**Summary:** The Summary tab became *comprehensive* in v1.7.0, but it read as a wall of text — dense callout prose, long-sentence conclusion bullets, and a plain action list. v1.7.2 is a **presentation pass**: same coverage, but laid out as a report you scan.

### What changed
- **Headline callout** — bulleted and spaced, key numbers rendered as `.delta` pills, and **colour-coded by direction**: red (decline) / green `improve` / blue `neutral`.
- **Per-tab conclusion digests** — the long-sentence bullet lists are now **2-column `.conclusions-table`s** (bold aspect label → one tight conclusion with a delta pill and a `↗`). A `.tag` chip marks Slack-/user-sourced rows. Scan the left rail, read only the rows you want.
- **Recommended next steps** — now render as **action cards** (the same component CVR-RCA uses): priority badge (P1/P2/P3) + owner badge + the action + sizing bullets + `↗`, deduped across CVR-RCA actions and perf-audit Recommended Actions.
- **Visual kit** — a small, clearly-commented **additive** block (`.callout.improve/.neutral`, `.conclusions-table`, `.tag`, and an unscoped `.delta` pill shape) added inside the shared `<style>`. Additive only — no existing class changed, so re-vendoring from CVR-RCA stays mechanical.

### Decisions
- **Form only, not coverage** — the Summary still carries every tab's conclusions in full.
- **Reuse the existing action-card / pill components** rather than invent new ones.
- **Blast radius: `ce-rca` master only** — `summary_guide.md` + the additive visual-kit block; no sub-skill, `compose.py`, or template change.

---

## [v1.7.1] — 2026-06-08 — perf-audit transcript → second Transcript sub-tab

**Summary:** The Transcript tab (v1.6.0) could hold a sub-tab per skill, but only CVR-RCA emitted one. Now **perf-audit** does too — so stakeholders can read the reasoning behind the paid audit, not just its tables.

### What changed
- **`perf-audit` (source repo, v6.1.0 → v6.2.0)** — new **Step 6** writes a lightweight decision log to `transcript_perf_audit.md` (CE + windows, mode + data pulled, one-line verdict per section, headline finding, what was skipped/ruled out — conclusions only). Re-vendored into the bundle via `scripts/vendor.sh`.
- **`scripts/compose.py`** — `TRANSCRIPT_LABELS` maps `transcript_perf_audit.md` → **"Paid Performance Audit"** (matching the main tab; without it the glob would label it "Perf Audit"). The Transcript tab now shows **CVR-RCA** then **Paid Performance Audit** sub-tabs.
- **`references/registry.md`** — ownership note updated: this is a coordinated change in perf-audit's source repo, flagged for **upstreaming** to the owning team.

### Decisions
- **Lightweight decision log**, not verbose step-by-step; **no engine change** (model-authored).
- Change made in perf-audit's **source repo** + re-vendored (never edit the vendored copy).
- The Transcript-tab collection mechanism (m012) is unchanged — it already globs `transcript_<skill>.md`.

---

## [v1.7.0] — 2026-06-08 — Comprehensive standalone Summary tab

**Summary:** The Summary tab used to be a thin orientation page — vitals cards, a short callout, a cross-reference table. Stakeholder feedback: the Summary should let a reader understand the *whole* RCA on its own, and only open another tab for the nuance behind a conclusion. v1.7.0 rebuilds the Summary as a **standalone digest** — it now carries **every tab's conclusions in full**, while the supporting analysis (dimension cuts, detailed tables, charts) stays in the owning tab, one click (`↗`) away.

### What changed
- **`references/summary_guide.md`** — a new operating principle ("conclusions here, analysis in the tabs") and a richer recommended structure: vitals cards → **long-term context table** (pre→post Δ + YoY Δ, "is the move real?") → headline callout (TL;DR) → optional **"What we set out to check"** block (only when the analyst gave context) → **per-tab conclusion digests** (CE Health · CVR-RCA · Paid Perf-audit, each carrying its conclusions in full with `↗` deep-links; corroborating Slack signals folded in) → driver decomposition table → **consolidated Recommended next steps** → cross-reference table **last**.
- **Anchor correctness** — the CE Health cross-tab anchors in the guide were stale; corrected to the deterministic ids the renderer emits, so `↗` links land on the right section instead of the tab top.

### Decisions
- **Comprehensive in coverage, tight in form** — every line a conclusion or implication; bullets and mini-tables, not prose.
- **Actions now belong in the Summary** — one consolidated, deduped next-steps block (the per-action detail still lives in the tabs).
- **Still pure synthesis** — the Summary lifts conclusions + their numbers from the tabs; it never computes or queries.
- **Blast radius: `summary_guide.md` only** — no `compose.py`/template change; the Summary is still embedded verbatim as an `html-fragment`.

### Verification
Re-synthesised CE 243 + CE 3593 into `report_v2.html`: all three per-tab digests present, the consolidated next-steps block present, the cross-reference table last, the user-context block correctly omitted (no `user_context.md`), and 0 dangling `↗` links.

---

## [v1.6.0] — 2026-06-08 — Transcript tab: read what Claude actually did

**Summary:** The composite report showed each skill's polished *output* but never its *reasoning*. v1.6.0 adds a **Transcript** tab — the **always-last** tab — so any stakeholder can read the decision-making behind the numbers: the branches Claude explored, what it ruled out, and why it concluded what it did.

The tab carries **sub-tabs**, one per skill that produced a transcript, each shown **verbatim in monospace** so CVR-RCA's investigation tree-maps stay perfectly aligned. Today that's the **CVR-RCA** transcript; the mechanism is fully scalable — any skill that writes a `transcript_<skill>.md` into the run directory automatically gets its own sub-tab, with no code change.

### What changed
- **`compose.py`** — new `collect_transcripts()` (registry: `transcript.md` → "CVR-RCA"; plus a `transcript_*.md` glob with humanized labels) and `build_transcript_tab()`, appended after the tab loop so the Transcript tab is always last. Conditional: a run with no transcript files is byte-identical to before.
- **`templates/report.html`** — nested-tab CSS (`.subtab-*`), a verbatim `.transcript-raw` monospace block (`white-space:pre`, horizontally scrollable, HTML-escaped), and a **scoped** sub-tab switcher that never disturbs the top-level tabs.
- **`SKILL.md`** — the orchestrator now keeps its own run log in `_run_log.md` instead of `transcript.md`, so CVR-RCA's transcript stays clean for its sub-tab. Documents the `transcript_<skill>.md` contract.
- **`references/composition_rules.md`** — documents the Transcript tab.

### Decisions
- **Verbatim monospace**, not markdown — preserves tree-maps / indentation.
- **No orchestrator sub-tab** — sub-skill transcripts only (the orchestrator's run log stays internal).
- **Blast radius: `ce-rca` master only** — no sub-skill changes.

---

## [v1.5.0] — 2026-06-08 — Output layer: the report becomes a playground

**Summary:** Until now the orchestrator **stopped at compose** — it produced a tabbed HTML report and went quiet. The report was a dead artifact: all the context a run gathers (the funnel `summary.json`, daily `stage*.json`, CVR-RCA's `findings.md`, the CE Health and perf-audit tabs) sat on disk with no way to interrogate it. Stakeholders kept wanting to dig further — re-group TGIDs, split a step by device or geo, ask "why is S2C the primary driver," check whether the paid SIS drop explains the LP2S decline — and each ask meant a fresh manual investigation.

v1.5.0 adds a **Step 5 playground**: the analyst asks follow-up questions **in the same Claude session that ran `/ce-rca`**, and the master answers from the run's existing context wherever it can, runs a small bounded query only where it must, and — **only when the analyst explicitly asks** — promotes the Q&A into a new **Follow-ups & Q&A** tab. The report turns from a one-shot deliverable into a place to keep digging.

### How follow-ups are answered (in order)
1. **Reinterpret** — clarification / "why" questions, from `findings.md` + `transcript.md`. *(no query)*
2. **Re-aggregate from disk** — temporal re-slices (daily rows in `stage3`/`stage7`), segment/channel splits (`summary.json`/`stage1`), and **TGID revenue/traffic clubbing** (CE Health's §6 table in `ce_health_report.json`). Tagged `from existing data`. *(no query)*
3. **Bounded re-query** — cuts that aren't persisted (per-TGID **funnel**, device, geo, language, URL, price) run one small, scoped query off the bundled `q{2,4,5,6}.sql` patterns, within the run's fixed segment + window. Tagged `new query`.
4. **Cross-tab synthesis** — weave CE Health / CVR / perf together with `↗` links. Tagged `cross-tab`.

### Guardrails
- **Explicit promote.** Every answer is given in chat; the report is edited only on the analyst's say-so — keeps it curated and trustworthy.
- **Audited entries.** Each promoted entry carries question · answer · how-answered tag · date · SQL + one-line result (when a query ran) · `↗` citations.
- **The pivot rule.** Any time-window or scope change is **not** a follow-up — it spawns a fresh `/ce-rca` run (linked by a one-line pointer in the Follow-ups tab). No report is ever recomputed in place; every report stays one-window-consistent.
- **Non-destructive.** Promotion appends to `followups.md` and re-runs the (idempotent) composer; the Summary / CE Health / CVR / perf tabs are never touched.

### Changes by file
- **`references/followup_guide.md` (NEW)** — the Step 5 handler spec (routing, pivot rule, promote flow, audited-entry format).
- **`SKILL.md`** — new **Step 5 — Follow-ups (playground)**; reference-table row; Future-hook #5 (playground shipped; durable `/ce-rca-ask` re-entry deferred); changelog m011.
- **`scripts/compose.py`** — one conditional `TAB_SPECS` entry: **Follow-ups & Q&A** (`markdown`, `followups-` anchors), always last. No `followups.md` → no tab.
- **`references/composition_rules.md`** — Follow-ups tab documented in the reading order.

### What did not change
- **`ce-rca` master only** — the handler *reads* CVR-RCA's `q*.sql` patterns; CVR-RCA, perf-audit, and CE Health are untouched. No template/CSS change. A run with no promoted follow-ups is byte-identical to v1.4.0.

### Why it matters
The richest asset a run produces is its gathered context; this lets stakeholders actually use it — ask, get a sourced answer, and (when it's worth keeping) see it captured in the report. That's aimed squarely at adoption: the report becomes a living, interrogable document, not a PDF-shaped dead end.

### Deferred
- Durable `/ce-rca-ask <CE-or-run> "<question>"` re-entry across sessions (v1 is in-session).
- Persisting granular cuts (stage2/4/6) in CVR-RCA so more follow-ups are instant re-aggregations rather than re-queries — re-evaluate once we see which follow-ups are most common.
- Attaching the playground to a standalone CVR-RCA report (composite-first for v1).

---

## [v1.4.0] — 2026-06-05 — Self-contained bundle: one install, zero runtime repair

**Summary:** CE-RCA is now a **self-contained bundle** that runs like CVR-RCA — one thing, in one place, that just works. Previously the four skills were scattered across `~/Documents` (cvr-rca, perf-audit, ce-health-skill-main, ce-rca), and CE Health couldn't even run on its own (it was carved out of the analytics monorepo and still expected that layout). So every `/ce-rca` run began with a wall of pre-flight steps — the master hunting for sub-skills and hand-building an import shim for CE Health before any analysis happened. None of that was RCA logic; it was the master repairing a broken install at runtime, every time.

v1.4.0 moves **all** setup to install/vendor time. The three sub-skills are vendored **inside** the bundle under `skills/` (`skills/cvr-rca/`, `skills/perf-audit/`, `skills/ce-health/`), at fixed paths the master always knows. CE Health is patched once to run standalone (imports its own `engine/`; repo-root fixed to the skill dir) — no per-run shim, runs from any working directory. The master now resolves each sub-skill at its fixed bundle path and **fails fast** ("reinstall the bundle") if something's missing, rather than hunting or improvising.

### Changes by file
- **`skills/` (NEW)** — vendored copies of cvr-rca, perf-audit, ce-health (minus `.git`, `__pycache__`, internal working dirs).
- **`skills/ce-health/ce_health.py`** — 3-line standalone patch: `_repo_root = dirname(abspath(__file__))`; imports from `engine.sources.bq` + `engine.render.audit_skeleton` (was the monorepo `scripts.perf_audit_engine_v6.*` namespace). Upstream CE Health untouched; only the vendored copy is patched.
- **`scripts/vendor.sh` (NEW)** — one-command re-sync: copies each sub-skill from its source into `skills/` and re-applies the CE Health patch (so a re-vendor can't re-break it), then verifies CE Health imports cleanly. Sources configurable via env; perf-audit pinned (another team's skill).
- **`SKILL.md`** — Step 0c fires CE Health from `$SKILL_DIR/skills/ce-health/ce_health.py` directly; Step 2 resolves deep-dives at `$SKILL_DIR/skills/<name>/`. Replaced all path-resolution hunting (env → `~/.x` → sibling → Documents) with fixed bundle paths + fail-fast; explicit "never improvise a shim or hunt in ~/Documents" rule.
- **`references/registry.md`** — dispatch table pins fixed `skills/<name>/` paths + exact invocations; vendoring/update policy documented.
- **`INSTALL.md`** — one-step install (the bundle contains everything); removed the detect-only companion steps (old Steps 5–7); added a bundle-completeness check.

### What did not change
- The RCA logic, the report, the tabs, the composer, the orchestration handshake — packaging/distribution only.
- The standalone skills still live in their own repos for standalone use; the bundle vendors copies. Upstream CE Health is untouched (vendored copy patched; upstream fix tracked as a hand-off).

### Why it matters
A new user can install one bundle and run `/ce-rca <CE>` with zero pre-flight repair — exactly the CVR-RCA experience. The runtime is deterministic (no agent-improvised shims), and updating a vendored sub-skill is one `vendor.sh` run.

### Deferred
- Push the bundle to GitHub for distribution (kept local for now, per the current scope).
- Upstream CE Health packaging fix (so the vendored patch can eventually be dropped).

---

## [v1.3.0] — 2026-06-05 — Beautified CE Health tab (structured re-render)

**Summary:** The CE Health tab used to render as a wall of verbatim markdown tables — visually crude next to the polished CVR-RCA and Summary tabs. It is now re-rendered into the shared visual_kit chrome (metric cards, Plotly charts, styled tables, a Shapley waterfall) while preserving CE Health's content **exactly**: sections 1→11, exact headings, exact order, **all** rows, exact data. This is a deliberate, narrow carve-out of the cardinal rule — a *presentation re-render* of deterministic structured data (every number sourced from CE Health's `.json` + `.md`), not an edit. It mirrors how CVR-RCA already renders its own `summary.json`. The verbatim rule still binds **perf-audit** (freeform prose owned by another team). So the cardinal rule now splits into **verbatim-embed** (perf-audit) vs **structured re-render** (CE Health, CVR-RCA).

**How it's built.** New deterministic renderer `scripts/render_ce_health.py` runs at **Step 4c** (before compose). It reads `ce_health_report.json` + `.md` + `meta.json`, runs **Query 1** via the `bq` CLI — CE-level traffic/converters from `mixpanel_user_page_funnel_progression` (the CE-wide ALL row, lifted from cvr-rca `q1_base.sql`) and booking-revenue components from `combined_entity_stats` (lifted from `ce_health.py:fetch_ce_health`) — and writes `ce_health_tab.html`. Section mapping: §1 Metadata → **header pills** (Step 0d copies the 5 fields into `meta.json`; `build_header` renders them), §2 Vitals → 6 metric cards + the full 4-window table, §5 L12M → 2 Plotly charts (same data as the monthly tables), §6 TGIDs → styled table with the first 2 columns frozen on scroll, §7 Driver Diagnosis → the **one agreed exception**, a corrected canonical **6-factor** booking-revenue Shapley waterfall (CE Health's own 5-factor Shapley is mis-specified — it omits orders-per-converter and double-counts CR×TR; `ce_health.py:522–592`). The 6-factor identity reconstructs revenue exactly, so the Pre→Post bridge reconciles (`unattributable ≈ $0`).

**Failure-safe.** `compose.py`'s CE Health `TAB_SPECS` entry switches to `html-fragment` (embedded verbatim; inline Plotly executes) with a declared **markdown fallback** — if `ce_health_tab.html` is absent (render skipped/errored), the tab falls back to the verbatim markdown render of `ce_health_report.md`, so a failed beautification never costs the tab. If Query 1 fails but the render otherwise succeeds, the renderer keeps the tab and renders CE Health's §7 table verbatim instead of the waterfall.

**No CE Health skill change** (the orchestrator does all beautification), **no new CSS** (visual_kit reused), **no new compose tab-type** (`html-fragment` reused from the Summary).

### Changes by file

- **`scripts/render_ce_health.py`** (NEW) — productionized from the approved CE-243 prototype; `--run-dir` arg, Query 1 via `bq` CLI, canonical 6-factor Shapley, full-fidelity styled tables, bq-failure fallback.
- **`scripts/compose.py`** — CE Health `TAB_SPECS` → `html-fragment` (`ce_health_tab.html`) with a `fallback` to the markdown; `build_tabs` resolves per-spec fallbacks; `build_header` renders the metadata-pills row from `meta.json`.
- **`SKILL.md`** (m006) — Step 0d copies the 5 CE-metadata fields into `meta.json`; new Step 4c render step (non-fatal on failure); cardinal rule amended with the verbatim-embed vs structured-re-render split.
- **`references/composition_rules.md`** — documents the CE Health structured-re-render: inputs + Query 1, the section→component map, the §7 Shapley exception, the `cehealth-<slug>` anchors, the styling-rules reference, and the markdown-fallback contract; `meta.json` example + header description updated for the pills.
- **`VERSION`** → 1.3.0.

---

## [v1.2.0] — 2026-06-03 — User-context input layer (v1): optional free-text steering

**Summary:** The umbrella can now take the analyst's own knowledge into the RCA. At the Step 1 pause (after CE Health's diagnosis), an **optional** prompt invites a focus area, a hunch about where to look, or a known event (deploy / pricing / promo). The free-form reply is parsed into a short, structured `user_context.md`, which the CVR-RCA deep dive consumes at **two points**: L0 (the analyst's priors become **prioritised, falsifiable** branches — opened early, tested, can be ruled out) and Step 2b (corroboration against the data-driven findings, via the existing four-pattern model). It is built to a deliberate **balance** — it drives priority checks and corroboration but **does not narrow** the RCA (the full data-driven scope still runs; the primary driver is whatever the data says), **does not overwhelm** the output (proportional weight — a ruled-out hunch is one line), and **is never silently ignored** (every prior is closed CONFIRMED / RULED OUT / DATA GAP). Skipping is zero-friction — a bare "continue" writes no file and changes nothing, preserving adoption.

User context is deliberately **not** another evidence lens. Slack / perf-audit / CE Health are secondhand evidence held to Step 2b so they can't bias branch selection; user context is the analyst's *intent*, which legitimately directs the investigation — so it is the one input read at L0. The falsifiability guardrail (priors are tested; data decides the leaf) keeps that honest.

**v1 is lean — free-text only.** Attached files, Google Sheets, and user-named Slack channels are captured under a "Deferred inputs" slot with a "not consumed yet (v2)" note so nothing is silently dropped, but they aren't ingested yet.

### Changes by file

- **`SKILL.md`** (m005) — Step 1 pause gains the optional context prompt + the structured `user_context.md` template; `orchestration.json` gains a `user_context` pointer (separate from `context_lenses`); future-hook #3 promoted to v1-shipped. VERSION → 1.2.0.

### Paired change in CVR-RCA (separate repo)

- CVR-RCA v1.27 (c042): dual-consumes `user_context.md` — L0 steering (Signal 0) + Step 2b corroboration; standalone-safe.

### Deferred (v2 / hand-offs)

- Ingest the "Deferred inputs" slot (files → Sheets → Slack channels).
- perf-audit should consume `user_context.md` the same way (owner hand-off).

---

## [v1.1.3] — 2026-06-03 — Composite header completeness: Omni pill + landing-page link from CE Health

**Summary:** Two header elements were silently missing from composites; both now render reliably. **Omni dashboard pill** — Step 0d adds the `dashboards` array unconditionally (it only needs the CE ID), so every composite header carries the Omni link rather than depending on the orchestrator remembering to add it. **Landing-page link** — CE Health now emits the CE's most-visited landing-page URL in its JSON sidecar at `metadata.top_page_url` (derived from the highest-traffic page in its landing-page funnel, mirroring CVR-RCA's Q0), so Step 0d reads it directly and the header's 🔗 link + clickable CE name render **from the start** — before the deep dives, and even when CVR-RCA isn't dispatched. Step 4a is kept as a **fallback** only: if CE Health found no landing-page data but CVR-RCA did, it back-fills `top_page_url` from CVR-RCA's `summary.json` before compose. No `compose.py` change — `build_header` already rendered both when present; the gap was meta.json not being populated.

**Paired change in CE Health (local-only skill, not git-versioned):** `ce_health.py` now derives `top_page_url` from the highest-`l4w_users` row of its landing-page funnel and injects it into `meta`, so it flows into the sidecar's `metadata` block and into the "## 1. CE Metadata" markdown table (new "Landing Page" row). No new BQ query — reuses the landing-page data already fetched.

### Changes by file

- **`SKILL.md`** (m003) — Step 0d reads `top_page_url` from CE Health's sidecar `metadata.top_page_url` (primary); Step 4a reframed as a `summary.json` fallback; `dashboards` array added unconditionally (Omni). Step 4 sub-steps renumbered (4a fallback → 4b rename → 4c compose → 4d report).
- **CE Health `ce_health.py`** (local) — derive + emit `top_page_url`.

---

## [v1.1.2] — 2026-06-03 — Sentra dashboard link deprecated

**Summary:** Sentra is being retired, so the master no longer adds a Sentra link to the composite report header. Step 0d now populates `meta.json`'s `dashboards` array with the **Omni** link only, and `composition_rules.md` (the header chrome description + the `meta.json` example) drops the Sentra entry. `compose.py` already builds the dashboards row generically from whatever's in `meta.json.dashboards`, so no code change was needed there — removing Sentra from the master's instruction is sufficient. The `visual_kit.md` Page-skeleton doc-comment that named the old "Dashboards row — Omni + Sentra" section is updated to the renamed "Dashboards row". Paired with CVR-RCA v1.26 (c041), which trims Sentra on the standalone side.

### Changes by file

- **`SKILL.md`** (m003) — Step 0d meta.json enrichment: `dashboards` array is Omni-only (was Omni + Sentra).
- **`references/composition_rules.md`** — header-chrome line and the `meta.json` example drop the Sentra dashboard entry.
- **`references/visual_kit.md`** — Page-skeleton doc-comment points at the renamed "Dashboards row" section (kept in sync with the canonical cvr-rca copy).

---

## [v1.1.1] — 2026-06-03 — Re-vendor visual_kit (provenance/External-Signals generalisation)

**Summary:** Synced `references/visual_kit.md` from cvr-rca (now at visual_kit c007 / CVR-RCA v1.26). The change generalises the external-context integration section from Slack-only to lens-agnostic and makes the External Signals & Corroboration table the source-agnostic "sources cited" panel — so when a composite's CVR-RCA tab is produced, every external signal it used (Slack, perf-audit, CE Health) is tagged in a table and woven into the narrative. No code change in ce-rca; this is a vendored-doc sync (the VENDORED COPY header is preserved). The compose-time `<style>` extraction is unaffected (the change was prose, not CSS).

---

## [v1.1.0] — 2026-06-03 — Cross-skill RCA: Summary synthesis tab + context manifest

**Summary:** The tabs now talk to each other. v1.0 composed CE Health, CVR-RCA, and perf-audit into side-by-side tabs that sat next to each other without cross-referencing. v1.1 adds the two pieces that make the umbrella genuinely holistic: (1) a **context manifest** so each deep dive reconciles against the others' findings, and (2) a **Summary tab** that weaves everything into one front-page narrative.

**(1) Context manifest.** `orchestration.json` gains a `context_lenses` array (CE Health + perf-audit + Slack). CVR-RCA reads it at its Step 2b "Context reconciliation" (CVR-RCA v1.25) and folds CE Health's CE-level facts into its funnel findings — e.g. it localizes an S2C collapse on TGID 7148 *and* cites CE Health's 30% RPC drop for that same TGID, or steps back to say "the funnel finding is real but AOV was the headline mover per CE Health" when Shapley points elsewhere. The dependency model is a clean DAG: CE Health (upstream) feeds the deep dives; the deep dives reference upstream inline; the Summary (downstream) owns the peer↔peer weave. No circular cross-referencing.

**(2) Summary tab.** New **Step 3 (Synthesise)** fires a pure-synthesis sub-agent (`references/summary_guide.md`) after the deep dives finish. It reads every tab and writes `summary_report.html` — a polished HTML fragment using visual-kit chrome: a 6-card vitals row (Revenue/Traffic/CVR/AOV/Completion/Take Rate from CE Health), a root-cause callout, a **cross-reference table** (Finding · Source ↗ · Corroborated by ↗ · Implication), and per-driver synthesis blocks. Every `↗` deep-links into the owning tab. The Summary is the **first tab** (most readers open it first). Compose renumbered to Step 4.

### Changes by file

- **`SKILL.md`** (m002) — Step 2 writes `context_lenses` into `orchestration.json`; new Step 3 (Synthesise) fires the Summary sub-agent with graceful degradation; compose renumbered to Step 4 with Summary-first reading order; "Cross-skill data flow" section added; future hooks updated (arbiter, perf-audit owner hand-off).
- **`references/summary_guide.md`** (NEW) — the synthesis sub-agent spec: inputs, the pure-synthesis cardinal rule, the five output blocks, cross-tab link mechanics, and the arbiter TODO.
- **`scripts/compose.py`** — Summary added as the first `TAB_SPECS` entry via a new `html-fragment` tab type (embed verbatim, no conversion/extraction).
- **`references/registry.md`** — `context_lenses` manifest documented; Summary pass documented; perf-audit owner hand-off TODO.
- **`references/composition_rules.md`** — Summary-first reading order; the Summary tab spec.
- **`references/visual_kit.md`** — re-vendored from cvr-rca (registers `summary-*` + `cehealth-*` anchor prefixes).

### Paired change in CVR-RCA (separate repo)

- CVR-RCA v1.25 (c039): manifest-driven Step 2b context layer + CE Health as a new reconciliation lens (check #11). This is what lets a CVR-RCA tab cite CE Health.

### Deferred (TODOs)

- **Summary → arbiter:** today pure synthesis (weaves existing findings, never re-queries); a future upgrade fires one tie-break query when two tabs contradict.
- **perf-audit cross-skill enrichment:** perf-audit (owned by another team) should also read the manifest at its own synthesis and cite CE Health / CVR-RCA in its tab. Hand-off to its owner.
- **User context paste:** wire the `user_context.md` slot into the manifest.

---

## [v1.0.0] — 2026-06-03 — Initial release: CE-level RCA umbrella

**Summary:** CE-RCA is a new top-down master skill that gives a C-level reader
one tabbed report for a whole Combined Entity. It runs CE Health first, presents
the diagnosis and asks the user which directions to deep-dive, then fires the
matching sub-skills (CVR-RCA + perf-audit today) in parallel and composes their
outputs into a single tabbed HTML report. Each sub-skill's output appears
**verbatim** — the master is a composer, not an editor. The sub-skills are not
modified (the only cross-skill change is a small `orchestration.json` handshake
in CVR-RCA that prevents perf-audit being fired twice). The composite reuses the
shared `visual_kit.md`, so the umbrella report is visually identical to a
standalone CVR-RCA report.

### What ships

**Orchestrator — `SKILL.md`**
- Step 0: resolve CE + dates, create run dir + `meta.json`, fire CE Health
  (foreground), enrich `meta.json` from CE Health's JSON sidecar.
- Step 1: present the CE Health diagnosis in chat and pause for free-form user
  confirmation (continue with the default deep-dive, or pivot direction).
- Step 2: dispatch matched sub-skills via the registry, after writing the
  `orchestration.json` handshake; spawn them in parallel.
- Step 3: rename CVR-RCA's report, run `compose.py`, write the composite.

**Dispatch — `references/registry.md`**
- Driver → sub-skill table (CVR → cvr-rca, Traffic → perf-audit; AOV /
  Completion / Take Rate reserved for future skills).
- CVR ⇒ also-fire-perf-audit pairing rule.
- The orchestration handshake spec.

**Composition — `references/composition_rules.md` + `scripts/compose.py` + `scripts/helpers.py`**
- `compose.py` builds the tabbed report from run-dir artifacts in fixed reading
  order (CE Health → CVR RCA → Paid Performance Audit), emitting a tab only when
  its source artifact exists.
- Markdown tabs (CE Health, perf-audit) rendered verbatim via a stdlib-only
  markdown→HTML renderer (vendored from cvr-rca, extended with blockquote +
  fenced-code), with namespaced heading anchors (`cehealth-*`, `perfaudit-*`).
- CVR-RCA tab extracted from its standalone `report.html` — the CVR content only
  (`#tab-cvr-rca`, or the `.container` body for single-tab reports), with its
  Plotly chart scripts re-injected so charts render.
- Composite styling extracted from the vendored `visual_kit.md` at build time,
  so a visual_kit sync updates the composite with no template edit.

**Shell — `templates/report.html`**
- Header + dashboards row + sticky left-anchored tab bar + panes + back-to-top +
  tab-switching JS (incl. cross-tab anchor handling), all from visual_kit
  patterns.

**Distribution — `INSTALL.md`, `README.md`**
- Companion installer with steps for CE Health, CVR-RCA (v1.24+), perf-audit.
- Graceful degradation: any uninstalled companion just won't appear as a tab.

### Paired change in CVR-RCA (separate repo)

- CVR-RCA v1.24 (c038): the perf-audit spawn block gains an `orchestration.json`
  delegation check. When the master has pre-fired perf-audit, CVR-RCA skips its
  own spawn and consumes the shared output at Step 2b. Standalone `/cvr-rca`
  runs are unchanged.

### Future hooks (designed-in, deferred)

- User context paste (`user_context.md` slot).
- Cross-skill `↗` references (anchor scheme + tab JS already support it).
- A summary skill synthesising across tabs.
- More dispatch drivers (AOV-RCA, Completion-RCA, Take-Rate-RCA).
