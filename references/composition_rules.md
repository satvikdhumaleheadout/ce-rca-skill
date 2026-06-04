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

## Reading order (fixed)

Tabs are emitted in this order, each only if its source artifact exists:

1. **Summary** ← `summary_report.html` (present if the Step 3 synthesis ran)
2. **CE Health** ← `ce_health_report.md` (always present — CE Health always runs)
3. **CVR RCA** ← `cvr_rca_report.html` (present if cvr-rca was dispatched)
4. **Paid Performance Audit** ← `perf_audit_report.md` (present if perf-audit ran)
5. *(future tabs append here — one entry in `compose.py`'s `TAB_SPECS`)*

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

### Markdown tabs (CE Health, perf-audit, future markdown skills)

`compose.py` converts the markdown to HTML **verbatim** via the renderer in
`helpers.py` (vendored from cvr-rca, extended with blockquote + fenced-code).
The conversion mapping is the one documented in `visual_kit.md → "Perf-audit tab
rendering"`. Fidelity rules — no exceptions:

- Every section preserved with its original heading text.
- Every subsection (h3, h4) preserved — never collapsed into its parent.
- Every table cell, list item, paragraph, blockquote, code block, inline element preserved.
- No claims paraphrased, no numbers re-rounded, no sections reordered or dropped.

Heading IDs are namespaced by tab: CE Health → `cehealth-<slug>`, perf-audit →
`perfaudit-<slug>`. The slug strips a leading numbered prefix (`5. ` / `4a. `),
lowercases, hyphenates. This keeps anchors collision-free across tabs and lets
cross-tab `↗` citations resolve.

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
row, dashboards row) is built by `compose.py` from `<run_dir>/meta.json`, which
the master writes at Step 0. The dashboards row (Omni) and back-to-top
arrow are inherited from visual_kit chrome. `meta.json` carries the dashboard
URL list so the composite shows the same pill links a standalone CVR-RCA report
would.

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
