# CE-RCA Skill — Changelog

This file tracks every meaningful change pushed to this repository. Each entry
is written for stakeholder consumption — what changed, why it matters.

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
