# Composition Rules

How the master assembles the composite report at Step 3. The governing
principle: **the master is a composer, not an editor.** Every sub-skill's output
appears verbatim — nothing is summarized, reordered, restyled, or re-worded.
A future summary skill may synthesize across tabs; the master itself never does.

## The composite is built by `scripts/compose.py`

The master does not hand-write the composite HTML. It runs:

```bash
python3 scripts/compose.py --run-dir <run_dir>
```

`compose.py` reads the artifacts present in `<run_dir>`, builds one tab per
artifact (in the fixed reading order below), and writes `<run_dir>/report.html`.
This keeps composition deterministic and the master's job small.

## Run-folder layout (organized — Step 4f)

After compose, the master's **Organize** step (SKILL.md Step 4f) tidies the run so
**`report.html` is the only top-level file**; everything else is grouped by type:

```
<run_dir>/
  report.html                 ← the deliverable (only top-level file)
  transcripts/                transcript_cvr_rca.md (renamed from transcript.md), transcript_perf_audit.md
  tabs/                       summary_report.html, ce_health_tab.html, cvr_rca_report.html, followups.html
  reports/                    ce_health_report.md, findings.md, perf_audit_report.md, *_evaluation.md, slack_context.md, …
  data/                       summary.json, stage*.json, ce_health_report.json, meta.json, orchestration.json
  logs/                       _run_log.md
```

`compose.py` is **layout-aware**: it resolves each input **subfolder-first, then the
run-dir root** (see `resolve()` + `_SUBDIR`), so it composes identically whether the run
is organized or flat. Older runs and standalone sub-skill runs (which write flat) still
compose unchanged — the reorganization is purely cosmetic and fully backward-compatible.

## Reading order (fixed)

Tabs are emitted in this order, each only if its source artifact exists:

1. **Summary** ← `summary_report.html` (present if the Step 3 synthesis ran)
2. **CE Health** ← `ce_health_report.md` (always present — CE Health always runs)
3. **CVR RCA** ← `cvr_rca_report.html` (present if cvr-rca was dispatched)
4. **Paid Performance Audit** ← `perf_audit_report.md` (present if perf-audit ran)
5. **Follow-ups & Q&A** ← `followups.html` (present only once the analyst has promoted
   at least one Step 5 follow-up; an `html-fragment` tab)
6. **Transcript** ← any `transcript.md` / `transcript_<skill>.md` in the run dir
   (present if ≥1 transcript exists; **always last**)
