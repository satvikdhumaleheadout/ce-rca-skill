# Report Visual Kit

This file is the **report visual kit** — the skill-agnostic primitives any HTML-report-producing skill builds on. CSS, HTML patterns, styling rules, tab framework, ↗ link-to-table affordance, Slack integration patterns, generic anti-patterns.

The skill's own structure file (`report_structure.md` for CVR-RCA, `perf_audit_structure.md` for perf-audit, etc.) describes the section-level layout on top of these primitives. Read this file first, then the structure file for the skill you're writing for.

**What lives here:**
- Styling and language guidelines (rules 1–7)
- External context integration & link-to-table styling (lens-agnostic: Slack, perf-audit, CE Health, future siblings)
- Tabbed report structure (full-width left-anchored tab bar, perf-audit tab rendering, anchor scheme, citation routing, citation phrasings, tab visibility logic)
- Anti-patterns (visual / HTML)
- Visual Spec — Shared `<style>` block (CSS for header, container, section-label, metric cards, callout, action cards, analysis block, verdict line, tables, shapley flex bar, fixed segment banner, ref-link, tab bar, md-content)
- Anchor ID convention
- Page skeleton (header + container)
- Section label
- Metric cards HTML
- Root cause callout HTML (Shape A paragraph + Shape B multi-driver bullet)
- Action card HTML
- Analysis block HTML (general pattern)
- Table with highlight rows
- Plotly chart conventions

**What lives in the skill's structure file (not here):**
- Section 1/2/3 macro-structure
- The skill's "What belongs in Section N" table
- Skill-specific HTML patterns (Mix cascade, Fixed Segment banner, Geo / Non-Geo, Market context, Shapley decomposition, Hypotheses explored — these are all CVR-RCA-specific; perf-audit will define its own)
- Report length calibration for the skill

---

## Styling and language guidelines

These rules apply to every sentence that appears in the HTML output — callouts, verdict lines, subtext paragraphs, and action cards.

**1. No investigation structure labels.**
Path A, Path B, L0, L1, L2, Case A, Case B, Step 1, Step 2 are internal investigation labels. They must not appear in the report. The report presents findings, not the investigation process.

**2. No data-engineering terminology.**
"Data artefact", "extraction artefact", "data quality gap", "pipeline gap" are internal terms leadership will not recognise. If you need to explain synchronized zeros across all variants, describe the observation in plain language:
- ✅ "Availability shows zeros on these dates across all variants — likely a data gap rather than an actual sell-out, as the same pattern appears across all experiences checked."
- ❌ "This is likely an extraction artefact."

**3. No speculative user behavior without a data signal.**
Do not describe what users were thinking, planning, or intending unless there is a data point to ground it — session recordings, a traffic source shift, a lead-time distribution change. Phrases like "high-intent families planning trips" or "students booking spring break" are not findings.
- ✅ "Session recordings show users encountering an empty date picker beyond 7 days — consistent with the 8+ day booking drop."
- ❌ "High-intent families planning Hawaii trips may no longer be converting at the same rate."

**4. External context only when paired with a data signal.**
Seasonal framing, known events, and holidays are permitted when a corresponding data signal exists — e.g., a traffic spike on a specific date, a CVR break that aligns precisely with a holiday weekend. Never use seasonal framing as a catch-all explanation for a drop.
- ✅ "The onset aligns with Easter weekend (Apr 18–20), where the daily chart shows a sharp CVR drop on Apr 18."
- ❌ "The spring season typically brings lower-intent traffic."

**5. Preserve Headout-native jargon — do not paraphrase.**
Keep company-specific vocabulary as it is used internally: WBR (Weekly Business Review), SP (supply partner), GBV (Gross Booking Value), RR vs plan, TGID, TID, VID, CR%, FabriGPT, MB / HO, LP2S / S2C / C2A / A2O / C2O. These terms signal that findings were sourced authentically from the data and Slack threads stakeholders actually use. Paraphrasing them ("the weekly business review", "supply-partner-side reports") softens the signal and reduces trust — a stakeholder cannot tell whether the report quoted the source or interpreted it.
- ✅ "FabriGPT WBR · May 18 shows GBV −20% YoY, 64% RR vs plan."
- ❌ "An internal weekly report from May 18 shows revenue is 20% lower than last year and we're at 64% of plan."

This rule does NOT override rule 1 — investigation-internal labels (Path A/B, Case A/B/C, locus, lost_checkouts_delta) are not Headout-native jargon; they are skill-internal terms and must still be translated to business language in the report.

**6. Plain English for derived metrics.**
Numbers like `structural_delta_cvr` (current Δ minus LY Δ) collapse two comparisons into one figure — the gap matters more than the figure does. When citing one in a callout or verdict, unpack it once: what LY did over the same window, what we did, what the gap means (an improvement vs the seasonal baseline, or a decline that is worse than headline suggests). After the first unpacking in a section, use the shorthand.
- ✅ "Last year over the same window CVR fell 1.07pp; we rose 0.62pp despite that seasonal pressure, so the underlying gain vs the seasonal baseline is +1.69pp."
- ❌ "Structural ΔCVR is +1.69pp after stripping seasonality (LY −1.07pp)."

**7. Prefer the bullet shape when a callout enumerates drivers.**
When a Section 1 callout answer names multiple drivers, headwinds, or mechanisms, use the lead claim + bullet list shape rather than packing them into a paragraph with inline `(1)/(2)/(3)` markers. The bullet shape is the documented alternative — see "Visual Spec → Callout — multi-driver shape." Pick the shape that matches the finding: a single-mechanism callout stays in paragraph form; an enumerated callout uses bullets so the reader can scan the named drivers without parsing prose.

---

## External context integration & link-to-table styling

These rules govern how **any external lens** — Slack, perf-audit, CE Health, and future sibling skills — surfaces in the report, and how the reader navigates between findings and supporting evidence. Slack is the worked example throughout (it was the first lens), but the three-layer model, the four-pattern classification, and the link-to-table affordance are **lens-agnostic**: a perf-audit SIS verdict or a CE Health Shapley fact surfaces through exactly the same machinery as a Slack thread. The per-lens reconciliation logic lives in `SKILL.md → Step 2b → "Context reconciliation (checks #9–#11)"`; this section is the *styling and surfacing* side.

**Provenance, in one line:** any external signal you actually use must appear in two places — woven into the narrative at the point of use (Layers 1/2) **and** as one row in the consolidated External Signals table (Layer 3). Used signals are always attributed; unused ones stay out.

### Three layers of external-context integration

**Layer 1 — Narrative weaving (default, low bar).**
Whenever Slack adds colour, mechanism, or timing detail that sharpens the existing narrative, weave it into the *regular* callout questions and Section 3 verdict subtexts — not only the dedicated Important Context item. So "What drove the improvement?", "What broke?", "What's holding it back?", "When did it begin?", and any analysis block subtext can pull from Slack.

- Citation format inline: `Source · date ↗` — name and date stay visible (signals "this is from Slack"); the arrow is the clickable router to the External Signals block in Section 3 where the full thread link lives.
- **One citation per concept.** If the same Slack thread is the source for three sentences in a paragraph, cite it once at the most natural anchor — don't re-cite the same source line after line.
- When the Slack timeframe matches the report's pre/post, light attribution is sufficient — no need to keep flagging the source after the first attribution in the paragraph.

**Layer 2 — Important Context callout-item (high bar).**
A third or fourth `.callout-item` block in the Section 1 callout reserved for Slack signals that:
- Introduce a metric or timeframe outside the report's primary comparison (YoY when report is pre/post; vs plan; macro context), AND
- Would cause a stakeholder to act differently or prioritise differently than the data alone would suggest.

The bar is high — most RCAs will not have one. Four "decision-changing" tests:
1. Does it change which team should act?
2. Does it change the priority of the action?
3. Does it contradict the obvious interpretation of the metric?
4. Does it introduce a metric or timeframe not in the report's primary comparison?

