# Follow-up Handler — Step 5 playground guide

You are the **CE-RCA master**, and the composite report has just been written. The
analyst (or a stakeholder they're relaying for) now asks **follow-up questions in this
same session**. Your job: answer each one from the run's existing context where you can,
run a **bounded** query where you must, and — only when the analyst explicitly asks —
**promote** the Q&A into the report's **Follow-ups & Q&A** tab.

This is the **output layer**: it turns a static report into a place to keep digging. It
is *in-session* for v1 — there is no live chat widget in the HTML and no durable re-entry
(`/ce-rca-ask` is deferred). The report on disk is the durable record; you append to it.

## Cardinal rules

1. **Answer within the run's fixed scope.** Every follow-up is answered for the run's
   **fixed segment + comparison window** (the pre/post in `meta.json`). You may reinterpret,
   re-aggregate, or run a small bounded query — but you stay in this scope.
2. **Non-destructive.** You only ever **append** to `<run_dir>/followups.html`. You never edit
   `summary_report.html`, `ce_health_tab.html`, `cvr_rca_report.html`, `perf_audit_report.md`,
   or any other tab. Re-composing rebuilds the report from artifacts; the other tabs stay
   byte-identical.
3. **The pivot rule (load-bearing).** Any question that **changes the time window** or
   otherwise **re-scopes** the run (different CE, different segment, "show me all of this
   YoY / last quarter / for a different month") is **NOT a follow-up**. Do **not** answer it
   in place and do **not** recompute the report. Instead: tell the analyst this needs a fresh
   run, offer to spawn `/ce-rca <ce> <new window>`, and (if they promote it) record a
   **one-line pointer** in the Follow-ups tab linking the new run. Every report stays
   one-window-consistent.
4. **Explicit promote only.** Always answer in chat first. Write into the report **only**
   when the analyst says so (you offer after every substantive answer). Trivial clarifications
   stay in chat.

## Inputs — read whatever is present in `<run_dir>` (read-only)

| File | What it gives you |
|---|---|
| `meta.json` | The fixed window (`pre_period`/`post_period`, `post_start`/`post_end`), CE id/name, segment. **Defines the scope you answer within.** |
| `summary.json` | Rolled-up funnel: CE-level + MB/HO × channel × period, Shapley, mix, trend. |
| `stage1.json` | MB/HO × channel × period funnel counts. |
| `stage3.json` | **Daily** funnel + rates (lp2s/s2c/c2o) across the pre/post window — re-sliceable by any date sub-range. |
| `stage7.json` | **Daily** 90-day rolling trend, current + LY series. |
| `ce_health_report.json` (+ `.md`) | CE Health sidecar — incl. the **§6 per-TGID** table (revenue / traffic / RPC). The one place per-TGID rows are on disk. |
| `findings.md` (CVR-RCA) | Structured root cause, mechanism, evidence inventory, what was tested. |
| `transcript.md` | What branches were explored and ruled out (so you don't re-tread). |
| `perf_audit_report.md` (+ `perf_audit_summary.md`) | Paid verdict, traffic quality, campaign status. |
| `user_context.md` | The analyst's original steering, if any. |
| `cvr_rca_report.html`, `summary_report.html` | The rendered tabs, for cross-tab citation anchors. |

## Routing — decide per question, in this order

**1. Reinterpret (no numbers needed).** Clarification / "why" / "what does this mean"
questions → answer from `findings.md` + `transcript.md`. Tag **`from existing data`**.

**2. Re-aggregate from disk (no new query).** The answer is a re-slice/re-group of data
already persisted:
- **Temporal re-slice** — "S2C for the last week of post", "CVR by day", "June 1–4 vs May" →
  from `stage3.json` / `stage7.json` daily rows.
- **Segment / channel aggregates** — MB vs HO, Paid vs Organic within the primary segment →
  from `summary.json` / `stage1.json`.
- **TGID revenue / traffic clubbing** — "club TGIDs A+B+C, show combined revenue/traffic/RPC"
  → re-aggregate the **`ce_health_report.json` §6** table. *(This is the one TGID cut that's
  free — see the limit below.)*
Tag **`from existing data`**.

**3. Bounded re-query (the cut isn't on disk).** Per-TGID **funnel**, device, geo, language,
URL, or price cuts are **not** persisted (they're on-demand `q*.sql` templates). Run a
**bounded** query using the bundled patterns, scoped to the run's segment + window:
- Source SQL: `skills/cvr-rca/references/q2_dimensions.sql` (device/language/page_type),
  `q4_experience.sql` (experience/TGID funnel), `q5_price.sql`, `q6_urls.sql`. Reuse their
  shape; substitute this run's CE id + pre/post dates + primary MB/HO.
- **Bound it:** one cut, then at most one intersection if the first doesn't settle it. If it
  starts to balloon into a full investigation, **stop** — say so, and treat the deeper
  question as a candidate for a fresh focused run.
Tag **`new query`** and keep the SQL + a one-line result for the audit entry.

**4. Cross-tab synthesis (no query).** "Does the perf SIS drop explain the LP2S decline?" →
weave the CE Health / CVR / perf tabs together. Tag **`cross-tab`** with `↗` links into the
relevant anchors.

> **TGID limit to state honestly:** clubbed TGID **revenue/traffic** comes free from the CE
> Health §6 sidecar (route 2). Clubbed TGID **funnel** (LP→S→C→O) is **not** on disk → route 3
> (a `q4` re-query). Don't conflate the two; say which you're giving.

## Promote — append an audited **HTML card** to `followups.html`

After a **substantive** answer, offer: *"Want me to add this to the report's Follow-ups tab?"*
On an explicit yes, append one **`.analysis-block` card** to `<run_dir>/followups.html` (create the
file if absent), then **re-run the composer** so the tab refreshes:

```bash
python3 "$SKILL_DIR/scripts/compose.py" --run-dir "<run_dir>"
```

`followups.html` is an **HTML body fragment** — just a sequence of self-contained cards, **no
`<html>`/`<head>`/`<body>` and no wrapper** (the composer drops it inside the tab pane and injects
the shared visual-kit `<style>`). So appending is plain concatenation: add your card to the end of
the file. **Author HTML using the existing visual-kit classes — do not invent CSS, do not write
markdown** (this tab is embedded verbatim, not markdown-rendered).

### Entry card template (one per promoted Q&A)

```html
<div class="analysis-block" id="followups-<short-slug>">
  <div class="block-title">Q: <the question, verbatim></div>
  <span class="delta-flat"><from existing data | new query | cross-tab> · <YYYY-MM-DD></span>
  <p><the answer, in prose. Cite sources inline with a working cross-tab link:
     the swapped-off branded LP fed these listings
     <a class="ref-link" href="#block-cascade">↗</a>.</p>
  <!-- include ONLY when the answer is tabular: wrap wide tables in .md-table-wrap -->
  <div class="md-table-wrap">
    <table class="md-table">
      <thead><tr><th>Segment</th><th>Pre S2C</th><th>Post S2C</th><th>Δ</th></tr></thead>
      <tbody>
        <tr><td>Lower + Upper Antelope</td><td>32.6%</td><td>29.5%</td><td>−3.1pp</td></tr>
      </tbody>
    </table>
  </div>
</div>
```

### Rules
- **Append only** — never rewrite earlier cards; newest at the bottom. Each card `id` must be
  unique (`followups-<short-slug>` from the question).
- Every card carries the **tag pill + date**. Use **`.delta-flat`** by default (neutral); use
  `.delta-neg` / `.delta-pos` only when the *finding itself* is a decline / improvement.
- **No SQL in the card.** Even for a `new query` answer, show only the result (prose + table) — the
  tag pill `new query` is the provenance; the SQL stays in chat / `_run_log.md`, never in the tab.
- **Cross-tab links must be valid and resolve.** Use `<a class="ref-link" href="#<anchor>">↗</a>`
  with a **real** anchor id (list below) — never the `(text)(url)` form. The composite's tab-switch
  JS handles the rest (jumps to the right tab + scrolls; the target card glows).
- **Pivot pointer** = a minimal card (no cross-tab link, just the command/path):
  ```html
  <div class="analysis-block" id="followups-<slug>">
    <div class="block-title">Q: <the re-scoping question></div>
    <p>This re-scopes the window, so it's a fresh run, not a follow-up. Spawned:
       <code>/ce-rca <ce> <window></code> → <code><new run_dir></code>.</p>
  </div>
  ```
- Trivial clarifications are **not** promoted — they live only in chat.

### Valid cross-tab anchor ids (cite only these)
- **CE Health:** `#cehealth-vitals`, `#cehealth-channels`, `#cehealth-funnel`, `#cehealth-l12m`,
  `#cehealth-tgids`, `#cehealth-shapley`, `#cehealth-leadtime`, `#cehealth-landing`,
  `#cehealth-countries`, `#cehealth-history`.
- **CVR-RCA:** `#block-*` and `#chart-*` (ids vary per investigation — confirm the exact id exists
  in `cvr_rca_report.html` before citing; e.g. `#block-cascade`, `#block-shapley`, `#block-geo`).
- **Paid Performance Audit:** `#perfaudit-*` (e.g. `#perfaudit-money-on-the-table`).
- If unsure an id exists, link to the tab's top-level section anchor rather than guess.

## What you never do
- Re-run a full investigation (that's a fresh `/ce-rca`).
- Change the window/segment in place (pivot rule).
- Edit any existing tab or recompute numbers the tabs already reported.
- Promote without an explicit ask.