7. *(future top-level tabs append here — one entry in `compose.py`'s `TAB_SPECS`)*

The Follow-ups tab is the **output layer** (the Step 5 playground). It is conditional
(no promoted follow-ups → no `followups.html` → no tab) and embedded as an
**`html-fragment`** — authored by the master with the same visual-kit chrome as the
Summary tab (each Q&A is an `.analysis-block` card with a `.delta-*` tag pill, optional
`.md-table`, and working `.ref-link` cross-tab `↗` links), **not** markdown-rendered. The
master re-runs `compose.py` after each promoted answer so the tab refreshes; re-composition
is idempotent and never rewrites the other tabs. See `references/followup_guide.md`.

The **Transcript** tab is built by `compose.py` *after* the `TAB_SPECS` loop, so it is
**always the last tab**. It carries **sub-tabs**, one per skill transcript, each
**markdown-rendered** (via `render_markdown_tab`, with heading ids namespaced per sub-tab to
avoid collisions) so headings, tables, and prose are styled. ASCII tree-maps stay pixel-aligned
because the skills **fence them in ` ``` ` blocks**, which the renderer emits as verbatim
`<pre><code>` (CVR-RCA v1.29+ and perf-audit v6.3+ fence their tree-maps; an old *unfenced*
transcript renders with a flattened tree — acceptable for historical runs). Collection is
**registry + glob** (`collect_transcripts()`): CVR-RCA's generic `transcript.md` maps to the **CVR-RCA**
sub-tab by convention, and any `transcript_<skill>.md` a skill writes auto-appears with a
humanized label — no per-skill code. Conditional (no transcript files → no tab). The
orchestrator's own `_run_log.md` is excluded (no `transcript` name) and never shown. Sub-tabs
use `.subtab-*` classes with a scoped switcher, kept distinct from the top-level `.tab-pane`
mechanic so nesting never clobbers the main tabs.

The Summary is first because most readers open it first — it's the front page.
The rest match the C-level mental model: zoom out (is the CE okay?) → zoom in
(where's the funnel break?) → zoom further (is paid dragging?).

## The Summary tab

The Summary is **our** synthesis (authored by the Step 3 sub-agent per
`summary_guide.md`), not a verbatim render of an external skill — so it earns the
full visual-kit chrome: a 6-card vitals row (Revenue / Traffic / CVR / AOV /
Completion / Take Rate, values from CE Health verbatim), a root-cause callout, a
cross-reference table (Finding · Source ↗ · Corroborated by ↗ · Implication), and
per-driver synthesis blocks. It carries `↗` cross-tab links into every other tab.

It is written as a clean HTML **body fragment** (`summary_report.html`), so
`compose.py` embeds it via the **`html-fragment`** tab type — verbatim, no
markdown conversion, no body extraction, no chart-script handling (the Summary
has no charts; it references the tabs' charts via `↗`). It is **pure synthesis**:
it weaves findings the tabs already reached and never computes new numbers.

## The CVR-RCA rename step (master's responsibility)

CVR-RCA writes its standalone report to `<run_dir>/report.html`. The composite
*also* targets `<run_dir>/report.html`. To avoid a same-path read/write and to
keep CVR-RCA's output as a clean source, the master renames CVR-RCA's file
**after the cvr-rca sub-agent finishes and before running compose.py**:

```bash
mv <run_dir>/report.html <run_dir>/cvr_rca_report.html
```

`compose.py` reads `cvr_rca_report.html` and writes the composite to
`report.html`. CVR-RCA's other artifacts (`findings.md`, `transcript.md`,
`summary.json`) are untouched.

## How each tab is rendered

### Markdown tabs (perf-audit, future markdown skills)

`compose.py` converts the markdown to HTML **verbatim** via the renderer in
`helpers.py` (vendored from cvr-rca, extended with blockquote + fenced-code).
The conversion mapping is the one documented in `visual_kit.md → "Perf-audit tab
rendering"`. Fidelity rules — no exceptions:

- Every section preserved with its original heading text.
- Every subsection (h3, h4) preserved — never collapsed into its parent.
- Every table cell, list item, paragraph, blockquote, code block, inline element preserved.
- No claims paraphrased, no numbers re-rounded, no sections reordered or dropped.

Heading IDs are namespaced by tab: perf-audit → `perfaudit-<slug>`. The slug
strips a leading numbered prefix (`5. ` / `4a. `), lowercases, hyphenates. This
keeps anchors collision-free across tabs and lets cross-tab `↗` citations resolve.

### CE Health tab (structured re-render — `ce_health_tab.html`)

CE Health is **not** rendered as verbatim markdown. It emits deterministic
structured data — a `ce_health_report.json` sidecar (vitals / windows /
metadata) plus `ce_health_report.md` (11 sections as GFM tables) — which
`scripts/render_ce_health.py` re-renders into visual_kit chrome (the
"structured re-render" mode of the cardinal rule; same as how CVR-RCA renders
its own `summary.json`). The master runs the renderer at **Step 4c**, before
compose; `compose.py` embeds the resulting `ce_health_tab.html` as an
**`html-fragment`** tab (verbatim — its inline Plotly `<script>`s execute
because the fragment is part of the parsed document).

**Inputs:** `ce_health_report.json` + `ce_health_report.md` + `meta.json`, and
**Query 1** (run via the `bq` CLI by the renderer — same project/location as
CE Health's BigQuery client): CE-level traffic + converters from
`mixpanel_user_page_funnel_progression` (the CE-wide ALL row, lifted from
cvr-rca `q1_base.sql`) and the booking-revenue components
(`count_orders`, `sum_order_value`, `sum_order_value_completed`, `sum_revenue`)
from `combined_entity_stats` (lifted from `ce_health.py:fetch_ce_health`).

**Fidelity contract — exact content, beautification only.** CE Health's sections
1→11, exact headings, exact order, **all** rows, exact data. No summarization, no
row-trimming, no reordering. The section→component map:

| § | CE Health heading | Rendered as |
|---|---|---|
| 1 | CE Metadata | header pills (via `build_header`, from `meta.json` — not in the tab body) |
| 2 | CE Vitals | 6 metric cards (TM / LM / Δ-MoM) + the full 4-window table + a note that the Revenue card is CE Health's **normalised** revenue |
| 3 | Channel Breakdown | styled table, all rows |
| 4 | Funnel | styled table, all rows |
| 5 | L12M Trajectory | 2 Plotly charts (Revenue+Orders; Clicks+Paid-ROI) — same data as the two monthly tables, with a "full tables remain in source" note |
| 6 | Top TGIDs | styled table, all rows, first 2 columns frozen on horizontal scroll |
| 7 | Driver Diagnosis (Shapley) | **the one agreed exception** — a corrected canonical 6-factor booking-revenue waterfall (see below) |
| 8 | Historical Context | rendered faithfully from the markdown (varies per run) |
| 9 | Lead Time Cohorts | styled table, all rows |
| 10 | Landing Pages | styled table, all rows |
| 11 | Customer Countries | styled table, all rows |

**The §7 Shapley exception.** CE Health's own Shapley is mis-specified
(`ce_health.py:522–592` — 5 factors, omits orders-per-converter, and
double-counts CR×TR). The tab replaces it with the canonical **6-factor**
decomposition `revenue = traffic × cvr × orders/converter × aov × completion ×
take_rate` over all 720 permutations, computed on **booking revenue**
(`revenue_actual`) from Query 1. The identity reconstructs revenue exactly, so
the Pre→Post bridge reconciles (`unattributable ≈ $0`). A verdict line names the
drags/lifts and notes the booking-vs-normalised revenue distinction.

**Anchors:** the `cehealth-<slug>` scheme is preserved (`cehealth-vitals`,
`cehealth-channels`, `cehealth-shapley`, `chart-cehealth-l12m-rev`, …) so
cross-tab `↗` links resolve exactly as for the markdown tabs.

**Authored prose** (verdict lines, notes) follows `visual_kit.md → "Styling and
language guidelines (rules 1–7)"` — load-bearing here: rule 4 (seasonal/YoY
framing must be paired with a named data signal + `↗`), rule 5 (preserve jargon:
TGID, RPC, CR/TR), rule 6 (unpack derived metrics in plain English).

**Markdown fallback (failure-safe).** The CE Health `TAB_SPECS` entry declares a
`fallback` to `ce_health_report.md` (markdown). If `ce_health_tab.html` is absent
— the render step was skipped or errored — `compose.py` renders the verbatim
markdown instead, so a failed beautification never costs the tab. If Query 1
fails but the rest of the render succeeds, the renderer keeps the tab and renders
CE Health's §7 table verbatim in place of the waterfall.

### HTML-extract tab (CVR RCA)

CVR-RCA's `report.html` is a full standalone document with its own internal tab
framework (CVR + perf-audit) or a single-tab flat layout. The master shows
perf-audit as its **own peer tab**, so from CVR-RCA's report `compose.py`
extracts **only the CVR content**:

- Inner HTML of `<div id="tab-cvr-rca">` (the 2-tab case), OR
- Inner HTML of `<div class="container">` (the single-tab flat case).

It does **not** pull in CVR-RCA's internal `#tab-perfaudit` pane — that would
duplicate the dedicated Paid Performance Audit tab.

**Charts:** CVR-RCA renders Plotly charts via `<script>` blocks at the end of
`<body>`, outside the tab pane. `compose.py` extracts those Plotly scripts and
re-injects them into the composite before `</body>`, so the CVR-RCA tab's charts
still render. Chart placeholders (`<div id="chart-...">`) inside the extracted
pane content are preserved as-is.

This extraction is verbatim — the CVR-RCA content is moved, not rewritten. Only
the outer tab-bar chrome (which the composite replaces with its own) is dropped.

## Styling — sourced from the vendored visual_kit

`compose.py` pulls the shared `<style>` block out of `references/visual_kit.md`
at build time and injects it into the composite `<head>`. This means a
visual_kit sync (copying the latest from cvr-rca) automatically updates the
composite's styling — no CSS is hand-copied into the template, so there's no
drift between the kit and the umbrella report.

## Header + chrome

The composite header (eyebrow "CE Root Cause Analysis", CE name, pre/post meta
row, dashboards row, **metadata pills**) is built by `compose.py` from
`<run_dir>/meta.json`, which the master writes at Step 0. The dashboards row
(Omni) and back-to-top arrow are inherited from visual_kit chrome. `meta.json`
carries the dashboard URL list so the composite shows the same pill links a
standalone CVR-RCA report would. The **metadata pills** row (Category ·
Subcategory · Evolution · Management · Status) is where CE Health's "## 1. CE
Metadata" section lives in the beautified report — `build_header` renders any of
those five `meta.json` fields that are present as translucent chips; the row is
omitted entirely when none are set.

`meta.json` shape:

```json
{
  "ce_id": 252,
  "combined_entity_name": "Louvre Museum",
  "combined_entity_type": "Museum",
  "market": "France",
  "country": "FR",
  "pre_period": "2026-03-01 to 2026-03-31",
  "post_period": "2026-04-01 to 2026-04-30",
  "post_start": "2026-04-01",
  "post_end": "2026-04-30",
  "top_page_url": "https://www.headout.com/...",
  "combined_entity_category": "Museum",
  "combined_entity_subcategory": "Art Museum",
  "evolution_bucket": "Mature",
  "management_type": "Managed",
  "headout_status": "1. Top 20",
  "dashboards": [
    {"label": "Omni Analytics", "url": "https://..."}
  ],
  "generated_date": "2026-06-03"
}
```

Dashboard URL templates are CE-analytics knowledge — the master fills them the
same way CVR-RCA's `report_structure.md → "Dashboards row"` documents (only the
CE ID is substituted; Omni's date params are constant).

## Cross-tab citations (future hook, designed-in)

The anchor scheme (`cehealth-<slug>`, CVR-RCA's `block-*` / `chart-*`,
`perfaudit-<slug>`) is collision-free across tabs, and the composite's tab JS
already switches tabs when an in-page anchor targets a non-active pane. So when
the cross-skill-reference hook is built later, a citation like
`(per CE Health ↗)` linking to `#cehealth-driver-diagnosis-shapley` will work
with no composition change. Today the master doesn't inject these citations —
that's deferred until each sub-skill's Step 2b is extended to emit them.

## Single-tab degradation

If only CE Health ran (the user declined any deep-dive), the composite still
renders with the tab framework — one button, one pane. The chrome stays
consistent so the artifact still reads as a CE-RCA. (No special-casing to strip
the bar; a one-tab bar is acceptable and simpler.)