If none apply, the signal lives only in the Section 3 External Signals block — do not clutter Section 1.

q-label format: `Important context — [short category]`. Category tag is Claude's choice; examples: "different timeframe", "operational change", "market signal", "supplier issue". Position: after the primary narrative items in the callout (third or fourth slot).

Important Context applies to **both** CVR-declined and CVR-improved cases:
- **Decline example:** a CVR drop where Slack/WBR shows the entire market is down 30% reframes the urgency — the action is no longer "fix our funnel" but "we are outperforming the market."
- **Improvement example:** a CVR gain where YoY GBV is −20% reframes a celebration into "we are converting better within a shrunken pool."

**Layer 3 — External Signals & Corroboration block in Section 3 (the provenance table).**
A dedicated `.analysis-block` (id `block-market-context`) — the report's "sources cited" panel. It renders whenever **any** external lens contributed at least one signal you *used* (Pattern A, B, or C). Every used signal gets exactly one row here, regardless of which lens it came from — this is the table half of the provenance contract. Unlike the earlier Slack-only design, **Pattern A corroborations now also get a row** (a used signal is a used signal — provenance applies even when the lens merely confirmed what the data already showed); the inline `(per … ↗)` citation and the table row are complementary, not either/or. See "External signals & corroboration block" in the Section 3 spec below for the full HTML pattern.

### Signal patterns (cross-reference) — applies to every lens

The classification logic lives in `hypothesis.md → "Slack signal classification"` (named for Slack historically, but the four patterns apply identically to perf-audit and CE Health). Four patterns: A (direct corroboration), B (mechanism explanation), C (reframing context), D (testable gap). Each surfaces in the report as follows — *and any signal you act on, A through C, also earns a row in the External Signals table*:

| Pattern | Where it surfaces |
|---|---|
| A — direct corroboration | Inline `(per <source> ↗)` in the relevant block's subtext + **row in External Signals table** + Source column in Hypotheses Explored table |
| B — mechanism explanation | Layer 1 narrative weaving + **row in External Signals table** |
| C — reframing context | Layer 2 Important Context callout-item + **row in External Signals table** |
| D — testable gap | Result of the one-query test becomes a regular finding in Section 3, cited inline `(prompted by <source> ↗)`. The prompting signal also earns an External Signals row so the provenance is visible; don't double-count the *finding* itself there. |

### Timeframe-citation rule

