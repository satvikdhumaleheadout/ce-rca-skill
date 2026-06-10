# CVR-RCA Skill — Changelog

This file tracks every meaningful change pushed to this repository. Each entry corresponds to a GitHub push and is written for stakeholder consumption — what changed, why it matters, and what improved.

---

## [v1.30] — 2026-06-10 — Eval → on-demand maintainer tool; session recordings removed

**Sync note.** Applied to the vendored copy first, then mirrored to the standalone source
(`~/Documents/RCA skill/cvr-rca`) — the two are **back in sync** on these files (the 7 edited files
are byte-identical, both at v1.30.0).

Two changes:

**1. Auto-evaluation → on-demand.** The run flow no longer scores itself. The auto "Step 4 — Evaluate
the analysis" section (which ran the rubric and wrote `evaluation.md` at the end of every run) is
removed. In its place is a concise **"Quality Evaluation — Maintainer Tool (On-Demand)"** section:
a maintainer spawns a sub-agent against any finished run-dir (read `$SKILL_DIR/evals/evaluator.md`,
run dir `<run_dir>`, write `<run_dir>/evaluation.md`). It reads only on-disk artifacts, is not part
of the run, and is never shown to the analyst. The 7-theme rubric and the meta-review note are kept.
The run now ends with a single chat line — `Report → <run_dir>/report.html` — no eval, no narration.
`evals/evaluator.md` gains an on-demand maintainer-tool preamble (rubric unchanged). Saves tokens +
time on every analyst-facing run for a record the analyst never sees. Companion: ce-rca SKILL.md
Step 4b doc reworded to "*if* a maintainer ran CVR-RCA's on-demand eval" (the `[ -f ]`-guarded
organize move is unchanged).

**2. Mixpanel session-recording pulls removed.** Every active instruction/callout to fetch or cite
session recordings (the `Get-User-Replays-Data` MCP) is excised from `SKILL.md`, `references/`
(context, hypothesis, report_structure, visual_kit, worked_example), and `evals/evaluator.md`. The
LP2S broad-drop hypothesis fallback is reworded to alternative evidence paths (APM / deployment
timestamps / vendor status / event-level) so the branch keeps a non-empty fallback. Ruled-out and
anti-pattern examples now use quantitative checks (lead-time bucket queries) instead of recordings.
Historical CHANGELOG entries are left as-is.

---

## [v1.29] — 2026-06-08 — Transcript tree-map fenced (markdown-safe)

The investigation transcript's `## Tree map` is now wrapped in a ` ```text ` code fence; the detail
sections stay plain markdown. No content or behaviour change for a standalone CVR-RCA run. The reason
is downstream: the CE-RCA umbrella report now renders each skill's transcript **as markdown** in its
Transcript tab, and an unfenced ASCII tree (`├─ │ └─`) collapses into a paragraph under markdown.
Fencing keeps the alignment intact. Companion: ce-rca v1.9.0.

---

## [v1.28] — 2026-06-08 — Additive hooks for CE-RCA's context-ingestion layer

**Summary:** Small, gated additions so the CE-RCA umbrella's new context-ingestion layer (user-pointed docs / Sheets / Slack) can flow through CVR-RCA. Every one is a no-op on a standalone run with no `user_context.md` / `orchestration.json`, so standalone behaviour is unchanged.

### What changed
- **User-data lens** — a `user_data_*` entry (an ad-hoc data pull the analyst provided, distilled by the orchestrator's ingestion sub-agent) reconciles at Step 2b with the same four-pattern model as any other lens. No new mechanism — one more manifest entry.
- **User Slack channel** — the Slack collector takes an optional `user_channels` arg and reads the user-named channel(s) alongside its discovery set (new Search 4), tagged "user-requested". One Slack pass, one `slack_context.md`.
- **Known-event chart markers** — a Known event with an in-window date drops a dated marker on the daily/90-day trend charts. It never moves the analysis window.
- **User-provided citations** — a distinct `(per user-provided … ↗)` tag so analyst-supplied evidence reads distinctly from system-derived.

Companion: ce-rca v1.8.0.

## [v1.27] — 2026-06-03 — User context as a steering input

**Summary:** CVR-RCA can now take the analyst's own knowledge into the investigation. When `<run_dir>/user_context.md` is present — captured by the CE-RCA umbrella's Step 1 pause (focus / hunch / known event), or hand-placed in a standalone run — CVR-RCA consumes it at **two points**: at **L0** the priors become *prioritised, falsifiable* branches (opened early, tested, can be ruled out), and at **Step 2b** each prior is closed and corroborated against the data-driven findings. This is what lets a human say "look at LP2S at the landing-page level, I think it's broken there" and have that genuinely shape the hypotheses Claude opens — without the RCA losing its independence.

**The balance (the whole point).** User context is powerful but must not distort the RCA. Five guardrails are baked into the skill text: **(1) priority, not tunnel-vision** — priors are appended to the data-driven default branch set, never a replacement; the mix/shapley/trend orientation still determines the primary driver. **(2) corroboration, not confirmation** — at Step 2b a prior is reconciled with the four-pattern model and can be RULED OUT; it carries no special authority. **(3) not narrow** — the full investigation still runs; the leaf is wherever the data lands, even if that's not where the user pointed. **(4) proportional output** — a confirmed prior is woven into the relevant finding; a ruled-out one is a single line; the report leads with the data-driven driver. **(5) always closed, never ignored** — every prior is resolved CONFIRMED / RULED OUT / DATA GAP via the existing close-every-quantified-signal discipline.

**Why user context may steer L0 when Slack / perf-audit / CE Health may not.** Those are *lenses* — secondhand evidence held to Step 2b so they can't bias branch selection. User context is the analyst's *intent*, which legitimately directs where to look — so it is the one deliberate exception, read at L0. The falsifiability guardrail keeps it honest: the data still decides.

### Changes by file

- **`SKILL.md`** (c042) — L0 gains "Signal 0 — user context" (priors → prioritised falsifiable branches + the lens-exception carve-out + the not-narrow rule). Step 2b gains check #12 (close every prior + four-pattern corroboration + proportional-output rule). Preamble updated to #9–#12 with the user-context-is-not-a-lens note. VERSION → 1.27.0.

### What did not change

- The investigation engine (cascade, L1/L2+, the four-pattern model), and the other lenses' reconciliation — unchanged. Signal 0 is additive.
- Standalone `/cvr-rca` with no `user_context.md` → byte-identical to v1.26.

### Paired change in CE-RCA (separate repo)

- ce-rca v1.2.0 (m005): the Step 1 pause captures the optional free-text context into a structured `user_context.md` and adds a `user_context` pointer to `orchestration.json`. v1 is free-text only; files / Google Sheets / Slack channels are a deferred v2 slot.

---

## [v1.26] — 2026-06-03 — Provenance contract + Sentra deprecation

**Summary:** Two reliability fixes, both **output contracts** (they govern what the finished report must contain, never how the investigation runs — so the skill keeps its analyst freedom). **(1) Source attribution made deterministic.** Previously, signals from external lenses (Slack, perf-audit, CE Health) only reliably showed up as a *table* when **Slack** returned a mechanism/reframing signal — the "Market context" block was Slack-gated. So when Slack was unavailable (e.g. CE 243, where the connector timed out) and perf-audit merely *confirmed* the finding (a "Pattern A" corroboration, which was wired inline-only), the perf-audit signals dropped out of any table and survived only as two buried inline citations. v1.26 generalises the block into a source-agnostic **"External Signals & Corroboration"** table that renders whenever *any* lens contributed a signal you used — one row per used signal, each with a Source ↗ link to the owning tab or thread. The governing rule is a one-paragraph **provenance contract**: any external signal that informs a callout, verdict, or narrative line must appear in two places — woven in at the point of use **and** as a table row — regardless of whether it corroborated, explained, or reframed. A missing lens becomes a disclosure row, never suppresses the table. Net effect: the reader can always see, at a glance, every outside source the analysis leaned on, and absence of a row now reliably means "wasn't used" rather than "Claude forgot." **(2) The 90-day trend chart can't silently vanish.** The CE 243 report shipped with the always-on 90-day LY trend chart's container but no render script — an empty gap. Step 3 gains a required-elements completeness check backed by a new **advisory linter** (`scripts/validate.py`): after the report is written, it flags any chart container missing its `Plotly.newPlot` call (caught generically — any orphaned chart, not an enumerated list) plus missing always-on elements and a missing External Signals table when external lenses were used. It is cosmetic and advisory by design — it runs only at the end, never sees the investigation, never edits the report, and never blocks (exit 0 always); Claude adds each flagged element or consciously skips it. So the skill's analyst freedom is fully preserved while silent structural gaps (like the CE 243 empty chart) get caught before the report ships.

**(3) Sentra dashboard link deprecated.** Sentra is being retired as a tool, so the report header's dashboards row no longer creates a Sentra pill — it now carries the **Omni** link only. The Omni URL template, the emitted-HTML pattern, and the pre-write sanity check are all trimmed to Omni-only. (Historical changelog entries that mention Sentra are left intact — we don't rewrite history.)

**Why it matters:** a C-level reader needs to trust both the *completeness* of the report (the headline trend chart is always there) and the *provenance* of every claim (every outside signal is attributed and traceable). Both were previously probabilistic — Claude did them well *sometimes*. v1.26 makes them contracts. The Sentra removal keeps the header pointing only at tools that still exist.

### Changes by file

- **`SKILL.md`** (c040, c041) — c040: Step 2b checks #9–#11 preamble gains the provenance contract + a widest-first reading hint (CE Health → perf-audit → Slack, synthesise together); Check #10 Pattern A now also adds a table row (was inline-only — the CE 243 drop-out bug); Step 3 gains the required-elements completeness check (90-day chart + its render script, metric cards, callout, Shapley, hypotheses, External Signals block). c041: Sentra deprecation. VERSION → 1.26.0.
- **`references/report_structure.md`** — (provenance) the Section 3 "Market context & operational signals" block becomes the source-agnostic **"External signals & corroboration"** block: renders for any used lens signal, source-agnostic columns (Source cell links to Slack thread *or* perf-audit/CE-Health tab anchor), unavailable-lens disclosure row; keeps id `block-market-context` so existing ↗ citations resolve. (Sentra) "Dashboards row — Omni + Sentra" → "Dashboards row — Omni"; Sentra URL template + pill + sanity-check mention removed.
- **`references/visual_kit.md`** (c007) — "Slack integration & link-to-table styling" → **"External context integration & link-to-table styling"** (lens-agnostic; Slack stays the worked example). Layer 3 + the four-pattern surfacing table updated so Pattern A/B/C all earn a table row, not just Pattern B/C. Dashboards-row doc-comment in the Page skeleton points to the renamed "Dashboards row" section.

### What did not change

- The investigation. L0/L1/L2, the cascade, dimension cuts, the four-pattern model, the hard rule (lenses consulted only at Step 2b) — all unchanged. These are output contracts on the report, not new process.
- Standalone `/cvr-rca` runs work exactly as before; the table simply renders for whatever lenses were present (often just Slack).
- The CE Health / perf-audit reconciliation logic from v1.25 — only the *surfacing* (table + provenance) changed.

---

## [v1.25] — 2026-06-03 — CE Health as a reconciliation lens + manifest-driven context layer

