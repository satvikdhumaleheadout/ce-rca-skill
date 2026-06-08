# CE-RCA Skill — Changelog

This file tracks every meaningful change pushed to this repository. Each entry
is written for stakeholder consumption — what changed, why it matters.

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