When citing a metric from a Slack source whose timeframe **differs** from the report's pre/post comparison (YoY, vs plan, vs LY, prior quarter, etc.), the report must explicitly name the timeframe in the same sentence:
- ✅ "Year-over-year is a different picture: CE 1223 GBV is −20% vs the same period in 2025 (FabriGPT WBR · May 18 ↗)."
- ❌ "The absolute order count is below LY plan." *(does not name the timeframe; reader cannot reconcile with the report's pre/post finding.)*

When the Slack timeframe **matches** the report's pre/post window, light attribution is sufficient — no need to repeat the timeframe.

### Slack corroboration upgrades evidence on confirmed findings

When Slack confirms a mechanism that has already been CONFIRMED via data — particularly on declines, where the action card is going to a DRI for execution — elevate the citation from a bare `(corroborated ↗)` parenthetical to an inline named source: `(per [Author · date] ↗)`. Naming the source raises stakeholder confidence: it moves a finding from "we measured it" to "we measured it AND the BDM/Supply/Marketing team has independent corroboration." Use this on the verdict subtext of the analysis block where the data-driven finding lives. Do not stack the same citation across multiple subtexts — one elevation per finding.

### When Slack context is unavailable

If `slack_context.md` was not available at write-time — the sub-agent timed out, returned after Step 3 was completed, or hit a permission denial — render a small disclosure card inside the External Signals block. Never silently drop the Slack lens; give the reader a path forward.

```html
<div style="background:#f3f4f6;border-left:4px solid #8892a4;border-radius:0 6px 6px 0;padding:10px 14px;margin-top:16px;font-size:13px;color:#444;">
  <strong>Slack context not included in this run.</strong>
  [One line on why — e.g., "Sub-agent took longer than the wait window; returned ~22 min later." or "#mkt-france read denied by Slack permissions."]
  To enrich this report with the Slack lens, re-run with the Claude Code context extension and request a Slack pass on this CE.
</div>
```

Use this card whenever Slack didn't reach the report, regardless of CVR direction. Remove it when Slack signals are present — the External Signals table is then the disclosure.

### ↗ link-to-table pattern

Every Section 3 analysis block carries an `id` attribute (see "Anchor ID convention" in the Visual Spec). Claims in Sections 1 and 2 — and the Hypotheses Explored "Test run" column in Section 3 — link to the primary supporting block via a small `<a class="ref-link" href="#block-id">↗</a>` icon.

**Where to use ↗ (do):**
- Section 1 callout — after every numeric or named-finding claim cluster, pointing to the primary block that carries the supporting evidence. A claim cluster is "a complete thought," not "every individual number"; aim for one arrow per sentence.
- Section 2 action cards — after the `cause` line, pointing to the block that confirms the cause.
- Section 3 Hypotheses Explored table, "Test run" column — pointing to the block that ran the test.
- Slack source citations everywhere — the arrow in `Source · date ↗` routes to the External Signals block.

**Where NOT to use ↗ (don't):**
- Inside Section 3 verdict lines, subtexts, or any non-Hypothesis table within Section 3. Section 3 *is* the evidence — jumping from one Section 3 block to another is navigation noise.
- After every individual percentage; one arrow per claim cluster is enough.
- As a substitute for prose. The reader should be able to read the sentence and understand the finding without clicking anything; the arrow is a verification affordance.

**Citation format split:**
- Internal navigation: bare `↗` (one character, no text)
- Slack source: `Source · date ↗` (name + date as text, arrow as the link)
- Perf-audit source: `per perf-audit ↗` or `perf-audit named: <event · date> ↗` (see "Tabbed report structure" below for the cross-tab anchor scheme)
- CE Health source: `per CE Health ↗` or `CE Health: <fact> ↗` (e.g. `CE Health: TGID 7148 RPC −30% ↗`) — links to a `#cehealth-*` anchor in the CE Health tab

All use the same `.ref-link` CSS class — visually consistent, semantically distinct by context. When the anchor target lives in a non-default tab (e.g., `#perfaudit-paid-deep-dive`, `#cehealth-driver-diagnosis-shapley`), the JS in the template switches tabs before scrolling; same visual experience for the reader.

---

## Tabbed report structure

The report can hold multiple analyses in one file via a tab framework. Today there are two real tabs: the CVR-RCA itself (always present) and the Paid Performance Audit (present only when the perf-audit sub-agent ran). The framework is **scalable** — a third or fourth tab (e.g., a future experiment-RCA or supply-RCA) is one config entry, not a rewrite.

### When tabs appear

- **No tabs (flat layout):** the spec uses the legacy `{"sections": [...]}` shape, OR `{"tabs": [...]}` with exactly one tab. Used when the cascade fixed on Organic, perf-audit was not installed, or perf-audit returned DATA GAP / timed out.
- **Tabs visible:** the spec uses `{"tabs": [...]}` with **two or more** tabs. The tab bar is sticky under the report banner; the first tab is active on load.

Backward compatibility is absolute — a legacy single-section spec renders byte-identically to v1.13 output.

### HTML pattern — tab bar + tab panes

Claude writes the tab structure inline in the report. Copy this pattern verbatim — tab bar outside `.container`, then both panes inside:

```html
<body>

<!-- Tab bar — outside .container so it stretches full-viewport-width
     and the first button hugs the 40px left edge -->
<div class="tab-bar" role="tablist">
  <button class="tab-button active" data-tab="cvr-rca" role="tab" aria-selected="true">CVR RCA</button>
  <button class="tab-button" data-tab="perfaudit" role="tab" aria-selected="false">Paid Performance Audit</button>
</div>

<div class="container">

  <!-- Tab 1 — CVR RCA (the standard Sections 1, 2, 3 below) -->
  <div class="tab-pane active" id="tab-cvr-rca" role="tabpanel">
    <!-- header, metric_cards, callout, action cards, all Section 3 blocks here -->
  </div>

  <!-- Tab 2 — Paid Performance Audit (only when perf-audit ran successfully) -->
  <div class="tab-pane" id="tab-perfaudit" role="tabpanel">
    <div class="md-content">
      <!-- perf_audit_report.md rendered inline — see "Perf-audit tab rendering" below -->
    </div>
  </div>

</div><!-- /.container -->

<!-- Tab-switching JS at the very end of <body> — see "Tab JS" pattern below -->
</body>
```

For **single-tab / flat** reports (perf-audit didn't fire, returned DATA GAP, or cascade fixed on Organic), **omit the `.tab-bar` and both `.tab-pane` wrappers entirely**. The body becomes a plain `<div class="container">` with the report content inside. No vestigial tab markup, no inert tab bar with one button.

### Perf-audit tab rendering — markdown → HTML verbatim

When the perf-audit tab is emitted, Claude reads `<run_dir>/perf_audit_report.md` and writes its HTML representation directly into the second tab pane. **The perf-audit's own structure is the structure of Tab 2 — verbatim.**

**Fidelity rules — no exceptions:**
- Every section is preserved with its original heading text.
- Every subsection (h3, h4) is preserved — not collapsed into its parent h2.
- Every table cell, list item, paragraph, code block, blockquote, and inline element is preserved verbatim.
- No claims paraphrased, no numbers re-rounded, no sections reordered, no content dropped.
- The perf-audit's structure is the perf-audit's structure — CVR-RCA does not impose its own Section 1/2/3 / callout / action-card chrome on top of it.

Conversion mapping (markdown syntax → HTML tags, content unchanged):

| Markdown | HTML |
|---|---|
| `# Heading` | `<h1 id="perfaudit-<slug>">Heading</h1>` |
| `## Heading` (with optional leading "N. ") | `<h2 id="perfaudit-<slug>">Heading</h2>` (slug strips the leading "N. ") |
| `### Heading` (with optional leading "Na. ") | `<h3 id="perfaudit-<slug>">Heading</h3>` |
| `#### Heading` | `<h4 id="perfaudit-<slug>">Heading</h4>` |
| `**bold**` | `<strong>bold</strong>` |
| `*italic*` or `_italic_` | `<em>italic</em>` |
| `` `code` `` | `<code>code</code>` |
| `- item` / `* item` | `<ul><li>item</li></ul>` |
| `1. item` | `<ol><li>item</li></ol>` |
| `> quote` | `<blockquote>quote</blockquote>` |
| `[label](url)` | `<a href="url">label</a>` |
| `| pipe | table |` (GFM) | `<table class="md-table"><thead>…</thead><tbody>…</tbody></table>` |
| ` ``` fenced code ``` ` | `<pre><code>…</code></pre>` |
| `---` (hr) | `<hr>` |
| Paragraph break | `<p>…</p>` |

**Slug rule for heading IDs:** lowercase the heading text, strip a leading numbered prefix like `1. ` / `4a. ` / `Appendix A — ` (whatever is conventionally there), replace non-alphanumerics with hyphens, collapse consecutive hyphens, prepend `perfaudit-`. So `## 4. Paid Deep Dive — Google Search` becomes `id="perfaudit-paid-deep-dive-google-search"`; `### 4a. Campaign roster, post-consolidation (Apr–May 2026 trailing snapshot)` becomes `id="perfaudit-campaign-roster-post-consolidation-apr-may-2026-trailing-snapshot"`. Stable across re-renders as long as the heading text doesn't change.

**Fallback — when the markdown contains a construct we can't convert faithfully:** if any part of the markdown uses syntax not covered above (e.g., perf-audit-skill adds a new construct in a future version), embed the raw markdown text directly inside a `<pre class="md-raw">` block. Better to show raw markdown text than to paraphrase or omit. The fallback should be rare; the conversion mapping above covers everything perf-audit-skill emits today.

**Wrapper:** the entire converted content sits inside `<div class="md-content">` for typography. See the shared `<style>` block for `.md-content`, `.md-table`, and the new `.md-content pre.md-raw` styling.

### Cross-tab anchor scheme

| Tab | Anchor prefix | Example |
|---|---|---|
| Summary (CE-RCA composite only) | `summary-*` | `#summary-root-cause` |
| CE Health (CE-RCA composite only) | `cehealth-*` | `#cehealth-driver-diagnosis-shapley`, `#cehealth-top-tgids` |
| CVR-RCA (Section 3 blocks) | `block-*` and `chart-*` (no tab prefix) | `#block-cascade`, `#chart-daily-c2o` |
| Paid Performance Audit | `perfaudit-*` | `#perfaudit-paid-deep-dive`, `#perfaudit-coverage-matchmaking` |

The slug generator strips a leading "N. " from numbered headings, so `## 5. Coverage + Matchmaking` becomes `id="perfaudit-coverage-matchmaking"`. Stable across re-renders as long as the heading text is unchanged. The `summary-*` and `cehealth-*` prefixes apply only inside the CE-RCA umbrella composite (where those tabs exist); a standalone CVR-RCA report has only `block-*`/`chart-*` and `perfaudit-*` tabs.

### Citation routing — CVR-RCA → perf-audit tab

When Step 2b check #10 (perf-audit reconciliation) routes a finding into the CVR-RCA tab, the citation includes a `↗` linking to the most relevant perf-audit anchor. Use this routing table:

| Citation context | Anchor target |
|---|---|
| Traffic-quality verdict (SIS / CPC / Paid CVR trends) | `#perfaudit-paid-deep-dive` |
| Campaign pause / dormancy event | `#perfaudit-paid-deep-dive` |
| Cohort coverage / language-geo CVR breakdown | `#perfaudit-coverage-matchmaking` |
| tROAS self-suppression / bidding strategy | `#perfaudit-paid-deep-dive` |
| Competitor surge / auction insights | `#perfaudit-external-dynamics` |
| Funnel comparison from the ads side | `#perfaudit-funnel` (advisory — never cited in primary funnel claims) |
| Generic "see full perf-audit" reference | `#perfaudit-executive-summary` |

### Citation phrasings (four patterns — mirrors Slack)

The four-pattern reconciliation in `SKILL.md → Step 2b check #10` produces citations in these shapes:

| Pattern | Phrasing | Example |
|---|---|---|
| A — direct corroboration | `(per perf-audit ↗)` | "LP2S concentrated on URL set X (per perf-audit ↗)." |
| B — mechanism explanation | `(perf-audit named: <event · date> ↗)` | "(perf-audit named: campaign 'Brand-Search-EN' paused Apr 8 ↗)" |
| C — reframing context | `(traffic quality DEGRADED — per perf-audit ↗)` | "Page-side fix needed AND traffic-quality contributor (per perf-audit ↗)." |
| D — testable gap | Inline `(prompted by perf-audit ↗)` after the data-driven leaf that resulted | "TGID 7148 surge confirmed (prompted by perf-audit ↗)." |

Citation placement follows the same rules as Slack:
- **Allowed:** Section 1 callout subtexts, Section 2 action card cause lines, Section 3 External Signals block, Hypotheses Explored "Test run" column.
- **Not allowed:** Section 3 verdict lines or their subtexts (Section 3 *is* the evidence — internal navigation between Section 3 blocks is noise).

### User-provided source citations

When a finding leans on **user-provided** context (an MMP doc, an ad-hoc Sheet, or
a user-named Slack channel — surfaced via `user_context.md` / a `user_data_*`
lens), cite it with a distinct tag so the reader can tell analyst-supplied from
system-derived evidence:

| Source | Phrasing |
|---|---|
| MMP doc / narrative | `(per user-provided MMP doc ↗)` |
| Ad-hoc data pull | `(corroborated by user Sheet: <name> ↗)` |
| User-named Slack channel | `(per user-flagged #channel · date ↗)` |

Same placement rules as above; a used user-provided signal gets a row in the
External Signals & Corroboration block like any other lens. Never let a
user-provided citation carry a finding the data didn't independently reach.
- **One citation per concept** — same rule as Slack. If the perf-audit verdict supports three sentences in a paragraph, cite it once at the most natural anchor.

### Visual differences from CVR-RCA content

The perf-audit tab uses `.md-content` styling, which inherits the dark-theme look but keeps the markdown structure (h2/h3 hierarchy, GFM tables with `.md-table` class, lists, bold/italic). It deliberately does **not** mimic Section 3's `.analysis-block` cards — the perf-audit report has its own logic and section structure; restyling it would obscure that. The visual cue is intentional: the reader knows they're looking at a different artifact.

### Tab bar placement — full-width, left-anchored

The tab bar renders full-viewport-width and sticky at the top of the viewport, with the first button left-anchored to the 40px content edge (matching the header's content padding). This is **outside** the centered `.container` (max-width 1050px) — the bar stretches the full window so a reader on any monitor size sees the tabs at the page's left edge rather than as a centered island within the content column. The HTML pattern above places the `<div class="tab-bar">` between `<body>` and `<div class="container">` exactly so this layout falls out naturally.

### When the perf-audit tab is conditional / omitted

The CVR-RCA tab is unconditional (always emit). The perf-audit tab is emitted only when:
1. The cascade fixed on Paid (Trigger 1 or Trigger 2 from `SKILL.md → "Perf-audit context — fire and forget"`), AND
2. `perf_audit_report.md` exists in the run directory and has non-empty content, AND
3. The sub-agent verdict was not `DATA GAP: no campaigns` (in which case there is no useful content to show; the verdict still surfaces via the findings.md evidence entry and any Pattern B/C citations)

When any of those fail, write the report as a single-tab flat layout — no `.tab-bar`, no `.tab-pane` wrappers, no tab-switching JS. The report body is just `<div class="container">` with the Sections directly inside.

---

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Root cause callout says "CVR declined due to multiple factors" | Non-committal — GM doesn't know what happened |
| Actions buried after 6 charts | GM has to read through analysis to find what to do |
| Every analysis run appears in the report | Shows the work, not the conclusion |
| "Investigate further" as an action | Not actionable — the investigation just finished |
| DRI is "Product team" with no specific task | Can't be forwarded |
| Analysis block opens with "The following table shows..." | Describes data, not the finding |
| All dimension cuts present when none showed a concentrated signal | Template-driven, not story-driven |
| Shapley visualization in a mix-dominant finding | The steps didn't break — showing it implies they did |
| Table shows rates/shares with no user counts | Stakeholder can't judge if the finding is substantial — a 10pp drop on 30 users is noise |
| Investigation-internal terminology in the report body (Step 1/2/3, Path A/B, Case A/B/C, "locus", "lost_checkouts_delta", "candidate TGIDs") | These are transcript terms — they mean nothing to a GM or stakeholder. Translate: "the three most-affected experiences" not "the Case B candidate TGIDs"; "supply checked and ruled out" not "Step 3 confirmed supply ruled out". |
| Daily inventory time-series rendered as an HTML table | A 27-row × 4-column date table is unreadable at a glance. The daily time-series is always Plotly line charts. The only table in the inventory section is the TID snapshot summary. |
| Standalone analysis block that restates a conclusion already shown in a prior block | If a sub-step breakdown (e.g., C2A/A2O) concludes the same thing as an experience mix table that came just before it, the sub-step block adds no new information. Fold the one new data point into the existing block's subtext paragraph and remove the standalone block. Every block in the report should add something the prior block didn't show. |
| `days_to_first_available_date` presented as the primary supply evidence | It is a single-integer proxy from `product_rankings_features` ("how far out is the first bookable slot?") — collapses real bucketed ticket counts into a yes/no signal. The canonical supply evidence is `inventory_availability` ticket counts per lead-time bucket. The proxy belongs in a corroborating footnote at most, regardless of CVR direction. |
| Tab 2 (perf-audit) wraps perf-audit content in CVR-RCA-style chrome (Section 1/2/3 callouts, action cards, "What drove the improvement / What's holding it back" rephrasings) | The perf-audit-skill is the source of truth for its own structure. Tab 2 is a verbatim markdown→HTML render of `perf_audit_report.md` — every section, every subsection, every table cell, every word preserved. CVR-RCA's job is to display the perf-audit, not to re-format it. If the markdown contains a construct we can't convert, fall back to `<pre class="md-raw">` raw markdown text. Fidelity beats polish. |
| Sub-headings dropped during the perf-audit md→HTML conversion (h3/h4 collapsed into parent h2; section numbering simplified; appendices omitted) | The perf-audit's structure is the perf-audit's structure. Sub-headings like `4a. Campaign roster` and `5c. Money on table (sized)` carry meaning the parent h2 doesn't capture. Conversion is one-to-one with the source markdown — if the `.md` has 22 headings, Tab 2 has 22 headings. |


## Visual Spec — HTML patterns

**Every report is written as self-contained HTML.** There is no render.py and no component library. Copy the shared `<style>` block below into every report's `<head>` and write each section using the HTML patterns below.

### Shared `<style>` block — copy into every report's `<head>`

```html
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f5f6fa;
    color: #1a1a2e;
    line-height: 1.55;
  }

  header {
    background: #1a1a2e;
    color: #fff;
    padding: 28px 40px 24px;
  }
  header .eyebrow {
    font-size: 11px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #8892a4;
    margin-bottom: 6px;
  }
  header h1 { font-size: 24px; font-weight: 700; }
  header .meta { margin-top: 8px; font-size: 13px; color: #b0bec5; }
  header .meta span { margin-right: 20px; }

  /* Dashboards row — optional row below .meta carrying pill-button links to
     external dashboards scoped to the same entity (CE) as the report.
     Chrome lives here; URLs are owned by the consuming skill's structure file
     (e.g., CVR-RCA's report_structure.md "Dashboards row" section). */
  header .dashboards {
    margin-top: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  header .dash-label {
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #8892a4;
    margin-right: 4px;
  }
  header .dash-link {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.14);
    color: #c8cfe0;
    text-decoration: none;
    padding: 4px 12px;
    border-radius: 14px;
    font-size: 12px;
    font-weight: 600;
    transition: background 0.15s, color 0.15s;
  }
  header .dash-link:hover {
    background: rgba(255,255,255,0.16);
    color: #fff;
  }

  .container { max-width: 1050px; margin: 0 auto; padding: 0 24px 60px; }

  .section-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #8892a4;
    margin: 40px 0 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e0e4ef;
  }

  .metric-cards {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }
  @media (max-width: 800px) { .metric-cards { grid-template-columns: repeat(3, 1fr); } }
  .metric-card {
    background: #fff;
    border-radius: 10px;
    padding: 18px 16px 16px;
    border: 1px solid #e8ebf4;
  }
  .metric-card .label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #8892a4;
    margin-bottom: 8px;
  }
  .metric-card .values { display: flex; align-items: baseline; gap: 8px; }
  .metric-card .pre  { font-size: 14px; color: #8892a4; }
  .metric-card .post { font-size: 22px; font-weight: 700; color: #1a1a2e; }
  .metric-card .delta {
    font-size: 12px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 12px;
    margin-top: 6px;
    display: inline-block;
  }
  .delta-neg  { background: #fdecea; color: #c62828; }
  .delta-pos  { background: #e8f5e9; color: #2e7d32; }
  .delta-flat { background: #f3f4f6; color: #555; }

  .callout {
    background: #fff;
    border-left: 4px solid #e53935;
    border-radius: 0 10px 10px 0;
    padding: 24px 28px;
    margin-bottom: 8px;
    border-top: 1px solid #e8ebf4;
    border-right: 1px solid #e8ebf4;
    border-bottom: 1px solid #e8ebf4;
  }
  .callout h2 { font-size: 16px; font-weight: 700; color: #c62828; margin-bottom: 16px; letter-spacing: 0.2px; }
  .callout-item { margin-bottom: 14px; }
  .callout-item:last-child { margin-bottom: 0; }
  .callout-item .q {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #8892a4;
    margin-bottom: 4px;
  }
  .callout-item .a { font-size: 15px; color: #1a1a2e; font-weight: 500; }
  /* Multi-driver shape — lead claim + bullet list inside .callout-item .a
     (see "Visual Spec → Callout HTML patterns → Multi-driver shape") */
  .callout-item .a ul { margin: 8px 0 0 0; padding-left: 18px; }
  .callout-item .a li { margin-bottom: 4px; line-height: 1.5; font-weight: 500; }
  .callout-item .a li strong { color: #1a1a2e; font-weight: 700; }

  .action-card {
    background: #fff;
    border-radius: 10px;
    border: 1px solid #e8ebf4;
    padding: 24px 28px;
    margin-bottom: 16px;
  }
  .action-card .ac-header { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px; }
  .priority-badge {
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 12px;
    white-space: nowrap;
    flex-shrink: 0;
    margin-top: 2px;
  }
  .p1 { background: #fdecea; color: #c62828; }
  .p2 { background: #fff8e1; color: #f57c00; }
  .p3 { background: #e8f5e9; color: #2e7d32; }
  .action-card .cause { font-size: 15px; font-weight: 600; color: #1a1a2e; }
  .action-card .dri-row {
    font-size: 13px;
    color: #555;
    margin-bottom: 16px;
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .dri-badge {
    background: #e8edf7;
    color: #3a4a8a;
    font-weight: 600;
    font-size: 12px;
    padding: 2px 9px;
    border-radius: 8px;
  }
  .action-card ul { padding-left: 18px; font-size: 14px; color: #333; }
  .action-card ul li { margin-bottom: 7px; }

  .analysis-block {
    background: #fff;
    border-radius: 10px;
    border: 1px solid #e8ebf4;
    padding: 24px 28px;
    margin-bottom: 20px;
  }
  .analysis-block .block-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin-bottom: 6px; }

  .verdict-line {
    font-size: 14px;
    font-weight: 600;
    color: #c62828;
    background: #fdecea;
    border-radius: 6px;
    padding: 8px 14px;
    margin-bottom: 18px;
  }
  .verdict-line.neutral { color: #3a4a8a; background: #e8edf7; }

  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th {
    text-align: left;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.7px;
    text-transform: uppercase;
    color: #8892a4;
    padding: 8px 12px;
    border-bottom: 2px solid #e8ebf4;
  }
  td { padding: 9px 12px; border-bottom: 1px solid #f0f2f8; color: #1a1a2e; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f8f9ff; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .neg { color: #c62828; font-weight: 600; }
  .pos { color: #2e7d32; font-weight: 600; }
  .highlight-row td { background: #fff8f8 !important; }

  .shapley-bars { display: flex; gap: 0; border-radius: 8px; overflow: hidden; height: 32px; margin: 16px 0 8px; }
  .shapley-bar { display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: #fff; }
  .shapley-lp2s { background: #6c8ebf; }
  .shapley-s2c  { background: #c62828; }
  .shapley-c2o  { background: #d6a832; }
  .shapley-legend { display: flex; gap: 20px; font-size: 12px; color: #555; }
  .legend-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }

  .ruled-out { font-size: 13px; color: #777; font-style: italic; padding: 6px 0 0; }
  .chart-container { margin-top: 16px; }

  /* ↗ link-to-table affordance — see "↗ link-to-table pattern" above */
  .ref-link { color: #3a4a8a; text-decoration: none; font-size: 12px; font-weight: 700; margin-left: 3px; }
  .ref-link:hover { color: #c62828; }
  html { scroll-behavior: smooth; }
  .analysis-block:target { box-shadow: 0 0 0 3px #ffe082; transition: box-shadow 0.4s; }

  /* Back-to-top floating button — fixed bottom-right, always visible.
     Uses anchor link to <header id="top"> so the existing scroll-behavior:smooth
     handles the scroll without any JS. See Page skeleton for the HTML pattern. */
  .back-to-top {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: rgba(26, 26, 46, 0.85);
    color: #fff;
    text-decoration: none;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 700;
    line-height: 1;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
    z-index: 100;
    transition: background 0.15s, transform 0.15s;
  }
  .back-to-top:hover {
    background: rgba(26, 26, 46, 1);
    transform: translateY(-2px);
  }
  @media print { .back-to-top { display: none; } }

  /* Markdown-sourced tab content (perf-audit tab and any other markdown-rendered tab).
     The perf-audit content sits inside <div class="md-content"> for typography that
     feels native to a polished markdown render — h2/h3 hierarchy, code styling, link
     colors, GFM table styling — without imposing CVR-RCA's .analysis-block chrome
     on top of the perf-audit's own structure. See "Perf-audit tab rendering". */
  .md-content {
    background: #fff;
    border-radius: 10px;
    border: 1px solid #e8ebf4;
    padding: 28px 32px;
    margin: 20px 0;
    line-height: 1.7;
  }
  .md-content h1 { font-size: 22px; font-weight: 800; margin: 24px 0 12px; color: #1a1a2e; }
  .md-content h2 { font-size: 18px; font-weight: 700; margin: 28px 0 10px; color: #1a1a2e; border-bottom: 1px solid #e8ebf4; padding-bottom: 6px; }
  .md-content h3 { font-size: 15px; font-weight: 700; margin: 20px 0 8px; color: #2a2a44; }
  .md-content h4 { font-size: 13px; font-weight: 700; margin: 16px 0 6px; color: #2a2a44; text-transform: uppercase; letter-spacing: 0.05em; }
  .md-content p { margin: 8px 0; }
  .md-content ul, .md-content ol { margin: 8px 0 12px 24px; }
  .md-content li { margin: 4px 0; }
  .md-content code { font-family: 'SF Mono', Menlo, monospace; font-size: 12px; background: #f5f6fa; padding: 2px 6px; border-radius: 4px; color: #c62828; }
  .md-content a { color: #3a4a8a; text-decoration: none; border-bottom: 1px solid rgba(58,74,138,0.3); }
  .md-content a:hover { border-bottom-color: #3a4a8a; }
  .md-content hr { border: none; border-top: 1px solid #e8ebf4; margin: 24px 0; }
  .md-content blockquote {
    border-left: 3px solid #e8ebf4;
    padding-left: 14px;
    margin: 12px 0;
    color: #555;
    font-style: italic;
  }
  .md-content :target { box-shadow: 0 0 0 3px #ffe082; transition: box-shadow 0.4s; border-radius: 4px; }

  /* GFM tables inside .md-content carry .md-table for consistent styling */
  .md-table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
    margin: 12px 0 16px;
    font-size: 13px;
  }
  .md-table th {
    background: #f5f6fa;
    color: #8892a4;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 2px solid #e0e4ef;
    padding: 10px 12px;
    text-align: left;
  }
  .md-table td { border-bottom: 1px solid #f0f1f5; padding: 10px 12px; }
  .md-table tr:last-child td { border-bottom: none; }
  .md-table tr:hover td { background: #fafbfd; }

  /* Fallback for the rare case the markdown contains a construct our conversion
     mapping doesn't cover — we embed the raw markdown text directly inside this
     <pre> block. Better to show raw markdown than to paraphrase or omit. */
  .md-content pre.md-raw {
    background: #f5f6fa;
    border: 1px solid #e8ebf4;
    border-radius: 6px;
    padding: 16px 18px;
    font-family: 'SF Mono', Menlo, Consolas, monospace;
    font-size: 12.5px;
    line-height: 1.55;
    color: #2a2a44;
    white-space: pre-wrap;
    overflow-x: auto;
    margin: 12px 0;
  }

  footer { text-align: center; font-size: 12px; color: #aaa; padding: 24px; margin-top: 20px; }
</style>
```

### Anchor ID convention — Section 3 blocks

Every `.analysis-block` in Section 3 carries an `id` attribute so Sections 1, 2, and the Hypotheses table can route to it via ↗ arrows. Use this canonical naming:

| Block | ID |
|---|---|
| Mix cascade analysis block | `block-cascade` |
| Geo / Non-Geo overview | `block-geo` |
| Shapley decomposition | `block-shapley` |
| 90-day CVR trend chart (Section 1, also anchorable) | `chart-90day` |
| Daily trend chart (C2O/S2C/LP2S) | `chart-daily-c2o` (substitute step name) |
| Funnel sub-step decomposition | `block-substeps` |
| Experience-level breakdown | `block-experience` |
| URL-level breakdown | `block-url` |
| Inventory TID summary | `block-inventory` |
| Session recordings | `block-recordings` |
| Lead-time distribution | `block-leadtime` |
| Price analysis | `block-price` |
| Weekday composition | `block-weekday` |
| HO / MB segment-specific block (when broken out) | `block-ho` / `block-mb` |
| Market context & operational signals | `block-market-context` |
| Dimensions checked — ruled out | `block-ruled-out` |
| Hypotheses explored | `block-hypotheses` |

Naming convention: `block-<kebab-name>` for tables and text blocks, `chart-<kebab-name>` for chart containers. When a CE-specific block doesn't fit the list (e.g., a custom breakdown by `previous_page_url`), invent a kebab-name following the same pattern — but reuse canonical IDs wherever the block matches the canonical type.


### Page skeleton

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CVR-RCA · [CE Name] (CE [ID])</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <!-- paste the shared <style> block here -->
</head>
<body>

<header id="top">
  <div class="eyebrow">CVR Root Cause Analysis</div>
  <h1>[CE Name] — CE [ID]</h1>
  <div class="meta">
    <span>📅 Pre: [pre_start]–[pre_end]</span>
    <span>📅 Post: [post_start]–[post_end]</span>
    <span>🌍 [Market] · [Country]</span>
    <span>🔗 <a href="[top_page_url]" target="_blank" style="color:#b0bec5;text-decoration:underline;">[top_page_url]</a></span>
  </div>
  <!-- Optional: dashboards row — see the consuming skill's structure file
       for URL templates (e.g., CVR-RCA's report_structure.md
       "Dashboards row" section). Omit the entire div if the
       skill defines no external dashboards. -->
  <div class="dashboards">
    <span class="dash-label">DASHBOARDS</span>
    <a href="[skill-defined URL]" target="_blank" class="dash-link">[Label] ↗</a>
    <!-- repeat per dashboard -->
  </div>
</header>

<div class="container">
  <!-- Section 1, 2, 3 blocks go here -->
</div>

<footer>Generated [date] · CVR-RCA · CE [ID] [CE Name]</footer>

<!-- Back-to-top floating arrow — fixed bottom-right, always visible.
     Scrolls to the <header id="top"> via the CSS scroll-behavior: smooth. -->
<a href="#top" class="back-to-top" aria-label="Back to top" title="Back to top">↑</a>

<!-- Plotly chart scripts go here -->
</body>
</html>
```

### Section label

```html
<div class="section-label">Section 1 — Executive Summary</div>
```

### Metric cards (Section 1a)

```html
<div class="metric-cards">
  <div class="metric-card">
    <div class="label">CVR</div>
    <div class="values">
      <span class="pre">4.67%</span>
      <span class="post">4.34%</span>
    </div>
    <div class="delta delta-neg">Δ −0.33pp / −7.0%</div>
  </div>
  <!-- repeat for LP2S, S2C, C2O, Traffic (LP Users) -->
</div>
```

### Root cause callout (Section 1b)

Two answer shapes are available inside each `.callout-item .a`. Pick the one that matches the finding — paragraph for a single mechanism, bullet list when the answer enumerates several drivers, headwinds, or mechanisms. See styling rule 7 above.

**Shape A — paragraph (single mechanism):**

```html
<div class="callout">
  <h2>Root Cause</h2>
  <div class="callout-item">
    <div class="q">What broke?</div>
    <div class="a">[specific finding — named metric, segment, magnitude]</div>
  </div>
  <div class="callout-item">
    <div class="q">Why did it break?</div>
    <div class="a">[mechanism — what it means, not what the data shows]</div>
  </div>
  <div class="callout-item">
    <div class="q">When did it break?</div>
    <div class="a">[exact date or window, sudden or gradual characterization]</div>
  </div>
</div>
```

**Shape B — multi-driver (lead claim + bullet list):**

Use when the answer names multiple drivers or headwinds. The lead claim is a short prose sentence (or two) that names the headline direction, magnitude, and framing. Each bullet starts with the named driver in `<strong>`, an em-dash, a one-line piece of evidence, and the `↗` ref-link at the end of the bullet (one arrow per bullet — no stacked arrows in a single sentence).

```html
<div class="callout">
  <h2>CVR Improved — What's Driving It &amp; What's Holding It Back</h2>

  <!-- Multi-driver answer: lead claim + bullet list -->
  <div class="callout-item">
    <div class="q">What drove the improvement?</div>
    <div class="a">
      [Lead claim — names the headline direction, magnitude, and framing
      (e.g., "structural and multi-causal", "concentrated on a single TGID").]
      <ul>
        <li><strong>[Driver name]</strong> — [one-line evidence]
            <a class="ref-link" href="#block-id">↗</a></li>
        <li><strong>[Driver name]</strong> — [one-line evidence]
            <a class="ref-link" href="#block-id">↗</a></li>
        <li><strong>[Driver name]</strong> — [one-line evidence]
            <a class="ref-link" href="#block-id">↗</a></li>
        <!-- repeat per driver -->
      </ul>
    </div>
  </div>

  <!-- Other callout items may use Shape A or Shape B depending on what fits -->
  <div class="callout-item">
    <div class="q">What's holding it back?</div>
    <div class="a">[paragraph or bullet list — same choice rule]</div>
  </div>

  <div class="callout-item">
    <div class="q">When did improvement begin?</div>
    <div class="a">[exact date or window, sudden or gradual]</div>
  </div>
</div>
```

Shape A and Shape B can be mixed within the same callout — each `.callout-item` makes the choice independently. A single-mechanism "When did it break?" answer can sit alongside a multi-driver "What drove the improvement?" answer in the same callout box.

---


### Action card (Section 2)

```html
<div class="action-card">
  <div class="ac-header">
    <div class="priority-badge p1">P1</div>
    <div class="cause">[one sentence — the specific finding that drives this action]</div>
  </div>
  <div class="dri-row">
    <span class="dri-badge">[Team name]</span>
    <span>+ [secondary team if applicable]</span>
  </div>
  <ul>
    <li>[specific action step with named experience, date, or URL]</li>
    <li>[specific action step]</li>
  </ul>
</div>
```

---

### Analysis block (Section 3 — general pattern)

```html
<div class="analysis-block">
  <div class="block-title">[Block title — what this analysis shows]</div>
  <div class="verdict-line">[One-line finding — red for signal, add class "neutral" for ruled-out]</div>

  <!-- table or chart -->

  <p style="font-size:13px;color:#555;margin-top:12px;">
    [Interpretive subtext — what the data implies, not what it shows]
  </p>
</div>
```

---

### Table with highlight rows

**Raw user counts are mandatory in every table.** Any table that shows rates, shares, or percentages must also show the raw user count for that segment — either as a dedicated column or as a "Pre N / Post N" sub-label. A stakeholder reading a 12pp rate drop on a 40-user segment should be able to judge its significance immediately, without doing arithmetic. Never show shares or rates alone.

The minimum columns for a rate table are: **Segment · Pre Users · Post Users · Pre Rate · Post Rate · Δ Rate**. When checkout or booking impact is the point (e.g. experience-level S2C), add a **Checkout Impact** column.

```html
<table>
  <thead>
    <tr>
      <th>Segment</th>
      <th class="num">Pre Users</th>  <!-- always include raw counts -->
      <th class="num">Post Users</th>
      <th class="num">Pre S2C</th>
      <th class="num">Post S2C</th>
      <th class="num">Δ S2C</th>
    </tr>
  </thead>
  <tbody>
    <tr class="highlight-row">   <!-- use highlight-row for the primary driver row -->
      <td><strong>HO</strong></td>
      <td class="num">8,240</td>
      <td class="num">9,980</td>
      <td class="num">35.7%</td>
      <td class="num">23.4%</td>
      <td class="num neg">−12.3pp</td>
    </tr>
    <tr>
      <td><strong>MB</strong></td>
      <td class="num">41,600</td>
      <td class="num">43,200</td>
      <td class="num">24.8%</td>
      <td class="num">24.2%</td>
      <td class="num">−0.6pp</td>
    </tr>
  </tbody>
</table>
```

Use `.neg` (red, bold) for meaningful drops, `.pos` (green, bold) for gains, plain text for near-zero changes. Use `.highlight-row` to draw the eye to the primary driver rows.

---

### Plotly chart conventions

**Color palette:** Pre-period: `#6c8ebf` (blue). Post-period: `#c62828` (red). LY overlay: `#9e9e9e` (grey, dashed). Post window background shade: `rgba(198,40,40,0.05)`.

**Color names in callout text must be derived from chart code, not assumed.** When any verdict line, callout, or subtext paragraph names a trace by color (e.g. "UTV Raptor (red)"), the name must match the hex value explicitly assigned in that chart's `colors` object or trace definition — never inferred from Plotly's default color sequence or trace order. Write color references after the `colors` object is defined in the script; never before. If colors are not explicitly set, set them explicitly before writing any text that references them.

**Always add:** dashed mean reference lines (use `shapes` in layout) and annotations for pre/post average values directly on the chart.

**Known-event markers (user context).** When `user_context.md` carries a **Known event** whose date falls inside a daily/90-day chart's window, drop a dated vertical marker on that chart: a `shapes` vline at the event date + a short `annotations` label (e.g. "Pricing change · Apr 8"). Same `shapes`/`annotations` mechanism as the mean lines — just add an entry. Add it **only** when the event date is in-range and relevant to that chart's metric; never invent or shift dates, and never move the analysis window (the window is fixed at Step 0). The marker orients the reader to when an operational change landed relative to the trend.

**Chart sizing:** trend charts 280px height, bar charts 260px height. Use `responsive: true` in `Plotly.newPlot` config.

**Example — daily S2C trend:**
```javascript
Plotly.newPlot('trend-chart', [
  {
    type: 'scatter', mode: 'lines+markers', name: 'Pre period (Apr 6–12)',
    x: preDates, y: preS2C,
    line: { color: '#6c8ebf', width: 2.5 },
    marker: { size: 4, color: '#6c8ebf' }
  },
  {
    type: 'scatter', mode: 'lines+markers', name: 'Post period (Apr 13–19)',
    x: postDates, y: postS2C,
    line: { color: '#c62828', width: 2.5 },
    marker: { size: 4, color: '#c62828' }
  }
], {
  height: 280,
  yaxis: { tickformat: '.1%', title: 'S2C rate (%)' },
  xaxis: { title: 'Date' },
  plot_bgcolor: '#fff', paper_bgcolor: '#fff',
  font: { family: '-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif', color: '#1a1a2e' },
  legend: { orientation: 'h', y: -0.3 },
  margin: { l: 55, r: 20, t: 30, b: 50 },
  shapes: [
    { type: 'line', x0: preDates[0], x1: preDates[preDates.length-1],
      y0: preMean, y1: preMean, line: { color: '#6c8ebf', dash: 'dot', width: 1.5 } },
    { type: 'line', x0: postDates[0], x1: postDates[postDates.length-1],
      y0: postMean, y1: postMean, line: { color: '#c62828', dash: 'dot', width: 1.5 } }
  ],
  annotations: [
    { x: preDates[Math.floor(preDates.length/2)], y: preMean,
      text: 'Pre avg ' + (preMean*100).toFixed(1) + '%',
      font: { color: '#6c8ebf', size: 11 }, showarrow: false, yshift: 12 },
    { x: postDates[Math.floor(postDates.length/2)], y: postMean,
      text: 'Post avg ' + (postMean*100).toFixed(1) + '%',
      font: { color: '#c62828', size: 11 }, showarrow: false, yshift: -16 }
  ]
}, { responsive: true });
```

**90-day + LY overlay chart:** Two traces — current year (blue solid) and LY (grey dashed) — both plotted against `currentDates` on the x-axis. Do NOT use actual LY calendar dates for the LY line; use the current-year date array so both lines sit at the same calendar position and are directly comparable month-over-month.

**Step 1 — Extract `lyCvr` from summary.json.** LY data is NOT a top-level key. It lives inside `trend_context.series` as entries tagged `"series": "ly"`, interleaved with current-year entries tagged `"series": "current"`. You must filter, extract, and align it to `currentDates` before doing anything else:

```javascript
// Extract currentDates and currentCvr from trend_context.series
const currentSeries = summaryJson.trend_context.series.filter(e => e.series === 'current');
const currentDates = currentSeries.map(e => e.date);
const currentCvr   = currentSeries.map(e => e.cvr);

// Build lyCvr aligned to currentDates (null for dates with no LY entry)
const lyMap = {};
summaryJson.trend_context.series
  .filter(e => e.series === 'ly')
  .forEach(e => { lyMap[e.date] = e.cvr; });
const lyCvr = currentDates.map(d => lyMap[d] ?? null);
```

**Step 2 — LY data guard (mandatory).** A CE that had no Headout history last year will have all-zero LY CVR entries (not nulls). The guard must reject zeros as well as nulls — a flat line at 0% is not a valid LY overlay. The chart always renders with current-year data. When LY is absent, insert a visible amber badge immediately after the chart div — do not replace the chart with a warning or bury the note in grey subtext below it.

```javascript
// Guard: requires at least one LY value that is non-null AND > 0
const hasLyData = lyCvr.some(v => v !== null && v !== undefined && v > 0);
// The chart always renders — traces90d already excludes the LY trace when hasLyData is false.
// Do NOT replace the chart div with a warning banner.
```

After the `Plotly.newPlot('trend-90day', ...)` call, add:

```javascript
// When LY data is absent, insert a visible amber badge after the chart — not grey subtext
if (!hasLyData) {
  document.getElementById('trend-90day').insertAdjacentHTML('afterend',
    '<div style="display:inline-flex;align-items:center;gap:6px;background:#fff8e1;border:1px solid #f9a825;' +
    'border-radius:4px;padding:5px 10px;margin-top:8px;font-size:12px;color:#7a5c00;">' +
    '<span>⚠️</span><span><strong>No LY overlay:</strong> ' +
    '[state the specific reason — e.g. "CE launched in 2025, fewer than 10 users on scattered dates last year"]. ' +
    'LY line suppressed to avoid a misleading comparison.</span></div>'
  );
}
```

X-axis: `tickformat: '%d %b'`, `dtick: 7 * 86400000` (weekly ticks in milliseconds) — shows "01 Jan", "08 Jan", etc., giving week-level resolution across the 90-day window.

Post window: shade with a `rect` shape and a dashed vertical line at `post_start`. Use **red** (`rgba(198,40,40,0.05)`) for CVR decline cases, green (`rgba(46,125,50,0.05)`) for CVR improvement cases.

```javascript
// Define post period bounds and postDates for the annotation midpoint
const POST_START = summaryJson.meta.post_start;
const POST_END   = summaryJson.meta.post_end;
const postDates  = currentDates.filter(d => d >= POST_START && d <= POST_END);

// Both traces use currentDates — lyCvr values plotted at the same seasonal position
const currentYear = new Date(currentDates[0]).getFullYear();
const lyYear = currentYear - 1;
const traces90d = [
  {type:'scatter', mode:'lines', name:'CVR ' + currentYear,
   x: currentDates, y: currentCvr, line:{color:'#6c8ebf', width:2}}
];
if (hasLyData) {
  traces90d.push(
    {type:'scatter', mode:'lines', name:'CVR ' + lyYear + ' (LY)',
     x: currentDates, y: lyCvr, line:{color:'#9e9e9e', dash:'dash', width:1.5}}
  );
}

const postShadeColor = (summaryJson.headline.delta.cvr < 0)
  ? 'rgba(198,40,40,0.06)' : 'rgba(46,125,50,0.05)';
const postLineColor  = (summaryJson.headline.delta.cvr < 0) ? '#c62828' : '#2e7d32';
const midPostDate = postDates[Math.floor(postDates.length / 2)];

Plotly.newPlot('trend-90day', traces90d, {
  height: 280,
  yaxis: {tickformat:'.1%', title:'CVR'},
  xaxis: {tickformat:'%d %b', dtick: 7 * 86400000, title:''},
  plot_bgcolor:'#fff', paper_bgcolor:'#fff',
  font: {family:'-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif', color:'#1a1a2e', size:11},
  legend: {orientation:'h', y:-0.2},
  margin: {l:55, r:20, t:30, b:60},
  shapes: [
    {type:'rect', x0:POST_START, x1:POST_END, y0:0, y1:1,
     xref:'x', yref:'paper', fillcolor: postShadeColor, line:{width:0}},
    {type:'line', x0:POST_START, x1:POST_START, y0:0, y1:1,
     xref:'x', yref:'paper', line:{color: postLineColor, dash:'dot', width:1}}
  ],
  annotations: [{x: midPostDate, y: 0.92, xref:'x', yref:'paper',
    text:'Post period', font:{color: postLineColor, size:10}, showarrow:false}]
}, {responsive:true});
```

---

## Changelog

| # | Date | Changes |
|---|------|---------|
| c007 | 2026-06-03 | **"Slack integration & link-to-table styling" → "External context integration & link-to-table styling" (lens-agnostic).** The section now explicitly governs how *any* external lens (Slack, perf-audit, CE Health, future siblings) surfaces — Slack stays the worked example, but the three-layer model + four-pattern classification + ↗ link-to-table affordance are stated as lens-agnostic. Section intro gains a one-line provenance statement (used signals appear both woven-in and as a table row). Layer 3 reframed: the block is the **External Signals & Corroboration** "sources cited" panel, rendered whenever any lens contributed a used signal — and **Pattern A corroborations now earn a table row** (previously inline-only). The four-pattern surfacing table updated so A/B/C all add a row. Paired with cvr-rca SKILL.md c040 (provenance contract in the Step 2b preamble) and report_structure.md (block renamed/generalised, id `block-market-context` retained). |
| c006 | 2026-06-03 | Registered two new cross-tab anchor prefixes for the CE-RCA umbrella composite: `summary-*` (the Summary synthesis tab) and `cehealth-*` (the CE Health tab). Citation format split gains a CE Health source form (`per CE Health ↗` / `CE Health: <fact> ↗`). Both prefixes apply only inside the CE-RCA composite where those tabs exist; standalone CVR-RCA reports are unaffected. Paired with cvr-rca SKILL.md c039 (CE Health reconciliation lens at Step 2b). |
| c001 | 2026-05-28 | Initial version. Skill-agnostic visual primitives extracted from `cvr-rca/references/report_structure.md` (v1.19): shared `<style>` block (CSS for header / container / metric cards / callout / action cards / analysis blocks / verdict lines / tables / shapley flex bar / fixed segment banner / ref-link / tab bar / md-content); Page skeleton; Section label; Metric cards HTML; Root cause callout HTML (Shape A paragraph + Shape B multi-driver bullet); Action card HTML; Analysis block (general pattern); Table with highlight rows; Plotly chart conventions; Anchor ID convention; Styling and language guidelines (rules 1–7); Slack integration & link-to-table styling; Tabbed report structure (full HTML pattern); Anti-patterns. Read by any skill producing an HTML report. |
| c005 | 2026-05-29 | **Trimmed the "ignore `.html`" defensive language from Perf-audit tab rendering.** Removed the "Source of truth: never `perf_audit_report.html`" paragraph and rewrote the corresponding anti-pattern row to focus on the positive rule (perf-audit content stays in the perf-audit's structure) rather than enumerating the specific `.html` failure mode. The c004 guardrails made sense when perf-audit-skill had been emitting `.html` locally; once perf-audit-skill was rolled back to emitting markdown only, those guardrails became obsolete. Scalable skill instructions describe canonical behavior; one-off defensive negations belong in commit messages and changelog history, not in the live spec. Canonical rule unchanged: Tab 2 reads `perf_audit_report.md` and converts verbatim. Companion change in `SKILL.md` c037. |
| c004 | 2026-05-29 | **Perf-audit tab rendering rewritten + missing `.md-content` / `.md-table` CSS finally added.** Two related fixes: **(1)** The "Perf-audit tab rendering" subsection is rewritten to enforce verbatim markdown → HTML conversion from `perf_audit_report.md`, with explicit rules against summarization / restructuring / dropping subsections (h3/h4 must survive — `4a. Campaign roster`, `5c. Money on table (sized)`, Appendix sections, Data Sources all preserved). Source of truth pinned: `perf_audit_report.md` only. **`perf_audit_report.html` (if it exists) is ignored** because the perf-audit-skill's own md→html step may restructure content we can't control. Conversion mapping expanded to cover blockquotes, h4, fenced code blocks, and the inline link syntax. New fallback rule: if any markdown construct can't be faithfully converted, embed the raw markdown text inside `<pre class="md-raw">` — better to show raw markdown than paraphrased HTML. **(2)** The c001 entry promised `md-content` styling in the shared `<style>` block but the actual CSS rules were never added during the v1.19 extraction. Adding them now: `.md-content` (h1/h2/h3/h4 hierarchy, paragraph spacing, ul/ol, code, links, hr, blockquote, target highlight) plus `.md-table` (GFM table styling consistent with the rest of the visual kit) plus new `.md-content pre.md-raw` (monospace fallback for the raw-markdown render). Two new Anti-pattern rows codify the rule: "Tab 2 sources from .html or wraps perf-audit content in CVR-RCA chrome" and "Sub-headings dropped during the perf-audit md→HTML conversion". Companion change in `cvr-rca/SKILL.md` c036 (Step 3 Tab framework rewritten to drop the `.html` byte-paste). Driven by CE 3593 RCA where Tab 2 was 31% smaller than the source `.md` due to perf-audit-skill's `.html` restructuring step. |
| c003 | 2026-05-29 | Back-to-top floating arrow added. New `.back-to-top` CSS rule defines a fixed bottom-right circular button (40px, dark navy translucent background, subtle box-shadow, hover-brightens + lifts 2px). HTML pattern in Page skeleton: a single `<a href="#top" class="back-to-top" aria-label="Back to top">↑</a>` placed near the end of `<body>` after the `<footer>`. `<header>` gains `id="top"` as the anchor target. The existing `html { scroll-behavior: smooth; }` rule handles the smooth scroll without any JS. Hidden on print via `@media print { .back-to-top { display: none; } }`. Always visible (no scroll-detection JS) — kept minimal per "very small UX addition" framing. |
| c002 | 2026-05-28 | Dashboards row chrome added to header CSS — `.dashboards`, `.dash-label`, `.dash-link` rules support an optional row of pill-button links to external dashboards scoped to the same entity as the report. Page skeleton example gains a placeholder `<div class="dashboards">` block inside `<header>`, with a comment noting the consuming skill's structure file owns the URL templates. Chrome only — URLs are skill-specific (CVR-RCA carries Omni + Sentra in its `report_structure.md` "Dashboards row" section). Companion change in `cvr-rca/references/report_structure.md` c032 (Omni + Sentra URL templates). |