**Summary:** CVR-RCA now reads **CE Health** at its Step 2b synthesis — the missing cross-skill wire that lets the funnel RCA corroborate against, and reframe relative to, the CE-level health picture. Until now CVR-RCA reconciled its data-driven findings against Slack and perf-audit but was blind to CE Health (the wide upstream lens that decomposes the CE's revenue move across Traffic/CVR/AOV/Completion/Take Rate). When CVR-RCA runs under the CE-RCA umbrella, it now picks up CE Health's facts and weaves them in — e.g., localizing an S2C collapse on TGID 7148 *and* citing CE Health's 30% RPC drop for that same TGID, or stepping back to say "the funnel finding is real but AOV was the headline mover per CE Health" when Shapley points elsewhere. To make this scale (rather than bolting on a #11, #12, #13 forever), the per-lens checks are reframed under one **manifest-driven context layer**: read the lens list from `orchestration.json` when the master declares it, else detect by file presence — then reconcile every present lens with the same four-pattern model. A future sibling lens is one manifest entry, not new machinery.

### Changes by file

**`SKILL.md`** — c039
- Step 2b gains a "Context reconciliation — read every available lens" preamble: the lens manifest (`orchestration.json` `context_lenses` → file-presence fallback), the one-model rule (four-pattern A/B/C/D/Reject per lens), and the hard rule (lenses consulted only at Step 2b, never during L0/L1/L2).
- New check #11 — CE Health reconciliation: entity-level cross-link (Pattern A corroboration on a shared TGID/experience), headline-driver reframe (Pattern C when CE Health's Shapley names AOV/Completion/Take Rate), B/D as usual. `#cehealth-<slug>` cross-tab citations, standalone-safe (no CE Health present → no citation).
- VERSION → 1.25.0.

**`references/visual_kit.md`** — c006
- Registers the `summary-*` and `cehealth-*` cross-tab anchor prefixes (for the CE-RCA umbrella composite) and the CE Health citation form (`per CE Health ↗` / `CE Health: <fact> ↗`).

### What did not change

- The four-pattern model, and the Slack (#9) and perf-audit (#10) reconciliations — same behavior, now framed as manifest lens entries.
- Standalone `/cvr-rca` — no `orchestration.json`, no `ce_health_report.md` → falls back to file-presence detection, CE Health simply absent, no `#cehealth-*` citations. Byte-compatible with v1.24.
- Report structure, tab framework, investigation logic, perf-audit and CE Health skills themselves.

### Why this design

The thing that makes CVR-RCA's output good is that it reconciles its own data-driven leaf against every other lens at synthesis time — corroborate, explain, reframe, test. CE Health was a glaring omission: it carries the CE-level "what actually moved revenue" decomposition that should anchor and sometimes reframe a funnel finding. Adding it as check #11 fixes that; reframing the checks as a manifest-driven layer means the *next* lens (an AOV-RCA sibling, say) costs one entry, not a new check and a new code path. The hard rule (consult lenses only at Step 2b) is preserved so the data-driven investigation stays honest — lenses corroborate a completed picture, they never steer branch selection.

---

## [v1.24] — 2026-06-03 — Orchestration handshake: run cleanly as a sub-skill of the CE-RCA master

**Summary:** CVR-RCA can now be orchestrated by the new **CE-RCA master skill** (a separate repo that runs CE Health → CVR-RCA + perf-audit → one composite tabbed report) without firing perf-audit twice. A new master writes an `orchestration.json` file into the shared run directory listing which sub-skills it's pre-firing. CVR-RCA's perf-audit spawn block now checks that file: if `perf-audit-skill` is listed under `fired_by_master`, CVR-RCA skips its own perf-audit spawn and consumes the master's output at Step 2b check #10 instead. The existing wait-for-file polling at check #10 handles any timing race, so there's no new coordination machinery. **Standalone `/cvr-rca` runs are completely unchanged** — the orchestration file doesn't exist, so the normal fire-and-forget spawn happens exactly as before. This is the only change CVR-RCA needs to participate in the umbrella; its report, investigation logic, and visual output are otherwise identical to v1.23.

### Changes by file

**`SKILL.md`** — c038
- The "Perf-audit context — fire and forget" spawn block gains a delegation-check preamble: read `<run_dir>/orchestration.json`; if `perf-audit-skill` is in `fired_by_master`, log the delegation and skip the spawn (consume at Step 2b). Belt-and-braces secondary check skips the spawn if `perf_audit_report.md` already exists. Falls through to normal spawn logic when neither file is present.
- VERSION bumped to 1.24.0.

### What did not change

- Standalone `/cvr-rca` behavior — byte-identical to v1.23 (orchestration file absent → normal spawn).
- The Step 2b check #10 reconciliation — same four-pattern routing, same polling, same citations.
- The report, the tab framework, the visual kit, the investigation logic — all unchanged.
- The perf-audit skill itself — unchanged.

### Why this design

The CE-RCA master needs CVR-RCA and perf-audit to run side-by-side under one run directory, but CVR-RCA already fires perf-audit on its own when the cascade goes Paid — naively, that means two perf-audit runs for the same CE. A file-existence race ("skip if the report exists") is fragile because CVR-RCA might check before the master's parallel perf-audit has finished writing. The `orchestration.json` handshake is race-free: it declares intent *before* anything is fired, so CVR-RCA knows to delegate regardless of timing, and the existing consume-time polling does the waiting. The mechanism is invisible to standalone runs and generalises to any future orchestrator.

---

## [v1.23] — 2026-05-29 — Trim one-off `.html` guardrails from the Tab 2 spec

**Summary:** Removes defensive language from the v1.22 spec that warned "if `perf_audit_report.html` exists, ignore it." That paragraph was added when perf-audit-skill had been emitting `.html` locally; once perf-audit-skill was rolled back to markdown-only output (also as part of the v1.22 change set), the warning became obsolete. Scalable skill instructions describe canonical behavior; one-off defensive negations against a failure mode that can't occur belong in commit messages and the changelog, not in the live spec. The canonical rule is unchanged: **Tab 2 reads `perf_audit_report.md` and converts markdown → HTML verbatim.**

### Changes by file

**`SKILL.md`** — c037
- Step 3 "Tab framework — when to use it" paragraph that started "Important — do NOT use `perf_audit_report.html` even if it exists" is removed. The Tab 2 description is now a single positive instruction (read `.md`, convert verbatim, preserve every section/subsection/word) plus the fallback rule for unparseable markdown.

**`references/visual_kit.md`** — c005
- "Perf-audit tab rendering" subsection: the "Source of truth: never `perf_audit_report.html`" line is removed. The fidelity rules section stays unchanged.
- Anti-pattern row rewritten to focus on the positive rule (don't wrap perf-audit content in CVR-RCA chrome) without enumerating the specific `.html` failure mode.

### What did not change

- The v1.22 fidelity rules (every section, every subsection, every word preserved). Same.
- The conversion mapping (markdown → HTML tag table). Same.
- The fallback to `<pre class="md-raw">` for unparseable constructs. Same.
- perf-audit-skill behavior. Already rolled back to markdown-only in v1.22.

### Why this design

Skill instructions accumulate during firefights — "if X breaks, do Y" — and never get pruned. The result is a spec that gets longer, more defensive, and harder for new readers to parse. The v1.22 `.html`-ignore rule was real and necessary when written, but once the upstream cause was fixed (perf-audit-skill stopped emitting `.html`), the defensive rule was just describing a problem that can't happen. Removing it now keeps the spec scalable: any future skill emitting markdown for embedding follows the same canonical Tab 2 path, with no special-case negotiation. If a similar issue recurs in the future, the right move is to fix the producing skill, not to permanently inflate the consuming spec.

---

## [v1.22] — 2026-05-29 — Tab 2 sources from perf-audit `.md` verbatim (partial revert of v1.19's HTML embed)

**Summary:** CVR-RCA's Tab 2 (Paid Performance Audit) reverts to verbatim markdown → HTML rendering of `perf_audit_report.md`. The v1.19 design had Tab 2 byte-paste from `perf_audit_report.html` — a polished HTML file the perf-audit-skill emits alongside its markdown. That design relied on perf-audit-skill's md→html step being faithful. In practice it isn't: perf-audit-skill restructures and summarizes during its own md→html conversion, collapsing h3/h4 subsections into parent h2 sections, dropping appendices, and adding CVR-RCA-style chrome (callouts, action cards) around its content. Result: CE 3593's Tab 2 was 31% smaller than the source `.md` (2,051 words vs 2,975), with sub-headings like `4a. Campaign roster, post-consolidation`, `5c. Money on table (sized)`, the Monthly Trajectory appendix, and the Data Sources section all collapsed or dropped.

v1.22 fixes this at the source: Tab 2 reads `perf_audit_report.md` directly and converts markdown → HTML using the documented mapping in `visual_kit.md`. **Every section, every subsection, every table cell, every paragraph, every word is preserved.** No summarization, no restructuring, no CVR-RCA chrome wrapped around perf-audit content — the perf-audit-skill's own structure is the structure of Tab 2. `perf_audit_report.html` is explicitly ignored even if it exists; only the `.md` is canonical.

A fallback rule covers the rare case where the markdown contains a construct the conversion mapping doesn't cover (e.g., the perf-audit-skill adds a new construct in a future version): embed the raw markdown text inside `<pre class="md-raw">`. Better to show raw markdown than paraphrased HTML — fidelity beats polish.

The fix also caught a related drift: the `.md-content` and `.md-table` CSS rules were referenced by spec but never actually added to `visual_kit.md` during the v1.19 extraction. They're added now (along with the new `.md-content pre.md-raw` styling for the fallback).

### Changes by file

**`SKILL.md`** — c036
- Step 3 "Tab framework — when to use it" rewritten. Source = `perf_audit_report.md`. Explicit instruction that `perf_audit_report.html` is ignored even if present. Fidelity rules made explicit. Fallback to `<pre class="md-raw">` documented.

**`references/visual_kit.md`** — c004
- "Perf-audit tab rendering" subsection rewritten as "Perf-audit tab rendering — markdown → HTML verbatim". Conversion mapping expanded (blockquotes, h4, fenced code, GFM tables, hr, inline links). Slug rule formalized for all heading levels including subsections (4a, 5c, etc.). Fallback rule documented.
- Missing CSS finally added to the shared `<style>` block: `.md-content` (h1–h4 hierarchy, paragraphs, lists, code, links, hr, blockquote, `:target` highlight), `.md-table` (GFM styling consistent with the rest of the kit), and the new `.md-content pre.md-raw` (monospace fallback for raw markdown).
- Two new Anti-pattern rows: Tab 2 sourcing from `.html` or wrapping perf-audit content in CVR-RCA chrome; sub-headings dropped during the conversion.

**perf-audit-skill (local rollback, not in this repo)**
- The local-only changes to perf-audit-skill that added Step 6 (Write HTML report), `references/visual_kit.md`, and `references/perf_audit_structure.md` are rolled back. perf-audit-skill returns to emitting `perf_audit_report.md` only. These changes were never pushed to the upstream perf-audit-skill GitHub repo, so the rollback is local-only.

### What did not change

- The perf-audit-skill's markdown output. `perf_audit_report.md` is unchanged and remains the canonical text artifact for both Claude's Step 2b reconciliation reasoning and CVR-RCA's Tab 2 display.
- The tab framework itself (sticky bar, JS, anchor scheme `perfaudit-<slug>`). Tab 1 / Tab 2 layout unchanged.
- The cross-tab citation routing table and four-pattern citation phrasings.
- Single-tab / flat-spec reports (perf-audit didn't run / DATA GAP / Organic cascade) — no behavior change.

### Why this design

The v1.19 trust assumption — perf-audit-skill's `.html` would be a faithful conversion of its `.md` — turned out wrong. Once that's established, byte-pasting from `.html` becomes a fidelity hazard. The fix is structural: pin the source to `.md` (the canonical artifact), do the conversion at Tab 2 write-time (under CVR-RCA's control), enforce verbatim fidelity in the conversion rules. The small cost (Claude does the markdown→HTML conversion at every CVR-RCA report write) is worth the certainty that nothing gets paraphrased or dropped. The fallback rule (raw markdown if conversion can't handle something) is the safety net so the spec doesn't become rigid against future perf-audit-skill changes.

---

## [v1.21] — 2026-05-29 — Back-to-top floating arrow

(Originally `[Unreleased]`; tagged retroactively as released since the commit `6bb01c0` was pushed to `origin/main` on the same day.)

**Summary:** A small UX addition. Every report now carries a fixed circular ↑ button in the bottom-right corner; one click scrolls smoothly back to the top of the page. Always visible (no scroll-detection JS to fade in/out), uses the existing `scroll-behavior: smooth` CSS via an anchor link to `<header id="top">` — zero new JavaScript. Hidden on print. Lives entirely in `visual_kit.md` because the chrome is skill-agnostic; any future skill emitting an HTML report inherits it.

### Changes by file

**`references/visual_kit.md`** — c003
- New `.back-to-top` CSS rule: `position: fixed; bottom: 24px; right: 24px;` — 40×40px circular dark-navy translucent button with subtle box-shadow, hover-brightens and lifts 2px.
- `@media print { .back-to-top { display: none; } }` so it doesn't appear in printed/PDF exports.
- Page skeleton example: `<header>` gains `id="top"` as the anchor target; new `<a href="#top" class="back-to-top">↑</a>` placed near the end of `<body>` after `<footer>`.

### What did not change

- No new JavaScript — the existing `html { scroll-behavior: smooth; }` rule (already in the shared style block) handles the scroll animation.
- No interference with the tab-framework JS — that handler only acts when the anchor target is inside a non-active tab pane; `<header id="top">` is outside any tab pane, so the handler delegates to native browser behavior.
- No changes to `report_structure.md`, `SKILL.md`, or any per-skill structure file. Pure visual_kit chrome addition.

---

## [v1.20] — 2026-05-29 — Header dashboards row (Omni + Sentra)

**Summary:** Every CVR-RCA report header now carries a `.dashboards` row with two pill-button links to external CE-scoped analytics dashboards — Omni Analytics and Sentra. Analysts can jump from the report into either dashboard in one click, with the CE filter pre-applied. The chrome (`.dashboards`, `.dash-label`, `.dash-link` CSS plus a placeholder block in the Page skeleton) lives in the shared `visual_kit.md` so any future skill emitting an HTML report can reuse the same pill style. The two specific URL templates (Omni dashboard ID + filter IDs; Sentra base URL) live in CVR-RCA's `report_structure.md` because they are CE-analytics knowledge, not generic chrome. Only the CE ID is substituted at write time — Omni's date params are constant (the dashboard has built-in pre/post comparison logic for last-30-days vs prior-30-days, independent of the RCA's actual pre/post windows); Sentra defaults to its own 30-day window with no URL date parameters available.

### Changes by file

**`references/visual_kit.md`** — c002
- Header CSS gains three rules (`header .dashboards`, `header .dash-label`, `header .dash-link`) for the pill-button row below the existing `.meta` line. Recessed-button styling that visually distinguishes external links from the static meta info.
- Page skeleton example gains a placeholder `<div class="dashboards">` block inside `<header>`, with a comment noting the consuming skill's structure file owns the URL templates.
- Initial Changelog table added to the file (c001 for the v1.19 initial extraction; c002 for this change). The file previously had no changelog table; this commit establishes one going forward.

**`references/report_structure.md`** — c032
- New "Header — CVR-RCA-specific extensions" section inserted at the top of the file (above "Section 1 — Executive Summary"). Documents the Omni + Sentra URL templates with explicit substitution rules.
- Pre-write sanity check gains a third item: the dashboards row must be populated with both links before the report is considered done.

### What did not change

- The rest of the header chrome (eyebrow, h1, meta row with 📅 / 🌍 / 🔗 spans) — unchanged.
- The dashboards row is unconditional — rendered on every CVR-RCA report regardless of CE or RCA direction. No conditional logic.
- Perf-audit's standalone HTML report — does not (yet) emit the dashboards row. The chrome is now available in the shared `visual_kit.md` if perf-audit-skill later wants to add its own dashboard URLs; that's a separate change in the perf-audit repo.

### Why this design

Analysts running an RCA almost always want to cross-reference the CE in Omni or Sentra during interpretation — for traffic decomposition, channel attribution, or month-over-month context the RCA report doesn't carry. Putting the links in the header (rather than buried in Section 3 or a footer) treats them as part of the orientation chrome alongside the pre/post dates and the landing-page URL — which is exactly the analyst's mental model. The chrome/URL split between `visual_kit.md` and `report_structure.md` honors the v1.19 architecture: shared visual primitives go in the kit; skill-specific content (these specific dashboard URLs) goes in the skill's structure file. Future skills emitting HTML reports can adopt the same pill style with one CSS reference; they only need to define their own URL templates.

---

## [v1.19] — 2026-05-29 — Visual kit extraction + perf-audit HTML output + Tab 2 embed-from-HTML

**Summary:** Generalize the report visual system so multiple skills can produce HTML reports in the same visual language without copy-paste drift. Extract skill-agnostic visual primitives (CSS, HTML patterns for metric cards / callouts / action cards / analysis blocks / tables / tab framework / ↗ link-to-table pattern / Slack integration / styling rules / Plotly conventions) from `references/report_structure.md` into a new shared file `references/visual_kit.md`. The remaining content in `report_structure.md` is CVR-RCA-specific structure (Section 1/2/3 macro layout, "What belongs in Section 3" table, CVR-RCA-specific block specs). Perf-audit gets a parallel `references/perf_audit_structure.md` that defines its own section layout on top of the same `visual_kit.md` (an identical copy lives in the perf-audit-skill repo). The perf-audit skill now emits both `perf_audit_report.md` (canonical text record, unchanged) AND `perf_audit_report.html` (NEW polished standalone HTML deliverable, self-contained with visual_kit CSS inlined). CVR-RCA's Step 3 Tab 2 rendering switches from "read markdown + render to HTML inline" to "read perf-audit's HTML, extract body content, paste verbatim" — a byte-paste rather than a comprehension step. Visual quality goes up (both tabs share `visual_kit.md` so they look visually identical); Claude's reading load goes down (no markdown→HTML conversion at Step 3); RCA quality is structurally insulated (perf-audit's investigation phase remains format-agnostic; the HTML render happens after all conclusions are reached). Markdown artifacts remain Claude's input for Step 2b reconciliation reasoning — verbose HTML never enters Claude's reasoning context.

### Changes by file

**`references/visual_kit.md`** — NEW file (c001 in its own changelog)
- Skill-agnostic visual primitives extracted from `report_structure.md`. Contains: shared `<style>` block (CSS for header / container / metric cards / callout / action cards / analysis blocks / verdict lines / tables / shapley flex bar / fixed segment banner / ref-link / tab bar / md-content); Page skeleton; Section label; Metric cards HTML; Root cause callout HTML (Shape A paragraph + Shape B multi-driver bullet); Action card HTML; Analysis block (general pattern); Table with highlight rows; Plotly chart conventions; Anchor ID convention; Styling and language guidelines (rules 1–7); Slack integration & link-to-table styling; Tabbed report structure (full HTML pattern); Anti-patterns.
- Preamble names the file as the report visual kit — any skill producing an HTML report reads this for primitives.

**`references/report_structure.md`** — c031
- Trimmed to CVR-RCA-specific content only. Removed: Styling guidelines, Slack integration, Tab framework, Anti-patterns, Visual Spec (CSS + generic component HTML patterns), Plotly conventions, Anchor ID convention (all moved to visual_kit.md).
- Kept: Section 1/2/3 macro-structure, "What belongs in Section 3" table, URL-level breakdown block, Inventory section format, Session recordings format, Ruled-out dimensions section + block, Mix cascade analysis block, Fixed Segment banner, Geo / Non-Geo overview block, Market context block, Shapley decomposition block, Hypotheses Explored block, Report length calibration.
- Added preamble pointing to visual_kit.md. Reordered to nest CVR-RCA-specific block specs under a new "## CVR-RCA-specific block specs" h2 parent.

**`SKILL.md`** — c035
- File-role descriptions updated: `report_structure.md` renamed as "CVR-RCA-specific report structure"; new `visual_kit.md` description as "shared visual primitives" added.
- Step 3 lazy-load instruction extended to read `visual_kit.md` alongside `actions.md` + `report_structure.md`.
- Step 3 "Tab framework — when to use it" subsection rewritten: read `perf_audit_report.html`, extract body content, paste verbatim. Fallback to legacy md→HTML render if HTML missing.

**Perf-audit-skill repo** (paired release, separate repo)
- New `references/perf_audit_structure.md` (c001) defines perf-audit's section layout on top of visual_kit primitives. Section 1 (verdict callout + 5 metric cards), Section 2 (Recommended Actions with Diagnose-and-fix / Audit-and-document / Scale-with-guardrails sub-templates), Section 3 (8–9 supporting analysis blocks: CE Overview, Channel Breakdown, Paid Deep Dive, CPC 3-Lens, Coverage + Matchmaking, Funnel Reconciliation, External Dynamics, Red Flags, Monthly Trajectory). Anchor scheme `perfaudit-<slug>`. Custom-block guidance for novel findings. Embedding spec for CVR-RCA Tab 2.
- New `references/visual_kit.md` — byte-identical copy of cvr-rca's. Manual sync policy documented (when visual_kit changes in cvr-rca, copy to perf-audit; revisit if a third user appears).
- `SKILL.md` gains Step 6 — Write HTML report. Lazy-loads visual_kit.md + perf_audit_structure.md at this step. Renders `perf_audit_report.html` from the same intermediate findings as the markdown (no new investigation work). Markdown artifact unchanged.

### What did not change

- Investigation logic. Perf-audit Steps 0–5 unchanged; CVR-RCA Steps 1–2b unchanged.
- Markdown artifacts. `perf_audit_summary.md` and `perf_audit_report.md` are still produced and still the canonical text record. They remain Claude's input for Step 2b reconciliation reasoning. HTML is opaque at the embed step.
- The visual language. CVR-RCA reports look identical to v1.18 output (same chrome, same patterns — just now read from visual_kit.md instead of report_structure.md).
- Cross-tab anchor scheme, citation routing table, four-pattern citation phrasings.

### Why this design

The v1.18 architecture had perf-audit emit markdown only, and CVR-RCA rendered that markdown to HTML inline inside Tab 2. Two problems: (1) every CVR-RCA run re-did the markdown→HTML conversion, paying tokens for work that could be done once inside perf-audit; (2) the inline render used `.md-content` styling rather than visual_kit's polished `.analysis-block` chrome, so Tab 2 visually felt foreign next to Tab 1. v1.19 fixes both by having perf-audit emit HTML directly using the same visual_kit both skills now share. The investigation phase stays format-agnostic — perf-audit reaches all its conclusions before the HTML render at Step 6 — so RCA quality is structurally insulated from the format change. And the extracted visual_kit is the foundation for the next skill that produces HTML reports (experiment-RCA, supply-RCA, etc.): they reference the same primitives, define their own structure file, and bundle into CVR-RCA's tab framework with no additional engineering.

---

## [v1.18] — 2026-05-29 — Bulleted shape for Section 1 callout

**Summary:** Section 1 callout answers gain a second shape — lead claim + bullet list — for multi-mechanism findings. The existing paragraph form remains the default for single-mechanism findings; Claude picks the shape that matches the finding. No threshold rule, no word cap. New styling rule 7 makes the preference explicit ("prefer the bullet shape when a callout enumerates drivers"). The bullet form is documented in the Visual Spec with its own CSS and HTML pattern so it inherits the existing callout typography (15px dark text) and ↗ ref-link placement convention.

### Changes by file

**`references/report_structure.md`** — c030
- New styling rule 7 added to the existing rules 1–6 list: prefer bullet shape when enumerating drivers.
- Section 1c spec rewritten to document both shapes (paragraph + lead claim with bullet list); removes the prescriptive "1–3 sentences" upper bound on `.a` answers since multi-driver answers naturally extend beyond that.
- Visual Spec gains CSS for `.callout-item .a ul`, `li`, `li strong` — tight bullet spacing that inherits the existing callout typography.
- Visual Spec gains a "Shape B — multi-driver" HTML pattern alongside the existing single-mechanism pattern. The two shapes can mix within the same callout — each `.callout-item` chooses independently.

### What did not change

- The three-question structure (What broke / Why / When for declines; What drove improvement / What's holding back / When for improvements) — unchanged.
- The colored left border (`#e53935` red for decline, `#2e7d32` green for improvement) and the heading — unchanged.
- The ↗ ref-link convention — same placement rules, just one arrow per bullet instead of stacked inside a paragraph.
- Single-mechanism reports — render identically; the paragraph shape stays the default for them.

### Why this design

The most-scanned section of the report was becoming the hardest to scan when findings were multi-mechanism. The spec only described the paragraph form, so the natural fallback for a 5-driver answer was "paragraph with inline `(1)/(2)/(3)` markers and embedded bold tags" — visually dense, hard to skim. Documenting the bullet shape as the second-class option with its own HTML pattern lets Claude pick the shape that fits the finding instead of force-fitting everything into prose. The change is purely additive — single-mechanism callouts continue to render in paragraph form, so no existing report regresses.

---

## [v1.17] — 2026-05-29 — Lazy-load references by phase

**Summary:** Claude no longer reads all four reference files upfront. Reading is deferred to the phase that needs the file: `context.md` + `hypothesis.md` at Step 2 (investigation), `actions.md` + `report_structure.md` at Step 3 (writing the report), `evals/evaluator.md` at Step 4. Step 1 reads only `SKILL.md`. Files are loaded **whole** when loaded — section-level reads are explicitly rejected because they would constrain the cross-pattern reasoning surface that produces non-obvious findings (cross-cuts, catalogue-change recognition, the connections between query templates and historical patterns). The change is about *when* to load, not *what* to load. A new "On reading references — a note on freedom" subsection in SKILL.md codifies the operating principle: Claude has complete freedom to form hypotheses, design queries, and follow the data wherever it leads; references are the shared context that makes that freedom precise rather than vague. `actions.md` is deliberately deferred to Step 3 so the Step 2b synthesis reaches the root cause without being biased toward existing action templates — novel root causes can produce novel actions, not just remixes of the library.

### Changes by file

**`SKILL.md`** — c034
- "Before you begin" rewritten — reference reads moved out of the upfront block and into per-phase opening instructions. New "Per-phase reads" table at the top of the section.
- New "On reading references — a note on freedom" subsection between the file-role descriptions and "Your role". States the freedom principle explicitly; positions `context.md` as the data vocabulary, `hypothesis.md` as starting-point patterns (not a menu), `actions.md` as the Step 3-only cause-to-action library.
- Step 2 opening — new instruction at the top: read `context.md` + `hypothesis.md` now, both fully.
- Step 3 opening — new instruction at the top: read `actions.md` + `report_structure.md` now, both fully. Includes the explicit rationale for deferring `actions.md` to Step 3 (clean synthesis at Step 2b without action-template bias).
- Step 4 unchanged — already reads `evals/evaluator.md` at that phase.

### What did not change

- Reference content — no file split, no section subdivision, no rewording of patterns. `context.md`, `hypothesis.md`, `actions.md`, `report_structure.md` are unchanged.
- Investigation logic — Steps 1, 2, 2b, 4 work the same way; only the timing of reference reads changed.
- Slack / perf-audit sub-agent fire-and-forget timing.
- v1.16 Claude-writes-HTML workflow.

### Why this design

The original upfront-read instruction made sense when the skill was smaller, but the four references together are now ~85 KB and most of that content is not needed at most phases. Loading `actions.md` 30+ minutes before Step 3 risks biasing the Step 2b synthesis toward action-template matching; loading `report_structure.md` during investigation pulls Claude toward report-shape thinking when it should be doing investigation thinking. Lazy-loading by phase preserves the same total context volume across a run but ~halves the concurrent volume at any single phase. The discipline of "whole file or nothing" preserves the cross-pattern reasoning that produced CE 252's catalogue-change finding and CE 243's cross-cut leaf — splitting files into per-topic sub-files would constrain exactly the creative connection-making that the skill is designed to encourage.

---

## [v1.16] — 2026-05-29 — Retire spec-JSON + render.py pipeline; restore Claude-writes-HTML

**Summary:** v1.14 added a `report_spec.json` + `scripts/render.py` rendering pipeline to support a multi-tab deliverable (CVR-RCA + Paid Performance Audit). v1.15 added escape-hatch components (`analysis_block`, `raw_html`) and left-aligned the tab bar. Both releases solved a real tab problem but introduced a quality regression: render.py's 19 built-in component renderers (`metric_cards`, `mbho_channel_table`, `shapley_waterfall`, `dimension_table`, `experience_table`, `trend_chart`, `action_cards`, etc.) ship inline-styled HTML from pre-v1.13 — older visual idioms that look utilitarian next to the polished `.analysis-block` chrome the v1.15 template defined. When a report mixes built-ins with escape-hatch blocks, two visual eras of the skill end up side-by-side in one document. CE 252 (Louvre, May 27) was hand-authored before v1.14 shipped and remains the quality target; CE 243 (Eiffel Tower, May 28) was rendered through the pipeline and showed the visual drift. v1.16 retires the pipeline for CVR-RCA content and restores the v1.13-era Claude-writes-HTML workflow. The tab framework survives as a documented HTML pattern (tab bar + `.tab-pane` wrappers as a copy-pasteable block in `report_structure.md`); perf-audit markdown is rendered to HTML inline as part of writing the report, with content verbatim. Freedom of movement is total — no component dispatcher to constrain novel findings, no spec JSON to maintain, no rendering pipeline to debug.

### Changes by file

**`SKILL.md`** — c033
- Step 3 rewritten: "Write `report.html` directly, follow `report_structure.md` exactly." Removed the `report_spec.json` instruction, the `scripts/render.py` invocation, and the entire "Investigation drives the report, not the inverse" subsection (escape-hatch components no longer needed).
- Tab framework — when to use it: rewritten as a binary decision (two-tab if perf-audit ran successfully, single-tab flat otherwise) with pointers into `report_structure.md` for the HTML patterns. No more spec-JSON shape.
- c032 entry annotated as superseded by c033.

**`references/report_structure.md`** — c029
- "Tabbed report structure → Spec shape" section rewritten as a copy-pasteable HTML pattern: tab bar outside `.container`, two `.tab-pane` wrappers inside, tab-switching JS at end of body. No JSON.
- New "Perf-audit tab rendering — markdown → HTML inline" subsection documents the verbatim conversion mapping Claude performs.
- Single-tab / flat layout instruction clarified: omit the tab bar and `.tab-pane` wrappers entirely — do not emit vestigial tab markup.
- Section 3 "What belongs in Section 3" table: the two escape-hatch component rows (`analysis_block`, `raw_html`) replaced with a single "Custom analysis block" row pointing to the `.analysis-block` HTML pattern.
- Section opener text updated to reflect the Claude-writes-HTML model — "no rendering-pipeline constraint on what can ship; the guardrails are the HTML patterns in the Visual Spec section."

**`~/.claude/commands/cvr-rca.md`** (slash-command file, outside this repo)
- Step 3 reverted: "Write `report.html` directly. Follow `references/report_structure.md` exactly." Binary tab decision. No render.py invocation.

**`scripts/render.py`**
- No longer invoked by the workflow. File stays on disk as a reference implementation; can be cleaned up in a future release.

**`templates/report.html`**
- No longer invoked by the workflow. CSS and tab JS are now patterns in `report_structure.md → "Visual Spec — HTML patterns"` that Claude copies into the report directly.

### What did not change

- All other v1.15 improvements stay: pre-write sanity check, styling rule 6 (plain English for derived metrics), Slack-unavailable disclosure card, anti-pattern row on `days_to_first_available_date`, canonical-source rule for `inventory_availability`, demoted-proxy rule in `hypothesis.md`. None of these depended on the rendering pipeline.
- Tab framework as a *concept* — still present. The CVR-RCA + Paid Performance Audit two-tab deliverable is unchanged. Only the *mechanism* changed: from spec-JSON-driven to HTML-pattern-driven.
- Cross-tab anchor scheme (`perfaudit-<slug>`), citation routing table, four-pattern citation phrasings — all unchanged.
- Investigation logic (cascade, L2+, sub-agents, four-pattern reconciliation, evaluator). Steps 1, 2, 2b, 4 are untouched.
- Perf-audit skill — independent at `aaradhyaraiHO/perf-audit-skill`, ships `perf_audit_report.md` as before.

### Why this design

v1.14 was solving the right problem (single-deliverable C-level tabs) with the wrong tool (a render pipeline taking over all output). Component dispatchers are appropriate when you have many consumers each producing a different spec; the CVR-RCA has exactly one consumer (Claude) producing exactly one report per CE. Forcing that consumer through a 19-component schema, with an escape hatch for novel findings, added friction and constrained quality without adding any reproducibility the workflow actually needs. The simpler model — Claude reads `report_structure.md`, copies the CSS and HTML patterns, writes the report directly — matches the v1.13 era that produced CE 252's quality, and the tab feature drops in as a copy-pasteable HTML block rather than a JSON spec. The skill is simpler to maintain, the output is more polished, and the freedom-of-movement guarantee is preserved by construction (Claude writes HTML; there is nothing to escape).

---

## [v1.15-superseded] — 2026-05-28 — Left-aligned tabs + escape-hatch components + slash-command sync

**Note:** v1.15 shipped briefly and was superseded by v1.16 the same day after a quality-regression review on the first production use (CE 243). The escape-hatch components (`analysis_block`, `raw_html`) and the spec-JSON pipeline they fixed have been retired in v1.16. The two non-pipeline improvements from v1.15 — left-aligned tab placement and the slash-command preamble correction — survive v1.16 (the tab placement as an HTML pattern; the slash-command correction is partially reverted to point at the Claude-writes-HTML workflow). The original v1.15 entry is preserved below for change-log fidelity.

---

## [v1.15-original] — 2026-05-27 — Left-aligned tabs + escape-hatch components + slash-command sync

**Summary:** Three structural improvements driven by the CE 252 (Louvre) RCA session — one cosmetic, one architectural, one workflow. **(1) Tab placement** — the tab bar moves out of the centered `.container` and becomes a full-viewport-width sticky band with buttons left-anchored to the 40px header content edge. Survives any monitor width and matches standard tabbed-document conventions (Notion, Linear, Google Docs). Multi-tab reports gain visual consistency between the header and the tab bar; single-tab / flat-spec reports are byte-identical to v1.14. **(2) Escape-hatch components** — `analysis_block` and `raw_html` are added to render.py's dispatcher so Claude can ship novel investigation findings the 19 built-in components can't express. `analysis_block` wraps arbitrary HTML in the standard Section-3 chrome (visual consistency is free); `raw_html` is pure passthrough for the rare case where the standard chrome is wrong. SKILL.md Step 3 gains the principle "investigation drives the report, not the inverse" plus a guard rail against using the escape hatch for cosmetic deviation from existing components. Together these mean Claude has the same freedom of movement it had when writing HTML directly, with the determinism and aesthetic guardrails of the templated renderer. **(3) Slash-command preamble sync** — the `/cvr-rca` slash-command Step 3 instruction is updated from "write report.html directly (no render.py)" to "write report_spec.json, then run scripts/render.py". Resolves a latent v1.14 contradiction where the slash-command preamble said the opposite of what SKILL.md prescribed. A new "if this preamble ever contradicts SKILL.md, follow SKILL.md" guard rail catches future documentation drift.

### Changes by file

**`scripts/render.py`** — c032 + c033
- `assemble()` now emits the tab bar into a separate `tab_bar_html` variable, threaded through a new `{{TAB_BAR}}` template substitution slot that lives outside `.container`. When `tabs[] < 2`, the slot resolves to an empty string — no regression for single-tab / flat-spec output.
- New `render_analysis_block()` function — wraps arbitrary HTML in the standard `.analysis-block` chrome (rounded card, border, padding, title, optional verdict line, optional anchor id).
- New `render_raw_html()` function — pure passthrough with optional Plotly figure registration.
- Two new dispatcher branches (`analysis_block`, `raw_html`) before the unknown-component red-error fallback.
- `SECTION_TITLES` table updated — both new components mapped to `(None, "")` so the outer section wrapper doesn't add an extra heading.
- Module docstring extended with the two new schemas.

**`templates/report.html`** — c032
- New `{{TAB_BAR}}` placeholder between `<body>` and `<div class="container">`. The tab bar now stretches the full viewport with `padding: 0 40px` aligning the first button with the header's content edge.
- `.tab-bar` CSS updated — dropped the `margin: 0 -24px 24px` negative-margin trick that was compensating for `.container`'s `padding: 0 24px`; bar now sits naturally at viewport width.
- Comment block above `.tab-bar` explains the v1.15 rationale so future maintainers don't accidentally move it back inside `.container`.

**`references/report_structure.md`** — c027 + c028
- New "Tab bar placement — full-width, left-anchored" subsection under "Tabbed report structure → Visual differences from CVR-RCA content" explaining the placement, the rationale, and the byte-identical guarantee for single-tab specs.
- Two new rows in "What belongs in Section 3" table — `analysis_block` (the escape hatch for novel findings, with visual consistency) and `raw_html` (true passthrough, rare).
- Section opener gains one sentence pointing readers to the escape hatches when no built-in component matches the finding.

**`SKILL.md`** — c032
- New "Investigation drives the report, not the inverse" subsection at the end of Step 3 with both escape-hatch schemas (analysis_block, raw_html), a worked example for a cross-cut finding, and a guard rail prohibiting cosmetic use of the escape hatches.

**`~/.claude/commands/cvr-rca.md`** (slash-command file, outside this repo)
- Step 3 instruction updated from "Write report.html directly (no render.py — Claude writes HTML)" to "Write report_spec.json per SKILL.md Step 3, then run scripts/render.py". Pointer to analysis_block / raw_html for novel findings.
- New guard line: "If this slash-command preamble ever contradicts SKILL.md, follow SKILL.md — it is the source of truth for the workflow; this Quick Reference is a convenience wrapper."

### What did not change

- The 19 built-in component renderers — no signatures changed, no behavior changes.
- Single-tab / flat-spec rendering — byte-identical to v1.14.
- Cross-tab anchor scheme, citation routing table, four-pattern citation phrasings.
- Tab-switching JS in `templates/report.html` (click handlers, hash-on-load, Plotly resize on tab-show) — all preserved, all still work.
- Perf-audit tab markdown rendering — the `.md-content` styling, anchor-prefix injection, and slugification rules are unchanged.
- The unknown-component red-error fallback — still fires for typos in `component` names; never fires for legitimate novel findings (use `analysis_block` instead).

### Why this design

The cosmetic fix (left-aligned tabs) and the architectural fix (escape hatches) ship together because they share a principle: **the rendering layer serves the investigation, not the other way around.** Centered tabs were a rendering-driven design choice that read as visually disconnected on wide monitors; the 19-component cap was a rendering-driven constraint that could silence novel findings; the slash-command preamble drift was a documentation-driven contradiction that forced Claude to choose between two conflicting instructions. All three inverted the relationship between the renderer and the investigation. The v1.15 design restores the right order: investigations surface findings, the report shape accommodates them, with visual guardrails kept intact and a single source of truth for the workflow.

---

## [v1.14] — 2026-05-23 — Tabbed report framework (single deliverable for C-level audits)

**Summary:** The CVR-RCA report becomes a multi-tab HTML deliverable. The first tab is the existing CVR-RCA report (unchanged). When the perf-audit sub-agent ran (cascade fixed on Paid), a second tab — **Paid Performance Audit** — is rendered inline from `perf_audit_report.md` so stakeholders can read the full perf-audit without opening a separate file. Cross-tab citations work natively: every `(per perf-audit ↗)` style reference inside the CVR-RCA tab deep-links into the right perf-audit section, switching tabs and scrolling automatically. The framework is **scalable** by design — adding a future third tab (experiment-RCA, supply-RCA, anything else with markdown output) is a one-line config entry, not a rewrite. Backward compatibility is absolute: any run where the perf-audit didn't fire (Organic segment, not installed, DATA GAP) produces the existing flat report — byte-identical to v1.13 output. The perf-audit skill itself is **not modified** — CVR-RCA renders its markdown at report-build time, so the two skills retain independent release cadences (perf-audit ships at [aaradhyaraiHO/perf-audit-skill](https://github.com/aaradhyaraiHO/perf-audit-skill)).

### Changes by file

**`scripts/render.py`** — c031
- New stdlib-only markdown-to-HTML renderer (~150 lines). Handles ATX headings, GFM pipe tables, ordered/unordered lists, bold/italic/code/links, horizontal rules, HTML comment passthrough. Heading IDs are injected at render time with a configurable prefix (default `<tab-id>-`) so cross-tab anchors stay stable and namespaced.
- New `render_markdown_tab(path, anchor_prefix)` — reads a markdown file, renders to HTML, wraps in `<div class="md-content">`. Graceful fallback to a "source file not found" placeholder if the path doesn't exist; report still renders.
- New `render_tab_bar(tabs)` — emits the sticky `<div class="tab-bar">` above panes; only called when `tabs[]` length ≥ 2.
- `assemble()` extended to accept the new `tabs[]` spec shape. With ≥2 tabs, tab bar + panes are emitted; with 1 tab or no `tabs[]` key, content renders flat (legacy backward-compatible path).
- `main()` passes `spec_dir` into `assemble()` so `tabs[].source.path` resolves relative to the run directory.

**`templates/report.html`** — c031
- Sticky `.tab-bar` with pill-style `.tab-button` (dark theme, blue accent for active tab); `.tab-pane` uses `display:none` so inactive panes don't pollute browser scroll history.
- `.md-content` typography (h1–h4, p, ul/ol, code, links, hr) + `.md-table` styling that matches the CVR-RCA tab's table look so embedded markdown reports don't feel foreign.
- ~50-line vanilla-JS handler (zero dependencies, zero build step): click handlers on tab buttons, delegated handler on `a[href^="#"]` links that switches tabs when an anchor targets a non-active pane, hash-on-load tab activation, Plotly `Plots.resize` for charts in newly-visible panes. Native `:target` highlight + `scroll-behavior: smooth` are preserved.

**`references/report_structure.md`** — c026
- New top-level section "Tabbed report structure" — when tabs appear vs flat layout, full spec shape, per-tab keys, cross-tab anchor scheme, citation routing table (which CVR-RCA finding type links to which `#perfaudit-*` anchor), four-pattern citation phrasings mirroring the Slack patterns, visual-differences explainer, conditional-tab logic.
- "Citation format split" section extended with the perf-audit phrasing (`per perf-audit ↗`, `perf-audit named: <event · date> ↗`).

**`SKILL.md`** — c031
- Step 3 instruction added: inspect `<run_dir>/perf_audit_report.md`; if present and non-empty (and verdict was not `DATA GAP: no campaigns`), write the multi-tab spec shape; otherwise write the legacy flat spec. CVR-RCA tab is unconditional, perf-audit tab is conditional.
- Step 2b check #10 extended: every Pattern A/B/C/D citation must carry a `↗` to the routing-table anchor; phrasing and routing spec lives in `report_structure.md`.

### What did not change

- **The perf-audit skill** — runs as-is at `aaradhyaraiHO/perf-audit-skill`. CVR-RCA renders its markdown at report time; the two skills stay independently maintainable.
- **CVR-RCA tab content** — Sections 1, 2, 3 render exactly as v1.13 inside the first tab. No section was moved or restyled.
- **`report_spec.json` schema for legacy specs** — flat `{"sections": [...]}` is still accepted. Output for single-tab specs is byte-identical to v1.13.
- **PyPI dependencies** — none added. The markdown renderer is stdlib-only.

### Why this design

A C-level RCA deliverable needs to be one artifact a stakeholder can open, scroll, and trust — not a folder of files. At the same time, perf-audit's release cadence is owned by a different team; bundling its content into CVR-RCA's HTML at build time (rather than vendoring its code or copying its schemas) is the only design that gives stakeholders one file while keeping the two skills independently maintainable. The tab framework also future-proofs the report: experiment results, supply audits, cohort deep-dives can all become tabs without changing the CVR-RCA tab's structure.

---

## [v1.13] — 2026-05-22 — Perf-audit companion-skill integration (plug-and-play sub-agent)

**Summary:** CVR-RCA gains a paid-traffic enrichment layer by spawning a separate companion skill — [`perf-audit-skill`](https://github.com/aaradhyaraiHO/perf-audit-skill) — as a background sub-agent whenever the L1 cascade fixes on Paid. Mirrors the Slack fire-and-forget pattern exactly: spawn at the end of the cascade, do not consult during L2+ dimension cuts, read the verdict only at Step 2b synthesis. Two skills stay independent — no schemas, queries, or diagnostic logic moved between them. The sub-agent runs the full perf-audit on the CVR-RCA's pre/post date windows and writes a structured summary (overall verdict, SIS / CPC / Paid CVR trends, campaign status, one-sentence key finding, optional surprise hypothesis) to `<run_dir>/perf_audit_summary.md`. Step 2b check #10 reconciles the verdict using the same four-pattern model as Slack (A direct corroboration, B mechanism explanation, C reframing context, D testable gap, Reject). Funnel data is deliberately excluded from the summary to avoid attribution conflicts with the Mixpanel funnel — CVR-RCA owns the funnel numbers, perf-audit owns the traffic-and-campaign side. Distribution via convention: companion install at `~/.perf-audit-skill/` (added as optional Step 5 in INSTALL.md), with env-var override and sibling-directory + legacy fallbacks. CVR-RCA runs fully without it — if path resolution fails, the run logs `Perf-audit skill not installed — skipped` and continues. The integration is additive evidence, never a gate.

### Changes by file

**`SKILL.md`** — c030
- New section "Perf-audit context — fire and forget (Paid-side only)" inserted at the end of the L1 cascade (immediately before L2+). Trigger conditions, skip conditions, four-step path resolution, full spawn block with structured summary shape, context-isolation note.
- Step 2b gains check #10 "Perf-audit reconciliation" with four-pattern routing (A/B/C/D) + Reject + DATA GAP handling. Explicit reaffirmation that perf-audit is consulted only at this point — never during L2+ — so the data-driven branches must reach their own leaves first.
- Evidence inventory entry shape specified (Verdict / Key metrics / Campaign issues / Implication / Source).
- Root cause callout requirement: Patterns A, B, C must reflect the perf-audit verdict in the final report.

**`references/hypothesis.md`** — c030
- LP2S first-pass branches gain a "Paid fixed segment — perf-audit background context" paragraph explaining the sub-agent runs in parallel and the verdict folds in at Step 2b, not during dimension cuts.
- Mix first-pass branches gain a "Perf-audit background context (Level 2 and Level 3 exits)" paragraph explaining how Pattern B in check #10 routes campaign-level *why* findings into Layer 1 narrative without a second query.

**`INSTALL.md`** — c030
- New optional Step 5 "Install the perf-audit companion skill". Detects existing install, prompts user, fetches from `aaradhyaraiHO/perf-audit-skill` to `~/.perf-audit-skill/`. Previous Step 5 (Confirm) renumbered to Step 6.

### What did not change

- `references/context.md` — perf-audit owns its own data layer (table schemas, queries, diagnostic trees). CVR-RCA does not learn `ads_campaign_stats` or `google_ads_campaign_stats` shapes.
- The perf-audit skill itself — runs as-is, no fork or vendoring.
- Report structure — perf-audit findings appear as evidence entries and Section 3 Market Context rows, never as new sections.
- No blocking dependency — every existing CVR-RCA path continues to work without perf-audit installed.

### Why this design

The plug-and-play sub-agent pattern keeps both skills independently maintainable: perf-audit releases on its own cadence at `aaradhyaraiHO/perf-audit-skill`, CVR-RCA on its cadence here, and the bridge is a thin spawn-and-read contract. The fire-and-forget timing — same as Slack — protects the integrity of the data-driven investigation: dimension cuts reach their own leaves before the perf-audit verdict is read, so traffic-quality signals corroborate or surprise a completed picture rather than steering branch selection. This is the difference between *evidence weighting* (good) and *evidence biasing* (bad).

---

## [v1.12] — 2026-05-22 — Bidirectional RCA support, four-pattern Slack reconciliation, link-to-table styling, jargon preservation

**Summary:** Largest skill release since v1.0. Three connected expansions land together. **(1) Bidirectional RCA support** — the skill now treats CVR improvements as first-class investigations alongside declines. New "Improvement direction" first-pass branch sets in `hypothesis.md` (LP2S / S2C / C2O / Mix in the positive direction). New bidirectional Pattern 11 (Catalogue change — TGID launch, disablement, restructure) with data-driven trigger and query template in `context.md`. New "Improvement direction — action templates" library in `actions.md`: **Protect** / **Extend** / **Investigate-headwind** sub-templates with starter actions and DRIs. Report-structure spec gains improvement-case headwind magnitude threshold (<~10% of ΔCVR → fold into sub-bullet), sign-aware Shapley flex bar for mixed contributions, and direction-aware scoring guidance in the evaluator. Decline path is preserved and strengthened — no decline behaviour is weakened by the bidirectional work; cross-cut trigger rule rephrased to "concentrated movement (in either direction)" with identical threshold. **(2) Four-pattern Slack reconciliation model** — Step 2b check #9 rewritten. Every signal classifies into Pattern A (direct corroboration), B (mechanism explanation), C (reframing context), D (testable gap), or Reject. Each pattern routes to a specific surface in the report: A elevates Section 3 verdict subtext citations (decline-specific), B drives Layer 1 narrative weaving + Market Context block, C drives Layer 2 Important Context callout-item + Market Context block, D triggers a one-query test with `(prompted by Author · date ↗)` citation. Mandatory timeframe-citation rule for different-period Slack metrics. One-citation-per-concept rule. Reaffirms that Slack is consulted **only** at Step 2b — never during L0/L1/L2 — the fire-and-forget pattern is deliberate. New "Slack signal classification" reference table in `hypothesis.md`. High-value gap categories listed for Pattern D (assortment changes, pricing levers, content updates, supplier changes, catalogue events). **(3) Link-to-table styling + jargon preservation.** Every Section 3 analysis block now carries an `id` attribute; canonical anchor ID convention listed in `report_structure.md`. New `.ref-link` CSS (small ↗ icon, blue-grey, smooth scroll, `:target` highlight). ↗ used in Section 1 callout, Section 2 action cards, Hypotheses Explored "Test run" column — never inside Section 3 verdict lines or subtexts. Citation format split: bare `↗` for internal navigation, `Source · date ↗` for Slack citations. New styling rule 5: preserve Headout-native jargon (WBR, SP, GBV, RR vs plan, TGID, TID, VID, CR%, FabriGPT, MB / HO, LP2S, S2C, C2A, A2O, C2O) — paraphrasing reduces stakeholder trust by hiding the source. Does not override the existing investigation-internal-labels-translated rule. **(4) Step 4 footer hardened** — the two output lines (`Evaluation → …` and `[Total X/35] · …`) are the only chat output at end of run. No narrative summary, no Slack recap, no highlights block. **(5) Same-period vs different-period data boundary** documented in `context.md` to prevent fabricated YoY figures while allowing external reframing context.

### Changes by file

**`SKILL.md`** — c029
- Step 2b check #9 rewritten with four-pattern classification (A/B/C/D) + Reject. Explicit reaffirmation that Slack is consulted only at this point.
- Pattern A on declines: citation-elevation rule for DRI-bound actions.
- Pattern C: timeframe-citation rule made mandatory when Slack timeframe ≠ pre/post.
- Pattern D: high-value gap categories listed (assortment changes, pricing levers, content updates, supplier changes, catalogue events).
- One citation per concept rule added.
- Step 4 footer hardened — two output lines are the *only* chat output.
- Session recordings rule extended to improvement loci (decline = look for failure; improvement = verify smooth flow + surface new UI).
- L2+ section gains direction-sensitive language and pointer to `hypothesis.md → "Improvement direction"` when CVR improved.
- Catalogue change called out as a first-class data-driven hypothesis.

**`references/report_structure.md`** — c025
- New "Slack integration & link-to-table styling" section: three-layer model, four-pattern cross-reference table, timeframe-citation rule, Slack-corroboration-upgrades-evidence rule, ↗ link-to-table pattern with usage and citation-format-split rules.
- New Styling rule 5: preserve Headout-native jargon (does not override rule 1).
- Section 1c gains magnitude threshold for "What's holding it back" (improvement variant).
- Section 2 gains improvement-direction action card sub-spec (Protect / Extend / Investigate-headwind).
- Section 3 ordering adds item 6.5 Market Context (conditional).
- New "Market context & operational signals" HTML block spec.
- Shapley block gains sign-aware flex bar rule.
- Visual Spec gains `.ref-link` CSS, scroll-behavior, `.analysis-block:target` highlight.
- New "Anchor ID convention" section listing canonical IDs.
- "What belongs in Section 3" table gains rows for Weekday composition and Market Context.

**`references/hypothesis.md`** — c018
- Cross-cut trigger rule rephrased to "concentrated movement (in either direction)" — same threshold, broader language.
- New "Improvement direction — first-pass branches" section: LP2S/S2C/C2O/Mix in positive direction.
- New "Pattern 11: Catalogue change (bidirectional)" — TGID launch, disablement, restructure as first-class hypothesis.
- New "Slack signal classification" reference table — four patterns + Reject, with high-value gap categories for Pattern D.

**`references/context.md`** — c027
- New "Catalogue change" query section: `dim_experience_management` first-appearance scan (authoritative) plus `product_rankings_features` fallback. Data-driven trigger, no Slack input required.
- New "Same-period vs different-period external metrics" section: prevents fabricated YoY figures while allowing external reframing context via the Layer-1 Slack citation format.

**`references/actions.md`** — c005
- New Root Cause 11: Catalogue change (bidirectional decline/improvement actions).
- New "Improvement direction — action templates" library: Protect, Extend, Investigate-headwind sub-templates.
- New "Slack-corroboration upgrade on decline actions" rule.

**`evals/evaluator.md`**
- New "Direction-aware scoring note" — semantic translation guide for improvement RCAs.
- Theme 3 (Investigation Effort) gains structural-delta-based depth calibration: shallow investigation is correct for small structural deltas (<+0.15pp).

**`templates/report.html`**
- `.ref-link` CSS added to the shared template, with usage guidance comment.
- `html { scroll-behavior: smooth }` and `.analysis-block:target` highlight added.

---

## [v1.11] — 2026-05-21 — Slack context layer (retroactive entry)

**Summary:** Added Slack context layer to the investigation. A fire-and-forget sub-agent is spawned at the top of Step 2 (after `summary.json` is read, before the data-driven investigation starts) and runs three searches: CE-specific global (pre_start − 14 days → post_end), market channel read (pre_start → post_end), and #tf-bugalert (post_start − 2 days → post_end). Output written to `<run_dir>/slack_context.md` in four buckets: Platform/Bug, Supply/Inventory, Campaign/Traffic, CE-specific mentions. The main agent never waits for it — Slack is consulted only at Step 2b. Step 2b gains check #9 (Slack context reconciliation) with corroborate / test gap / reject classification. `report_structure.md` gains optional 5th "Source" column in hypotheses explored table and inline citation format. Sub-agent instruction set lives in `references/slack_context_guide.md`. *(This entry was missed when the v1.11 commit was pushed on 2026-05-21; added retroactively for completeness — see SKILL.md c028 for full file-level detail.)*

---

## [v1.10] — 2026-05-21 — Parallel first-pass batch, cross-cut investigation, inventory/completeness improvements

**Summary:** Three sets of changes bundled together. (1) First-pass branch set now runs via parallel sub-agents — each sub-agent receives only the SQL, an output path, and an explicit output contract (no reference files), enforcing context isolation. Main agent writes all SQL before spawning, waits for the full batch, then synthesises from the combined picture. Batch JSONs saved to `<run_dir>/batch_<cut_name>.json`. (2) Cross-cut added as a first-class investigation step with a formal trigger rule (≥8pp absolute or ≥20% relative), enumerated cross-cuts by funnel step, and a generic 2-dimension query template in `context.md`. (3) Inventory queries overhauled: period-median queries (APPROX_QUANTILES) replace single-date snapshots, bridge table fixed to `dim_experience_management WHERE variant_status = 'Active'`, time-series interpretation rewritten with trend-based classification, multi-TGID verdict patterns added to `report_structure.md`. Investigation completeness rules tightened across SKILL.md c022–c027.

### Changes by file

**`SKILL.md`** — c027
- "Run all branches within a level in parallel" replaced with a five-step spawning protocol. Each sub-agent receives exactly: complete SQL, output path (`<run_dir>/batch_<cut_name>.json`), and output contract. No reference files passed — context isolation enforced. Main agent waits for all results before synthesising. Transcript section opened before spawning, results filled after batch completes. Failure handling: missing JSON = DATA PULL FAILURE, log and continue, do not re-query inline. Applies to first-pass branch set only; deeper levels remain sequential.

**`references/context.md`**
- Cross-cut query template: generic 2-dimension query, funnel step substitution table, worked A2O example (`device_type × experience_id`).
- Inventory period-median queries (APPROX_QUANTILES across all extracted_dates in window) replace single-date snapshots.
- Bridge table fixed from `dim_tours` to `dim_experience_management WHERE variant_status = 'Active'`.
- Time-series interpretation guide rewritten: trend-based classification (sustained depression, onset event, gradual decline, episodic dips). Artifact detection rule for synchronised zeros.

**`references/hypothesis.md`**
- Cross-cut section: trigger rule (≥8pp absolute or ≥20% relative), common cross-cuts by funnel step (A2O, S2C, LP2S, C2A), three-outcome interpretation guide.
- TGID selection simplified to judgment-based language (removed rigid Case A/B/C).
- TID scoping rule: single depleted TID → individual scope; multiple depleted → TGID aggregate; mixed → depleted only.
- Inventory jargon firewall note added before inventory sequence.

---

## [v1.9] — 2026-05-20 — URL breakdown query, S2C secondary-driver scoping, Section 3 ordering, action card quality gates

**Summary:** Five connected quality upgrades, most motivated by gaps identified in recent CE 2330 and CE 189 evaluations. A dedicated URL breakdown query (`pct_of_lp` CTE) is added to `context.md` and wired into `hypothesis.md` and `report_structure.md` — replacing the canonical L2+ query wherever URL routing vs performance disambiguation is needed. `hypothesis.md` gains a secondary-driver scoping block for S2C (prevents unnecessary first-pass branches when S2C is not the primary driver) and a C2O experience-routing follow-up sequence. `report_structure.md` gains a fixed Section 3 ordering, a URL-level breakdown HTML block, an action card evidence threshold rule, and multi-step "What broke?" examples. `actions.md` gains a DATA GAP template for the RC9 unresolved A2O mechanism case. `SKILL.md` gains two new findings-gate items: fixed-segment reflection check and action card data-accessibility check.

### Changes by file

**`SKILL.md`**
- **Depth vs completeness clarification** — Added a note below the branch completeness rule: the rule is about map coverage, not depth. A one-line closure ("same mechanism as C2O — CONFIRMED" or "A2O within-experience improvement: mechanism untested — DATA GAP") satisfies completeness without requiring a full investigation branch for every minor quantified signal.
- **Findings gate item 6 — Fixed segment reflected in analysis** — New checklist item: if a fixed segment was declared at the end of the mix cascade, verify that L2+ queries actually apply those filters. If a broader cut was used as a proxy, note it explicitly and confirm it is a reasonable approximation. No silent mismatches between the declared segment and the data used.
- **Findings gate item 7 — Action cards reference accessible data** — New checklist item: before writing an action card that asks a team to investigate a specific period or data point, confirm that data is reachable via analytics. If it falls outside a rolling window or a backlogged table, name an alternative source (availability system logs, supplier contracts) so the DRI knows where to look.

**`references/context.md`** — c026
- Added dedicated URL breakdown query immediately after the canonical L2+ query pattern. The new query adds a `totals` CTE that computes `pct_of_lp` — each URL's share of CE LP traffic per period. Required to distinguish routing shifts (traffic moved between URLs, rates held) from performance shifts (a URL's own rate dropped, share held). The canonical L2+ query cannot answer the routing question. Carries all fixed segment filters from the cascade declaration; sorts by `users_lp DESC`.

**`references/hypothesis.md`** — c016, c017
- **c016 — S2C secondary-driver scoping block** — Added at the top of the S2C section: when S2C is a secondary driver (primary is C2O or LP2S), run the fixed-segment aggregate first. If flat/improved outside the fixed segment → close as RULED OUT. If declined but directionally explained by the primary finding → close as CONFIRMED with one-line explanation. Only open the full first-pass branch set if S2C shows an independent decline not explained by the primary mechanism. Prevents unnecessary dimension cuts on secondary steps.
- **C2O experience routing follow-up** — When C2O improved via an experience routing shift, two directional follow-up checks added using `product_rankings_features`: pricing signal (compare `final_price_usd` for gaining vs losing experience pre/post) and availability signal (compare `days_to_first_available_date`). Both are directional; if neither explains the shift, flag as DATA GAP rather than forcing a mechanism claim.
- **c017 — URL concentration pointer updated** — URL concentration cross-cutting check now points to the dedicated URL breakdown query from `context.md` instead of the canonical L2+ query. Reason: the section requires `pct_of_lp` to distinguish routing vs performance stories; the canonical query does not produce that column.

**`references/actions.md`** — c004
- **RC9 DATA GAP action template** — Added a template action card for when the A2O locus is confirmed but the specific mechanism is unresolved because `order_attempted_events_v2` was not queried (backlogged). Template provides: a specific BQ query scope (experience ID + post period), and three sub-hypotheses for the DRI to test (inventory sync failure → Ops/Engineering; gateway decline → Payments; fraud over-blocking → Payments rule audit). Ensures the DRI receives a starting hypothesis rather than generic "investigate further" text.

**`references/report_structure.md`** — c021, c022, c023, c024
- **c021 — Section 1c "What broke?" multi-step examples** — When multiple funnel steps each carry >15% Shapley share, name all of them in one sentence. Two examples added: one for multi-step same-mechanism case, one for multi-step different-mechanism case. Cross-reference note added under "Why did it break?" requiring seasonal/event-based framing to be paired with a specific data signal (traffic pattern, daily CVR break, or controlled comparison).
- **c022 — Action card evidence threshold** — Before creating a standalone action card, verify both the rate drop and raw event count. A directional signal from a small sample belongs as a sub-bullet inside the most relevant existing P1/P2 card, not a standalone card. Example sub-bullet wording provided.
- **c023 — Section 3 fixed ordering** — "What belongs in Section 3" now specifies a numbered fixed order for always-present blocks: (1) mix cascade + Fixed Segment banner, (2) Geo/Non-Geo, (3) Shapley, (4) daily trend, (5) primary driver cuts, (6) secondary driver evidence, (7) ruled-out dimensions, (8) hypotheses explored. Conditional blocks (inventory, session recordings, price) slot within primary driver evidence.
- **c024 — URL-level breakdown block HTML pattern** — New section before the inventory section format. Two verdict forms: performance verdict (rate dropped, share held) and routing verdict (share shifted, rates held). Table columns: URL · Period · Users · % of LP · LP2S · S2C · C2O · CVR. `.highlight-row` on URLs where rate dropped meaningfully or `pct_of_lp` shifted substantially. Pointer to the dedicated URL breakdown query in `context.md`.

### Test runs

Three new runs added (`v1.9`):
- **ce189_2026-04-09_2026-05-06** (Vatican Museums) — 31/35. Post-Easter seasonal composition shift confirmed as root cause; supply definitively ruled out (both limited-capacity TIDs show zero tickets in both pre and post periods). Remaining gaps: daily trend charts not filtered to fixed segment; no controlled comparison excluding Italian national holidays.
- **ce2330_2026-03-13_2026-05-12_run2** (Walt Disney World Orlando) — 28/35. Dual-driver: spring break → off-season demand shift (primary) + Magic Kingdom A2O failure for experience 36344 (secondary, DATA GAP pending order_attempted_events_v2). Run 2 closes all three execution errors from Run 1. Remaining gaps: Fixed Segment banner not rendered as standalone HTML component; cross-cut (Android Mweb × experience × A2O) not run.
- **ce6495_2026-03-13_2026-05-12** (Kualoa Ranch) — 27/35. Near-term inventory depletion of UTV Raptor Tour (TID 80074) confirmed as root cause via Jurassic Zipline inverse confirmation. Main gap: C2O branch not opened despite 22% Shapley share.

---

## [v1.0] — 2026-04-27 — Initial release

**Summary:** First versioned release of the CVR-RCA skill. Establishes the full investigation framework, reference files, SQL pipeline, rendering helpers, and evaluation rubric.

### What's included

**Core skill (`SKILL.md`)**
- Full 4-step investigation framework: baseline pipeline → investigation → report → self-evaluation
- Three mandatory pre-investigation questions: routing vs conversion (Q1), primary Shapley driver (Q2), sudden vs gradual onset (Q3)
- Worked example showing both a mix-dominant path and a funnel-conversion path
- Investigation transcript requirement (`transcript.md`) — every decision fork logged with hypothesis, data, decision, and ruled-out paths
- Custom query patterns for all available dimensions (`browsing_country`, `channel_name`, `lead_time_days`, `page_sub_type`, `previous_page_url`, cross-dimensional cuts)
- Mixpanel session recording integration for URL-level qualitative confirmation

**Reference files (`references/`)**
- `context.md` — full business domain vocabulary, table schemas (`mixpanel_user_page_funnel_progression`, `product_rankings_features`, `dim_combined_entities`, `dim_experiences`), column-level notes, counting rules, and analytical definitions
- `hypothesis.md` — 10 historical patterns drawn from 21 Headout MMPs, ranked by frequency across LP2S/S2C/C2O/mix scenarios; framed as priors to orient (not constrain) hypothesis generation
- `actions.md` — 10 root-cause-to-action mappings with DRI, priority, and historical references from real Headout RCAs
- `report_structure.md` — fixed three-section layout (Executive Summary → Actions → Supporting Analysis) with hard constraints, anti-pattern list, and length calibration table

**SQL pipeline (`references/`)**
- `q0_meta.sql` — CE name and top page URL
- `q1_base.sql` — base funnel by MB/HO × Channel × Period with CE-level ALL row
- `q2_dimensions.sql` — device, language, page_type cuts
- `q3_trend.sql` — daily CVR trend for pre and post periods
- `q4_experience.sql` — experience-level S2C and CVR breakdown
- `q5_price.sql` — price analysis (final vs original price, median, pre/post comparison)
- `q6_urls.sql` — top 20 page URLs by LP traffic volume with per-URL funnel rates

**Scripts (`scripts/`)**
- `run_analysis.sh` — orchestrates Q0–Q6, runs Q2–Q6 in parallel, produces `summary.json`
- `aggregate.py` — computes Shapley decomposition, mix vs conversion effects, C2O sub-decomposition, rolls up all stage JSON into structured `summary.json`
- `render.py` — HTML component helpers: metric cards, trend charts, experience tables
- `helpers.py` — shared utilities

**Report template (`templates/`)**
- `report.html` — base HTML template for rendered reports

**Evaluation rubric (`evals/`)**
- `evaluator.md` — 7-theme rubric (Narrative Coherence, Hypothesis Specificity, Investigation Effort, Branch Decision Quality, Evidence Strength, Output Appropriateness, DRI Actionability) scored 1–5 with evaluation file format
- `evals/runs/` — persistent record of past evaluations (accumulates across runs)

### Internal changelogs at time of initial release

The following changelog entries were already tracked inside individual reference files before the repo was created:

**SKILL.md**
| # | Date | Change |
|---|------|--------|
| c001 | 2026-04-24 | Initial version — investigation framework, 3 mandatory questions, Shapley, mix decomp, custom query patterns, render.py integration, Step 4 evaluator |
| c002 | 2026-04-24 | Added `report_structure.md` to "Before you begin" reads; updated file role descriptions; clarified `hypothesis.md` as historical priors not a constraint; replaced Step 3 guidance with pointer to `report_structure.md`; updated Backlogs for A2O query columns |

**`hypothesis.md`**
| # | Date | Change |
|---|------|--------|
| c001 | 2026-04-24 | Initial version — 10 patterns from 21 historical Headout MMPs |
| c002 | 2026-04-24 | Added "How to use this file" preamble; clarified patterns are priors not a constraint; Claude generates its own hypotheses from data |

**`actions.md`**
| # | Date | Change |
|---|------|--------|
| c001 | 2026-04-24 | Initial version — 10 root causes from 21 Headout MMPs and CVR Cause-to-Action Playbook |
| c002 | 2026-04-24 | RC1: competitive intel skill pointer added. RC2: inventory skill pointer added. RC8: pax setup skill pointer added. RC9: `order_attempted_events_v2` column detail added. RC10: content audit sub-skill pointer added |

**`report_structure.md`**
| # | Date | Change |
|---|------|--------|
| c001 | 2026-04-24 | Initial version — three-section report structure extracted from SKILL.md Step 3 and formalized |

---

## [v1.1] — 2026-04-27 — Process/domain separation

**Summary:** The skill was refactored to enforce a clean separation between *process* (what steps to follow and when to pivot) and *domain knowledge* (how to interpret data, what patterns to look for, how to write queries). `SKILL.md` is now a lean process orchestrator. `context.md` is the domain knowledge hub. A new `worked_example.md` file houses the two end-to-end investigation walkthroughs.

This makes the skill easier to maintain: process changes update `SKILL.md`, analytical guidance updates `context.md`, and neither bleeds into the other.

### Changes by file

**`SKILL.md`** (c003 → c007)
- **c003:** Added majority-contributor principle (focus on entities with meaningful CE traffic share, not long-tail noise) and rate × volume rule (impact = rate delta × user volume, not rate delta alone). Strengthened session recordings from optional to required once a locus is confirmed; skipping must be explicitly justified in the report.
- **c004:** Fixed session recordings trigger from conjunctive (URL *and* experience *and* segment) to disjunctive (any concentrated dimension cut is sufficient). Added "Data pull errors — log and continue" section: query failures are logged in the transcript and noted in the report as data gaps; the investigation does not halt.
- **c005:** Updated report visual standard; added P1/P2/P3 priority badges to action cards.
- **c006:** Removed references to Q2/Q4/Q5/Q6 as pre-built templates to run; fixed stale `summary.json` field references in investigation patterns. All custom querying is now framed as write-from-scratch using `context.md` schemas.
- **c007:** Stripped `SKILL.md` to pure process orchestration. All domain content moved out:
  - Query rules, dimension guidance, investigation patterns per funnel step → `context.md`
  - Both worked examples → `references/worked_example.md`
  - Q3 (onset type) expanded from two branches to three (sudden / gradual / seasonal); full interpretation guide lives in `context.md`

**`references/context.md`** (c002)
- Added **Query Principles** section: majority-contributor principle and rate × volume rule (moved from SKILL.md, formalized as domain rules)
- Added **Q3 Trend Interpretation** guide: how to read each 90-day trend shape (sharp break / gradual erosion / recovery in progress), how to use the LY overlay and `structural_delta_cvr` to calibrate investigation depth, and weekday composition check
- Added **Dimensions to Query and When**: `browsing_country`, `browsing_city`, `channel_name`, `lead_time_days`, `page_sub_type`, `previous_page_url`, cross-dimensional cuts, experience-level with availability proxy — each with the hypothesis context that makes it worth querying
- Added **Common Investigation Patterns**: per-funnel-step query angles for mix, LP2S, S2C, and C2O drivers (moved from SKILL.md, expanded)
- Added **Session Recordings** guidance: structured table format (Recording | Steps observed | Inference) rather than prose; inference column must state what each recording proves or rules out

**`references/worked_example.md`** (new file)
- Two complete end-to-end investigation walkthroughs extracted from `SKILL.md`:
  - **Example 1:** Mix-dominant story — MB traffic share shift explains the CVR drop; no funnel step broke; report covers mix table and URL traffic comparison only
  - **Example 2:** Conversion-dominant, concentrated locus — S2C drop, sharp Apr 8 onset, French × iOS Mweb cross-cut, session recordings confirming empty date picker; shows how the investigation narrows from CE-wide to one experience on one locale

---

## [v1.2] — 2026-04-27 — Default analysis window changed to 30 days

**Summary:** The skill previously required explicit date arguments every time it was invoked. Dates are now optional — when omitted, the script automatically uses the last 30 days as the post period and the 30 days before that as the pre period. This removes the most common friction point when starting a quick investigation.

### Changes by file

**`SKILL.md`** (c009)
- Invocation syntax updated from required `<pre_start> <pre_end> <post_start> <post_end>` to optional `[<pre_start> <pre_end> <post_start> <post_end>]`
- Added one-line note explaining the default: last 30 days = post, prior 30 days = pre

**`scripts/run_analysis.sh`** (c002)
- Date arguments are now optional. When not supplied, the script computes: `POST_END` = yesterday, `POST_START` = 30 days ago, `PRE_END` = 31 days ago, `PRE_START` = 61 days ago
- Added cross-platform `_date_offset()` helper that works on both BSD `date` (macOS) and GNU `date` (Linux)
- Script now prints the resolved date windows at the end of every run so it is always visible which periods were used
- Cleaned up header comments: removed stale Q2/Q4/Q5/Q6 "demoted" note that no longer applies

---

## [v1.3] — 2026-04-28 — Investigation tree model + unified run folder

**Summary:** Two significant upgrades in this release. First, the investigation model was rewritten from a sequential three-question gate into a parallel investigation tree (L0 → L1 → leaf), making the analytical reasoning faster and more structured. Second, all run outputs (report, transcript, evaluation, findings, raw data) are now consolidated into a single persistent folder per run, with date-range naming and auto-increment to prevent overwrites.

### Changes by file

**`SKILL.md`** (c012 → c016)
- **c012 — Investigation tree model:** Replaces the sequential Q1/Q2/Q3 gate model with a tree structure. L0 reads all three orientation signals simultaneously (`mix_dominance`, `shapley`, `trend_context`). L1 opens a parallel hypothesis batch based on L0 signals. Each result either confirms (open L2), rules out (close branch), or concentrates (anchor all downstream queries). Investigation terminates at a leaf: a specific mechanism × segment/experience/URL × date. Transcript format mirrors the tree with `## L0`, `## L1`, `## L2`, and `## Root cause confirmed` sections.
- **c013 — Tree map in transcript:** Transcript now has two layers — a tree map block at the top showing the full branch structure (`CONFIRMED / RULED OUT / OPEN / LEAF` per branch) and detail sections below with query results. Tree map is written after L0 with all L1 branches marked `OPEN` and updated as results arrive. Anyone reading the transcript sees the investigation shape immediately without scrolling.
- **c014 — Date range in output directory name:** Output folder renamed from `/tmp/cvr_rca_<ce_id>/` to include the date range (e.g. `ce167_2026-03-01_2026-04-29/`). Running the same CE twice with different windows no longer silently overwrites results.
- **c015 — Consolidated run folder:** All outputs for a run now live in one persistent folder: `~/Documents/RCA skill/Test Runs/ce<ce_id>_<pre_start>_<post_end>/`. Previously, outputs were scattered across `/tmp/`, `~/Documents/RCA skill/transcripts/`, and `~/Documents/RCA skill/evals/`. Report, transcript, evaluation, findings, and raw pipeline data are all co-located.
- **c016 — Auto-increment on folder collision:** If the named run folder already exists (same CE + same dates run twice), the script auto-increments the suffix: `_run2/`, `_run3/`, etc. The chosen folder name is printed at the start of the run. SKILL.md now uses `<run_dir>` shorthand throughout so the naming logic is explained once in Step 1 and not repeated.

**`references/context.md`**
- Added **"Investigation tree — L0 to L1 branch map"** section: a lookup table mapping each combination of L0 signals (mix dominant / LP2S primary / S2C primary / C2O primary / gradual / sudden) to the default set of L1 branches that should open. Removes the need to derive the branch set from first principles on every run.

**`references/worked_example.md`**
- Both examples (mix-dominant and conversion-dominant) rewritten with tree-format transcripts: parallel query batches made explicit, session recordings anchored to L2 leaf, tree map blocks included showing branch resolution.

**`scripts/run_analysis.sh`**
- Output directory updated to `~/Documents/RCA skill/Test Runs/ce<ce_id>_<pre_start>_<post_end>/`
- Auto-increment logic added for folder collisions
- Prints resolved run folder name at start of execution

**`scripts/aggregate.py`**
- Docstring example updated to reflect new output directory pattern

**Removed**
- `assets/headout-logo.svg` — unused since `render.py` was removed in a prior release
- `templates/report copy.html` — stale duplicate, superseded by `templates/report.html`

---

## [v1.4] — 2026-04-29 — Mix cascade, self-extending branches, hypothesis.md restructure

**Summary:** Three interlocking upgrades that make the investigation more rigorous and faster to execute. First, the mix cascade is now a mandatory L1 step that runs before any funnel hypothesis — it fixes the primary segment (MB/HO → Paid/Organic → Channel) so all downstream funnel analysis describes a homogeneous cohort. Second, hypothesis generation is now explicitly self-extending: branches grow level-by-level from what the data shows, not from a pre-written list, and a new "Surprises" result type forces investigation of unexpected findings. Third, `hypothesis.md` is restructured as the central branch reference for the entire investigation — it now owns both the L0 routing map and the first-pass branch sets (moved from `context.md`), keeping `context.md` focused on business vocabulary, schemas, and query rules only.

### Changes by file

**`SKILL.md`** (c017 → c020)
- **c017 — Mix cascade as mandatory L1:** Before forming any funnel hypothesis, run a three-level mix cascade (Level 1: MB vs HO from `summary.json`; Level 2: Paid vs Organic custom BQ query; Level 3: Channel breakdown within Paid). Fixed segment declared once in the transcript; all L2+ queries carry that segment's filters. L1 and L2+ step names updated accordingly.
- **c018 — Self-extending hypothesis loop:** L2+ branches grow from what the data shows, not from a fixed upfront list. Four result types formalised: Confirms, Rules out, Concentrates, and Surprises. "Surprises" is new — an unexpected result generates a new branch even if it wasn't in the default set. Investigation ends at the leaf, not at list exhaustion.
- **c019 — Remove stale artifact:** Removed "write 2–4 specific, falsifiable hypotheses" from L2+ — a leftover from the old Q1/Q2/Q3 model that contradicted the tree structure.
- **c020 — File role descriptions updated:** `context.md` role narrowed to business vocabulary, schemas, and query rules. `hypothesis.md` described as the two-level central branch reference (L0 routing + first-pass branch sets + historical patterns). L2+ pointer updated from `context.md` → `hypothesis.md`.

**`references/context.md`** (c004 → c009)
- **c004/c005 — Inventory table schemas:** Added `analytics_reporting.inventory_availability` and `analytics_intermediate.inventory_changes` with full column-level notes, join path (the two-hop `dim_experiences → dim_tours → inventory_availability` bridge), and lead-time bucket query. Bucket boundaries carry inline guidance to adapt to each CE's booking horizon. Results interpretation covers both window-specific and uniform-decline patterns.
- **c006 — Mix Cascade section:** Full three-level cascade added with BQ query templates for Level 2 (Paid/Organic) and Level 3 (Channel breakdown within Paid), decision rule for when to fix a level (>15% post share + dominant checkout impact), and fixed segment declaration template with filter strings.
- **c007 — Investigation patterns expanded:** LP2S gains three-tier triage (dimension cuts → pricing if no concentration → sessions as fallback). S2C gains language × S2C and device × S2C as first-pass cuts before experience-level; inventory lead-time bucket query integrated into S2C path. C2O expanded with four C2A hypotheses (pax availability, price friction, UX change, sessions) and three A2O hypotheses (gateway failure, fraud tightening, live inventory sync failure) with named DRIs.
- **c008 — Common Investigation Patterns header rewritten:** "Not rails" disclaimer replaced with explicit loop logic — patterns are the default starting set, results generate the next hypothesis, investigation ends at the leaf not at list exhaustion. Three reasons a list runs out before a leaf is reached added.
- **c009 — Moved investigation logic to hypothesis.md:** "Investigation tree — L0 to L1 branch map" and "Common Investigation Patterns" sections removed from `context.md` and moved to `hypothesis.md`.

**`references/hypothesis.md`** (c004)
- **c004 — Restructured as two-level branch reference:** Level 1 (L0 routing map + first-pass branch sets by funnel step) added at the top, moved from `context.md`. Level 2 (historical patterns 1–10) retained and explicitly labelled as "mechanism detail by scenario" — used once a first-pass branch confirms a direction. "How to use this file" updated to reflect full role as the central branch reference for all investigation levels.

**`references/report_structure.md`** (c006 → c010)
- **c006/c007 — Positive CVR framing:** New green-border callout variant for CVR-improvement investigations: heading "CVR Improved — What's Driving It & What's Holding It Back" with three questions (What drove the improvement? What's holding it back? When did the headwind emerge?).
- **c008 — 90-day chart to Section 1:** Chart moves from Section 3 (conditional) to Section 1 (always), appearing after metric cards and before the root cause callout. Post-window shade is green for improvements, red for declines.
- **c009 — Fixed Segment banner:** New HTML component after mix cascade output, before Shapley block. Declares `MB/HO · Paid/Organic · Channel` scope for all downstream funnel analysis.
- **c010 — Raw user counts mandatory:** All tables showing rates or shares must include Pre Users and Post Users columns. "Table shows rates/shares with no user counts" added to anti-patterns list.

---

## [v1.8] — 2026-05-07 — context.md/hypothesis.md structural separation + presentation-layer jargon fixes

**Summary:** Two connected changes. First, investigation decision logic was moved out of `context.md` and into `hypothesis.md`, restoring the intended separation: `context.md` owns business vocabulary, table schemas, and SQL queries; `hypothesis.md` owns the investigation decision tree (when to run what, how to interpret results, which branches to open). Second, three presentation-layer bugs were fixed in `report_structure.md` that were allowing internal investigation terminology to leak into the HTML report, and raw tables to appear where Plotly charts should be.

### Changes by file

**`references/context.md`** — c019

- **Structural separation:** Removed all investigation decision logic from the inventory section. What moved out: TGID locus identification (Case A/B/C + `lost_checkouts_delta` formula), the "before running, determine which path applies" decision framing, the TID scoping decision block ("use Step 2 results to decide single TID vs whole TGID"), and the broad-drop inventory path (Case C).
- **Queries renamed:** "Step 2 — TID summary table" → "TID snapshot query"; "Step 3 — Daily time-series" → "Daily time-series query". The numbered "Step" labels were investigation-layer jargon, not neutral query names.
- **Data availability facts retained neutrally:** Path A/B/X information rewritten as data facts ("`inventory_availability` retains a 30-day rolling window — if `pre_start < CURRENT_DATE − 30`, no pre-period rows exist") without the decision framing. The decision about which path to use now lives in `hypothesis.md`.
- **Pointer added:** "For TGID selection and the inventory investigation decision tree, see `hypothesis.md → S2C investigation → inventory branch`."

**`references/hypothesis.md`** — c007

- **"If experience concentrates" branch now owns the full inventory investigation sequence:** (1) TGID selection via `lost_checkouts_delta` + three-case classification (single dominant TGID ≥60% / multiple significant TGIDs ≥10% each / uniform drop); (2) data availability check before querying; (3) optional gradual-decline pre-check with `days_to_first_available_date`; (4) TID snapshot query usage (flag unlimited-capacity TIDs, scope the time-series); (5) daily time-series query usage (primary evidence — always run); (6) supply confirm/rule-out decision (healthy throughout post → pivot to pricing; depleted during post → supply is mechanism).
- **Broad-drop path moved here:** When no TGID accounts for ≥10% of `lost_checkouts_delta`, pick the top 3 TGIDs by `users_select` volume and run the inventory queries for each. Same bucket depleted across all three → CE-wide supply constraint; tickets healthy across all three → not supply.
- **"Step 2/3" label references removed throughout** — queries now referenced as "TID snapshot query" and "daily time-series query".

**`references/report_structure.md`** — c012

- **Supply gate wording:** Removed "Step 2" reference; the ruled-out verdict is now framed in terms of what the time-series showed, not internal step labels. Clarified that line charts may still be shown in the supply-ruled-out case as positive confirmation (lines staying above zero is visual evidence, not just a claim). TID snapshot table is omitted when supply is ruled out.
- **Anti-pattern added — Investigation-internal terminology:** Step 1/2/3, Path A/B, Case A/B/C, "locus", "lost_checkouts_delta", "candidate TGIDs" must not appear anywhere in the HTML report. These are transcript terms. In the report: "the three most-affected experiences" not "the Case B candidate TGIDs"; "supply checked and ruled out" not "Step 3 confirmed supply ruled out".
- **Anti-pattern added — Daily inventory as HTML table:** A 27-row × 4-column date table is unreadable at a glance. Daily inventory time-series is always Plotly line charts. The only table in the inventory section is the TID snapshot summary.

---

## [v1.6] — 2026-05-06 — Inventory analysis overhaul + Geo/Non-Geo dimension + Mix arithmetic guide

**Summary:** Three separate upgrades shipped together. First, the inventory analysis methodology was comprehensively overhauled: the old `count_days_available_30d` proxy is gone, replaced by direct TID-level queries against `inventory_availability` with a structured three-step path (locus identification → TID snapshot → daily time-series). The query was also corrected for two bugs (CE-wide scope, sold-out overcounting). Second, a Geo/Non-Geo dimension was added as a first-pass S2C and LP2S cut, and the mix cascade investigation path was expanded with a worked arithmetic guide and a canonical L2+ query template. Third, a new `events.md` reference file documents all GTM/Mixpanel funnel events.

### Changes by file

**`references/context.md`** — c012, c013, c014, c015

- **c012 — Mix cascade query fixes and arithmetic guide:** Fixed `COUNTIF` → `COUNT(DISTINCT CASE WHEN)` in Level 2/3 cascade queries and the canonical L2+ template. Added `PERFORMANCE_MAX` exclusion to Level 2/3 queries. Added `mix_effect`/`conversion_effect` arithmetic guide with step-by-step formula and a Level 3 worked example showing how to confirm which cascade level is the routing driver.
- **c012 — Canonical L2+ query template:** Added a single annotated template that carries the fixed segment filters through all Level 2+ funnel queries — prevents the fixed segment from being silently dropped on custom cuts.
- **c013 — Geo/Non-Geo dimension:** Added browsing country as a pre-step dimension. CE country identified from `dim_experiences.country`; query returns top-5 countries always plus the CE's home country. Interpretation guide covers Geo-only drop (demand shift or regulatory), Non-Geo-only drop (paid search or content), and mixed drops. Cross-dimensional intersections added (Geo × device, Geo × channel).
- **c014 — Inventory query scope bug fix:** Corrected a CE-wide scope bug where the query fetched all `tour_id`s for the CE instead of filtering to the confirmed TGID. Fixed by filtering `dim_tours` to `experience_id = '<tgid>'` before joining `inventory_availability`.
- **c014 — Inventory sold-out overcounting fix:** `COUNTIF(total_remaining = 0)` operated at TID × date grain — a date where one TID was sold out but others had capacity was incorrectly counted as zero-inventory. Fixed by adding a `tgid_daily_inventory` CTE that sums remaining across all TIDs per date before bucketing. A date is only counted as sold out when the sum across all TIDs for that date is zero.
- **c015 — Inventory analysis complete rewrite:** Removed `count_days_available_30d` as the inventory signal; replaced with direct `inventory_availability` queries throughout. Restructured as a three-step path:
  - **Step 1 — Locus identification:** Compute `lost_checkouts_delta = users_select_post × (s2c_rate_pre − s2c_rate_post)` for each TGID from Q4 results. Three cases: Case A (single TGID ≥60% of total delta — that TGID is the locus), Case B (2–3 TGIDs each ≥10% — multiple loci, run Step 2 for each), Case C (no TGID ≥10% — uniform drop, see broad-drop path).
  - **Step 2 — TID summary table:** Snapshot from the latest `extracted_date`. One row per TID. Ticket counts (sum of `total_remaining`) bucketed into 0–2d, 3–7d, 8–13d, 14–30d windows. Computes `is_fully_unlimited_capacity` — TIDs with this TRUE must be excluded from supply scarcity analysis (unlimited-capacity slots represent `total_remaining = 1` as a system constant, not actual ticket count).
  - **Step 3 — Daily time-series:** Tracks `extracted_date` trend per TID per bucket. Path B (pre within 30-day window): pre and post series overlaid. Path A (pre outside 30-day window): post only with an explicit data-unavailability note.
  - **Path A vs Path B determination** added at the top of the section; determines whether pre/post comparison or snapshot-only is possible.
  - **Broad-drop inventory path (Case C):** When S2C drops uniformly across all experiences with no concentration, pick the top 3 TGIDs by `users_select` volume from Q4 and run Step 2 for each. Same bucket depleted across all three → CE-wide supply constraint. All full → supply is not the mechanism.
  - **Supply gate:** If Step 2 shows no depletion across limited-capacity TIDs, do not run Step 3; pivot to pricing or UX instead.
  - Removed `count_days_available_30d` from `product_rankings_features` schema table.

**`references/hypothesis.md`** — c016

- All references to `count_days_available_30d` as an availability signal replaced with `inventory_availability` TID summary table (Step 2 from context.md).
- **Gradual S2C decline:** Added `days_to_first_available_date` as a fast directional check before running inventory queries — an increasing trend confirms supply scarcity direction without a full TID query.
- **CE-wide S2C drop (no concentration):** Updated to point to the broad-drop inventory path (top 3 TGIDs by volume, Step 2 for each).
- **Vendor throttling pattern:** Signal updated from `count_days_available_30d` to `days_to_first_available_date` + 0–2d bucket ticket count from TID summary table.
- **Experience-specific availability collapse:** Updated to run `inventory_availability` TID summary table and daily time-series instead of `count_days_available_30d`.

**`references/actions.md`** — c017

- RC2 (Inventory/availability constraint) signal updated: removed `count_days_available_30d` reference; replaced with `inventory_availability` TID summary table (near-zero ticket counts in one or more lead-time buckets) as the primary signal.

**`references/report_structure.md`** — c018

- "What belongs in Section 3" table: replaced "Availability proxy table" and "Inventory lead-time bucket table" rows with "Inventory TID summary table" (Step 2, one row per TID) and "Inventory daily time-series charts" (Step 3, one chart per lead-time bucket).
- Section renamed from "Inventory lead-time bucket table format" to "Inventory section format".
- Verdict forms updated from "window-specific spike / counts_zero_inventory" to "window-specific drop / ticket counts near zero".
- Added supply gate outcome instruction: write a ruled-out callout and skip the table/charts entirely if Step 2 finds no depleted limited-capacity TIDs.
- Added Path B spec: one row per TID, Pre/Post column pairs per bucket, `Capacity type` column, `highlight-row` on TID rows where the affected bucket pair shows the material drop, unlimited-capacity TIDs excluded from table with subtext note.
- Added Path A spec: post-only columns, amber note above table stating pre-period unavailability.
- Added daily time-series chart spec: four charts (one per bucket), Path B overlays pre/post, Path A post only.
- Updated subtext guidance: state pattern, when it started, what supply team should verify. No mechanism assertions.
- HTML pattern replaced: old format (rows per bucket, aggregate columns) replaced with two separate patterns — Path B (rows per TID, Pre/Post bucket columns) and Path A (rows per TID, post-only columns). Each with correct `highlight-row` usage and capacity-type column.

**`references/q1_base.sql`** — c019

- Removed `MAX(CASE WHEN page_type IN (...) THEN 1 ELSE 0 END) AS visited_lp` from SELECT; condition moved to WHERE clause. Fixed `GROUP BY 1, 2, 3, 9` → `GROUP BY 1, 2, 3, 8` to reflect the column count change.

**`references/worked_example.md`** — c020

- Removed `count_days_available_30d` from the S2C locus identification section (Example 2).
- Added TID summary table query result to the transcript: shows `tickets_8_13d` and `tickets_14_30d` → 0 for all TIDs of TGID 8821, confirming the 8+ day window as the affected bucket.

**`references/hypothesis.md`** — c021 (mix routing exit)

- Mix routing exit path rewritten as a 3-level investigation: Level 1 (time the shift — when did the MB/HO mix change?), Level 2 (which sub-segment drove it — Paid/Organic/Channel?), Level 3 (URL impact — did the mix shift affect a specific landing page?). Each level has a Tier 1/2/3 structure with a declaration template.
- LP2S Tier 1: added `browsing_country` (Geo/Non-Geo) as a parallel first-pass cut with drill-down guidance.
- S2C Tier 1: added `browsing_country` (Geo/Non-Geo) as a parallel first-pass cut.
- C2O C2A: added optional Geo/Non-Geo cut for broad drops with no device/experience concentration.

**`references/report_structure.md`** — c022 (mix cascade block)

- Added Mix cascade analysis block spec: `.analysis-block` with three sub-tables (one per cascade level). Each sub-table has a verdict line, `mix_effect`/`conv_effect` columns, and `highlight-row` on the fixed segment row. Routing exit variant renders only up to the exit level — if routing exits at Level 1, only the Level 1 table is shown.

**`references/events.md`** — new file

- New reference file documenting all GTM/Mixpanel funnel events used in CVR analysis: LP events (15 + 4 supporting), S2C events (14 + 3 supporting), C2O events (15 + 8 supporting). Each event includes key properties, analytical purpose, excluded noise events, and session join key notes.

---

## [v1.5] — 2026-05-04 — Findings synthesis gate + Evaluator failure mode classification

**Summary:** Two interconnected upgrades. (1) `SKILL.md` gains Step 2b: before writing any HTML, Claude writes `findings.md` with a mandatory Evidence inventory table where every claim must name its data source — closing the main hallucination vector where approximate values replaced confirmed BQ query outputs. (2) `evaluator.md` is redesigned to diagnose *why* each gap occurred, not just *what* was missing: every gap now gets a failure mode tag backed by a grounded citation, and a new Section 4 table maps all gaps directly to actionable skill file edits.

### Changes by file

**`SKILL.md`** — c010 / c011

**Step 2b — Structured findings synthesis (c010)**
- Claude now writes `findings.md` before writing any HTML, with four required sections: Root cause (one sentence), Mechanism (causal chain), Timing (classification + evidence), Evidence inventory (table with Claim / Supporting data / Source / Confidence)
- Open items section forces explicit tracking of every Consistent with / Unverified claim — each must be resolved with a query or arithmetic, or explicitly accepted with appropriate language in the report
- Step 3 writes from `findings.md` as source of truth — not directly from raw query outputs
- Rationale: test runs showed Claude writing reports using impressions and approximations rather than confirmed numbers from the transcript. `findings.md` is the checkpoint that catches this before HTML is committed.

**Evidence inventory Source column (c011)**
- Every claim in the Evidence inventory must name its data origin: a specific `summary.json` field, a named BQ query result, or a specific table row that will appear in the report
- A number with no named source must be derived explicitly with written arithmetic or removed — it must not enter the report
- Rationale: hallucination risk was highest at the transcript → report transition. The Source column makes provenance explicit and checkable.

**Output paths**
- All output paths use `<run_dir>` shorthand (`<run_dir>/transcript.md`, `<run_dir>/findings.md`, `<run_dir>/report.html`, `<run_dir>/evaluation.md`) — consistent with auto-increment run folder naming introduced in c016.

**`evals/evaluator.md`** — e001

- **What to review** — Added skill reference files (SKILL.md, hypothesis.md, context.md, report_structure.md) as the first pre-read step, before the report and transcript. Reading the skill files first is required so the evaluator can verify whether an instruction existed before classifying a gap.
- **Scoring** — Added two new required fields per theme: `Gap` (if score ≤ 4) describing specifically what was missing or wrong; `Why` — a failure mode tag with a grounding citation.
- **Failure Mode Classification** (new section) — Defines four tags with meanings and grounding requirements: `[MISSING_INSTRUCTION]`, `[AMBIGUOUS_INSTRUCTION]`, `[EXEC_ERROR]`, `[DATA_LIMIT]`. Tag assignment without a citation is explicitly prohibited.
- **Output format** — Updated Section 2 to show inline `Gap` / `Why` blocks with a worked example. Added Section 4: Failure Mode Summary table mapping every gap to a specific file + fix description.
- **Self-honesty check** — Four grounding checks added (one per tag type): did you actually look in the skill files, quote the instruction, confirm an attempt in the transcript, verify data unavailability?

### Test runs

Two new runs added (`v1.5`):
- **ce189_2026-03-05_2026-05-03** (Vatican Museums) — 25/35. Dual-driver: S2C supply capacity pressure (spring demand exceeded fixed Vatican slot supply, confirmed via availability proxy and lead-time bucket query) + C2O iOS/Android device split (price shock + live inventory). First run evaluated against the evaluator v1.5 rubric.
- **ce6495_2026-03-05_2026-05-03** (Kualoa Ranch) — 24/35. S2C demand quality decline: spring break wind-down replaced high-intent vacationers with low-intent off-peak tourists. First run to conclusively establish seasonal demand quality as a mechanism (no supply, pricing, or UX change confirmed).

---

## [v1.7] — 2026-05-06 — Inventory analysis overhaul (TID-level queries, Path A/B, supply gate)

**Summary:** The S2C inventory analysis methodology was comprehensively rewritten. The old `count_days_available_30d` proxy from `product_rankings_features` is removed entirely; all inventory investigation now uses direct TID-level queries against `inventory_availability`. Two query bugs were fixed first (CE-wide TGID scope; sold-out overcounting via `tgid_daily_inventory` CTE). The rewrite introduces a structured 3-step path: locus identification via `lost_checkouts_delta` (Step 1), a TID snapshot table (Step 2), and a daily time-series (Step 3). A Path A / Path B determination gate handles the 30-day rolling window limitation. A supply gate prevents unnecessary deep-dives when inventory is not depleted. The investigation decision tree (part2.js) was updated to reflect all changes.

### Changes by file

**`references/context.md`** — c014 / c015

- **c014 — Inventory query bug fixes:** Fixed two bugs in the existing lead-time bucket query. (1) CE-wide scope bug: the query fetched all `tour_id`s for the CE instead of filtering to the confirmed TGID (`experience_id = '<tgid>'`). (2) Sold-out overcounting: `COUNTIF(total_remaining = 0)` operated at TID × date grain — a date where one TID was sold out but others held capacity was incorrectly counted as zero-inventory. Fixed by adding a `tgid_daily_inventory` CTE that sums `total_remaining` across all TIDs per date before bucketing; a date is only counted as zero-inventory when the sum across all TIDs is zero.
- **c015 — Inventory analysis complete rewrite:** Removed `count_days_available_30d` as the inventory signal across the entire section. Restructured as a **3-step path**:
  - **Step 1 — Locus identification:** Compute `lost_checkouts_delta = users_select_post × (s2c_rate_pre − s2c_rate_post)` per TGID from Q4 results. Three cases: Case A (top TGID ≥60% of total delta → single locus), Case B (2–3 TGIDs each ≥10% → multiple loci, run Step 2 for each), Case C (no TGID ≥10% → uniform drop → broad-drop path).
  - **Step 2 — TID snapshot:** Run against latest `extracted_date`. One row per TID. Ticket counts (sum of `total_remaining`) in four buckets: 0–2d, 3–7d, 8–13d, 14–30d. `is_fully_unlimited_capacity` flag — TIDs where this is TRUE must be excluded from scarcity analysis (`total_remaining = 1` is a system constant for unlimited-capacity slots, not an actual ticket count).
  - **Step 3 — Daily time-series:** `extracted_date` trend per bucket. Path B: pre+post series overlaid. Path A: post only. Scoped to single TID if that TID is the locus, or whole TGID if all TIDs depleted equally.
  - **Path A vs Path B:** Determined by whether `pre_start >= CURRENT_DATE - 30`. Path B = full pre/post comparison. Path A = pre-period outside 30-day window; post-only snapshot with an explicit data-limitation note in the report.
  - **Supply gate:** If Step 2 shows no depletion across limited-capacity TIDs, skip Step 3 and pivot to pricing or UX investigation instead.
  - **Broad-drop path (Case C):** Run Step 2 for top 3 TGIDs by `users_select`. Same bucket depleted across all three → CE-wide supply constraint. All full → supply is not the mechanism.

**`references/hypothesis.md`** — c016

- All references to `count_days_available_30d` as the availability signal replaced with `inventory_availability` TID summary table (Step 2 results).
- **Gradual S2C decline (Pattern 4):** Added `days_to_first_available_date` as a fast directional check before running inventory queries — an increasing trend confirms supply scarcity direction without a full TID query.
- **CE-wide S2C drop (no concentration):** Updated to point to the broad-drop inventory path (top 3 TGIDs by `users_select`, Step 2 for each).
- **Vendor throttling pattern:** Signal updated from `count_days_available_30d` to `days_to_first_available_date` increasing + 0–2d bucket near zero in TID snapshot.
- **S2C Tier 1 (experience concentrates):** Updated to reference `lost_checkouts_delta` locus computation → Case A/B/C → 3-step inventory path.
- **Experience-specific availability collapse (Pattern 3):** Updated to run `inventory_availability` TID summary table and daily time-series instead of `count_days_available_30d`.

**`references/actions.md`** — c017

- RC2 (Inventory/availability constraint): removed `count_days_available_30d` reference; replaced with `inventory_availability` TID summary table (near-zero ticket counts in one or more lead-time buckets) as the primary signal.

**`references/report_structure.md`** — c018

- Section renamed from "Inventory lead-time bucket table format" to "Inventory section format".
- "What belongs in Section 3" table updated: "Availability proxy table" and "Inventory lead-time bucket table" rows replaced with "Inventory TID summary table" (Step 2, one row per TID) and "Inventory daily time-series charts" (Step 3, one chart per lead-time bucket).
- **Supply gate outcome:** if Step 2 finds no depleted limited-capacity TIDs, write a ruled-out callout and skip the table/charts entirely.
- **Path B spec:** one row per TID, Pre/Post column pairs per bucket, `Capacity type` column, `highlight-row` on TID rows where the affected bucket pair shows the material drop; unlimited-capacity TIDs excluded with subtext note.
- **Path A spec:** post-only columns, amber note above table stating pre-period unavailability.
- **Daily time-series chart spec:** four charts (one per bucket); Path B overlays pre/post as separate series; Path A post only.
- HTML pattern replaced: old format (rows per bucket, aggregate columns) replaced with two separate patterns — Path B (rows per TID, Pre/Post bucket columns) and Path A (rows per TID, post-only columns).
- Updated subtext guidance: state pattern, when it started, what supply team should verify. No mechanism assertions.

**`references/q1_base.sql`** — c019

- Removed `MAX(CASE WHEN page_type IN (...) THEN 1 ELSE 0 END) AS visited_lp` from SELECT (condition already enforced in WHERE clause, making the column redundant). Fixed `GROUP BY 1, 2, 3, 9` → `GROUP BY 1, 2, 3, 8` to reflect the column count change.

**`references/worked_example.md`** — c020

- Removed `count_days_available_30d` from the S2C locus identification section (Example 2). Added TID summary table query result to the transcript showing `tickets_8_13d` and `tickets_14_30d` → 0 for all TIDs of TGID 8821, confirming the 8–30d window as the affected bucket.

### Test runs

Three new runs added (`v1.7`):
- **ce6495_2026-03-05_2026-05-03_run3** (Kualoa Ranch) — 31/35. Third run on the same CE/window. Methodological improvements over run2: Geo/Non-Geo first-pass S2C cut correctly executed; TGID-scoped TID snapshot with corrected COUNTIF (bug c014 fixed); Path A correctly applied (pre period >30 days ago). Supply definitively ruled out: TGID 37530 fully stocked across all lead-time buckets despite −9pp S2C drop. Confirms spring break demand quality decline as root cause.
- **ce234_2026-04-21_2026-05-04** (Empire State Building) — 27/35. Routing story: Google Ads traffic collapsed 58% (1,186→499 users), shifting paid/organic mix from 80/20 to 51/49. Product funnel intact — Google Ads CVR held stable at 5.6–5.8%. Gaps: organic LP2S drop (26%→10% within organic) not investigated or ruled out; URL traffic comparison omitted; Level 2 cascade used all-traffic `summary.json` data instead of the MB-filtered query from `context.md`.
- **ce144_2026-04-08_2026-05-05** (Alcatraz Tours) — 32/35. CVR improvement case (+3.78pp above prior year). April 15 launch of exp 36426 (Alcatraz with Ferry & Audio Guide, $47.95) displaced the $87.30 Self-Guided Tour App as the dominant listing. The 46% price reduction removed friction at variant selection (S2C +7.0pp) and checkout (C2A +9.9pp). International markets benefited most: Canada +25pp, Australia +22pp, UK +8pp S2C. Residual gap: A2O −2.24pp, likely reflecting higher payment friction from increased international visitor share.

---

*Each future entry in this changelog corresponds to one GitHub push. Format: `[vX.Y] — YYYY-MM-DD — Short title` followed by a summary of what changed and why.*
