# CE-RCA Skill — Changelog

This file tracks every meaningful change pushed to this repository. Each entry
is written for stakeholder consumption — what changed, why it matters.

---

## [v2.45.0] — 2026-06-16 — Shapley drivers are computed including PMax (so contributions reconcile to total revenue)

**Summary:** The §7 Shapley decomposition splits the revenue change into six factors (`revenue = traffic × CVR × orders/converter × AOV × completion × take rate`). Its **revenue numerator** (orders, bookings, revenue) comes from `combined_entity_stats` — **all channels, including PMax**. But its **funnel factors** (traffic = LP users, converters → CVR + orders/converter) came from the Mixpanel funnel with **PMax excluded**. That asymmetry — orders counted PMax, converters not — landed entirely in the **orders/converter** factor and inflated it (on CE 2567, ~18% of converters were PMax users dropped from the denominator while their orders stayed in the numerator). With PMax conversion tracking now fixed upstream, we **include PMax in the whole Shapley computation** so traffic + CVR + orders/converter share the all-channels basis of revenue and each driver's contribution / share / total is correct.

What changed:
- **Shapley computation → all channels (incl PMax).** The engine sidecar (`compute_shapley_for_ce`, which feeds the Step-1 driver preview) now reads new all-channels funnel keys (`lp_viewers_all` / `cvr_all` / `order_completers_all`), and the §7 waterfall query (`render_ce_health._FUNNEL_SQL`) drops its PMax exclusion. Reconciliation verified on CE 2567 (`unattributable = $0`), with converters moving from 1,055 (PMax-excluded) to 1,286 (all-channels).
- **Everything else stays PMax-excluded (Omni basis), unchanged.** The funnel section, the per-TGID funnel, and the remaining vitals cards (Users / CVR / Revenue / AOV / …) keep the Omni basis exactly — `fetch_ce_funnel` adds the `*_all` keys via conditional aggregation, leaving every existing Omni key byte-identical.
- **"Orders / Converter" vitals card removed** from the orchestrator Step-1 call-out (SKILL.md) and the CE Health §2 vitals report (`render_ce_health.py`). It is rarely a headline mover, and its Omni basis would contradict the all-channels Shapley driver; it now survives only as a Shapley driver.
- **Disclosure note on every Shapley surface** — *"Shapley drivers are calculated including PMax (all channels) so contributions reconcile to total revenue; vitals exclude PMax and may read differently"* — in the Step-1 preview (SKILL.md), the §7 waterfall (render), and the Summary driver table (`summary_guide.md`).

Note: PMax funnel data is only reliable since the upstream conversion-tracking fix, so very old comparison windows may still under-count PMax converters (a residual that shrinks over time). Including PMax across vitals + funnel everywhere is a deliberate later step.

### Blast radius
- `skills/ce-health/ce_health.py` (`fetch_ce_funnel` adds `*_all` keys; `compute_shapley_for_ce` reads them), `scripts/render_ce_health.py` (`_FUNNEL_SQL` all-channels, §7 annotation, Orders/Converter §2 card removed), `SKILL.md` (Step-1 row removed + annotation + format-rule cleanup), `references/summary_guide.md` (driver-table annotation) + changelog row m080; `CHANGELOG.md`; `VERSION` 2.44.0 → 2.45.0. No `compose.py` / template / CVR-RCA / perf-audit / contract change; standalone `engine/sources/bq.py` untouched (no re-vendor).

---

## [v2.44.0] — 2026-06-16 — Summary tab is framed to the user's goal (reconciled against the data)

**Summary:** The goal the analyst picks at the start (0b) shaped the *intake* but never reached the *report*. Now the **Summary** — and only the Summary — uses it to **tilt the framing** of its headline callout and recommended next-steps toward what the user came for. No other tab/skill is touched, and the goal is never printed verbatim.

How it works (in `references/summary_guide.md`):
- **Tilt, don't restate.** The Summary derives a **posture** from the goal — *scale* (lead with what's working + levers to double down), *fix* (lead with root cause + remediation), *investigate* (lead with the answer to the specific question), or *neutral* (balanced). It classifies whatever the user picked **or typed in the free-text "Other" box**, so a custom goal still maps to the right posture.
- **The data wins.** Before tilting, it reconciles the posture against the headline direction (revenue Δ + top Shapley driver). If the stated goal contradicts the data — e.g. "scale" but revenue is down — it tilts to the **data-aligned** posture, never the stated one. The tilt only changes *emphasis and ordering*; it can never spin what the data shows (a decline stays a decline). On a conflict it may note the mismatch in one short clause, but the framing follows the data.
- **Everything else stays pure synthesis** — facts, drivers, and verdicts are whatever the tabs found; the goal only decides what leads and which actions surface first.

### Blast radius
- `references/summary_guide.md` (new "Goal-aware framing" section + `## Goal` input note + flow-row tags) + changelog row m079; `CHANGELOG.md`; `VERSION` 2.43.1 → 2.44.0. Summary-only — no other skill, renderer, `compose.py`, or contract change.

---

## [v2.43.1] — 2026-06-16 — Step-1 vitals: money is USD — always show the `$` symbol (never localize)

**Summary:** On a non-US CE, the Step-1 vitals preview showed AOV (and other money rows) with a **£/€ symbol** — so it looked like "AOV in local currency." It wasn't: the **value is correct USD** (the engine reads `*_usd` columns; `combined_entity_stats` is USD-normalized — verified CE 243/EUR AOV `$264.53` matches `fct_orders.order_value_usd` exactly, with no FX-factor divergence on any CE), and the **code is clean** (`render_ce_health.money()` hardcodes `$`). The culprit was the **in-chat Step-1 preview**, which the orchestrator writes at runtime — seeing the CE's "London · UK" / "Paris · Europe" metadata pills, the model localized the currency symbol.

Fix: an explicit instruction in §1 — **all preview money (Revenue, AOV, Shapley `$` contributions) is USD; always render `$`; the market/country pills are the CE's *location*, not its currency; never swap in £/€/₹/¥.** A UK CE's AOV is `$264`, not `£264`. Note-only — the rendered CE Health HTML tab already hardcodes `$`; no engine/render/contract change.

**Also surfaced (separate, deeper — not fixed here):** perf-audit's *paid-side* metrics (spend, conversion value, CM1, ROI, CPC) come from Google-Ads tables in the **account's native currency**, with **no `_usd` column** to switch to. For a non-US Google Ads account those are genuinely non-USD; fixing it properly needs upstream USD-normalization (FX-by-date) or explicit currency labeling — flagged for separate/owner work. CE Health and CVR-RCA money are all USD.

### Blast radius
- `SKILL.md` §1 (the USD/`$` note) + changelog row m078; `CHANGELOG.md`; `VERSION` 2.43.0 → 2.43.1. No engine / renderer / `compose.py` / contract change.

---

## [v2.43.0] — 2026-06-15 — "Orders / Converter" added to the vitals; Shapley label corrected

**Summary:** The §7 Shapley waterfall decomposes a 6-factor identity — `revenue = traffic × CVR × orders-per-converter × AOV × completion × take-rate` — where **orders-per-converter = orders ÷ converting users** (users who completed an order). We verified it's a correct, well-formed factor: the identity telescopes to revenue exactly (`unattributable ≈ $0`). But two gaps: it was **not shown in the vitals** (so the Shapley "Orders / Converter" driver could move with no vitals row explaining it), and it was **mislabeled "Orders / User"** — imprecise, because it's per *converter*, not per all users (orders/traffic would be a different number).

Now:
- **Shown in the vitals** — the CE Health §2 cards gain an **"Orders / Converter"** card (pre→post + % change), slotted after CVR; the Step-1 in-chat vitals table gains an **Orders/Conv** row. So the vitals now display all six Shapley factors (Users · CVR · Orders/Converter · AOV · Completion · Take Rate).
- **Label corrected** — "Orders / User" → **"Orders / Converter"** in the §7 waterfall and the engine insight line.

The data already existed (`order_completers` is fetched per window for the Shapley), so the engine change is a single merge onto each window's sidecar `vitals`, mirroring how CVR and Users were added.

### Blast radius
- `skills/ce-health/ce_health.py` (vitals merge + insight label), `scripts/render_ce_health.py` (§2 card + §7 label), `SKILL.md` (Step-1 row landed in v2.42.2 + changelog row m077), `CHANGELOG.md`, `VERSION` → 2.43.0. None-safe for older sidecars; no `compose.py` / template / CVR-RCA / contract change. Verified: both files parse; an injected sidecar renders the card; no "Orders / User" remains.

---

## [v2.42.2] — 2026-06-15 — 1c bucket questions lead with the bucket name

**Summary:** A live run showed the four constraint pop-ups rendering only the MMP observation ("From MMP: … Anything to add?") with **no visible bucket label** — you couldn't tell which of Supply / Landing Page / PPC / Pricing you were answering. We'd been relying on the `AskUserQuestion` `header` chip to carry the bucket, but it's ~12-char-capped ("Supply / Availability" doesn't fit) and isn't prominent in every client. Now the **question text itself leads with the bold bucket name**, so the order is always **bucket name → the MMP observation → "anything to add or correct?"** (e.g. *"**Landing Page** — From MMP: SD→SF URL change… Anything to add or correct?"*). Structure/wording only — no behaviour change.

### Blast radius
- `SKILL.md` §1c (question table + pre-fill shape) + changelog row m076; `CHANGELOG.md`; `VERSION` 2.42.1 → 2.42.2.

---

## [v2.42.1] — 2026-06-15 — "Your read" question: plainer wording

**Summary:** A live run surfaced the 1e question as *"What's the scalable lever you want sized, and where should I dig first?"* — too jargon-y. The §1e template now mandates **plain language, no jargon** (ask it the way you'd ask a colleague), with the default phrasing simplified to *"what do you think is driving this, and where should I dig first?"* and plainer examples. Wording only — no behaviour change.

### Blast radius
- `SKILL.md` §1e + changelog row m075; `CHANGELOG.md`; `VERSION` 2.42.0 → 2.42.1.

---

## [v2.42.0] — 2026-06-15 — The post-reveal "Your read" hypothesis ask becomes a pop-up too

**Summary:** The driver-hypothesis ask shown after the numbers ("💡 Your read on the driver…") was the **last free-text prompt** left in the onboarding — every other step (goal, window, the constraint buckets, aliases) is now a structured `AskUserQuestion`. This converts it to match, so the whole front door is consistent.

The pop-up (header **"Your read"**): a one-line question + a short example, with the **free-text box as the primary answer** (the analyst's read / where to dig) and **two quick-buttons** — **"Run the default"** and **"Let Claude infer the lead"** — both meaning "proceed with no steer" (same text-box-first, two-button shape as the 1c buckets). Behaviour is unchanged: a typed read is written to the analyst's priors/focus before dispatch (CVR-RCA opens it as a prioritised branch), either button or a no-direction reply just dispatches the default, it's asked once, and a general health check skips it.

**Answering this is the dispatch trigger** — it runs the default set (CE Context + CVR-RCA + perf-audit). Letting the user **check/uncheck which skills to run** is a planned future add; the "what I'll run" panel in the reveal already previews the set.

### Blast radius
- `SKILL.md` §1e (the ask) + the post-reveal dispatch-parse block + changelog row m074; `CHANGELOG.md`; `VERSION` 2.41.0 → 2.42.0. Presentation/flow only — no `user_context.md` contract, renderer, `compose.py`, or sub-skill change.

---

## [v2.41.0] — 2026-06-15 — Slack made portable: dynamic tool discovery, runs on every install

**Summary:** A live end-to-end validation surfaced that the Slack sub-agent silently did nothing for most people who installed the skill from GitHub. The cause was a **hard-coded Slack MCP namespace** (`mcp__plugin_weekly-growth-review_slack__…`) baked into the skill in two places. Slack now **discovers its tools dynamically by name**, so it works with **any** connected Slack MCP regardless of how that server is named in the user's environment.

### What changed

- **Dynamic discovery (the real fix).** Both `slack_context_guide.md` files (ce-context + cvr-rca) and `ce-health`'s Step 4 previously loaded Slack with an **exact-id** `ToolSearch("select:mcp__plugin_weekly-growth-review_slack__…")`. That returns nothing unless the user's Slack MCP happens to sit under that one specific plugin name — so for nearly everyone, no Slack tools loaded and the agent quietly skipped. They now use a **name-based** search — `ToolSearch("+slack search read channel thread")` — and call the tools by the exact names returned. Any Slack MCP namespace works.
- **Graceful when truly absent.** Each Slack site now has an explicit branch: *no Slack tools returned → write "Slack context unavailable" and skip — never fail the run.* So users with no Slack MCP degrade cleanly, and users with one finally get Slack.
- **De-pinned `allowed-tools`.** `ce-health` and `perf-audit` frontmatter pinned the same hard-coded Slack id in `allowed-tools`, which whitelist-blocked the real tool even after discovery (in standalone runs). Removed the pin — they now inherit the session's permissions, matching the `ce-context` sub-skill that owns the primary Slack search and never had a pin. (MCP server ids are environment-specific and can't be whitelisted at authoring time.)
- **Docs.** `ce-context/INSTALL.md` reworded: "any connected Slack server" — no specific plugin required.

### Why it matters

This was the one finding from the v2.40.0 validation that genuinely broke on a fresh clone (vs. machine-local credential quirks). Anyone who installs the skill and has a Slack MCP connected now gets the operational Slack stream automatically.

### Verification

Zero `plugin_weekly-growth-review_slack` / `select:mcp__` references remain in any runtime file; dynamic discovery confirmed present at all four Slack call sites.

---

## [v2.40.0] — 2026-06-15 — perf-audit CSV ask moved to a pre-dispatch gate (with where-to-export steps)

**Summary:** The Google-Ads CSV request for perf-audit (Auction Insights → §6b, Search Terms → §8) was in the Step-1 input menu — premature and contextless, since the user hasn't yet committed to running the paid audit. Moved it to a **short, single-purpose pre-dispatch gate** that fires **only when perf-audit is in the run**, right after the user confirms the default run and just before the parallel CE-Context + CVR + perf-audit spawn. The gate now also **tells users where to export the CSVs from** (so the ask is actionable), with full parsing detail still living in perf-audit's Step 0.

### What changed
- **`SKILL.md`** — removed the CSV bullet from Step-1 1a and the CSV-capture paragraph from 1b; added the conditional pre-dispatch gate in Step 2 (concise where-from + attach/paste/`skip`, capture to `<run_dir>/uploads/`); repointed the perf-audit dispatch hand-off to "captured at the pre-dispatch CSV gate." No engine/sub-skill/renderer change.

### Why
- Step 1 is for reading vitals + setting direction; a Google-Ads-export request there is confusing and dilutes the input menu. Asking once perf is confirmed — with export instructions — is both contextual and actionable. Can't prompt mid-parallel, so just-before-dispatch is the only clean spot. `skip` degrades gracefully.

---

## [v2.39.0] — 2026-06-15 — Alias confirm (1d) now fires on every run, not just when Slack input was given

**Summary:** CE Context runs the Slack collector on **every** CE-RCA run, and CE aliases ("KSC" → Kennedy Space Center) are what let that search find threads that only ever used the nickname. So the alias confirm should be asked **every time** — but it was reading as part of the optional Slack/doc intake (skipped when no Slack link was pasted), and the **general-health-check light path skipped it entirely** (soft-context pop-up → straight to the reveal).

Fixed in `SKILL.md` §1: (1) the 1d step now opens with an explicit **"ask on every run — not conditional on Slack input"** instruction, with a call-out against the common mistake of treating it as Slack-only intake; (2) the light path now routes **soft-context → 1d (aliases) → reveal**, so even a health check (and a bare-`skip` run) confirms aliases before Slack runs. It stays near-zero friction (auto-proposed short-forms, one-tap confirm) and still skippable (confirm-nothing → the search falls back to name + id).

### Blast radius
- `SKILL.md` §1c (light path) + §1d + changelog row m071; `CHANGELOG.md`; `VERSION` 2.38.0 → 2.39.0. Flow/wording only — the `ce_aliases` → `orchestration.json` → both Slack guides' Search-1 plumbing is unchanged; no renderer / `compose.py` / sub-skill-code change.

---

## [v2.38.0] — 2026-06-15 — Installer registers per-skill commands (`/ce-context`, `/cvr-rca`, `/perf-audit`, `/ce-health`) for standalone runs

**Summary:** Now that every sub-skill produces its own openable `report.html`, the installer registers a slash command for each — so a downloader can run **the whole RCA *or* just one piece**. `INSTALL.md` Step 3 now creates **five** commands instead of one:

- **`/ce-rca`** — the umbrella (CE Health → CE Context + CVR-RCA + perf-audit → one composite tabbed report).
- **`/ce-context <CE>`** — standalone CE orientation brief (about · timeline · prior RCAs · constraints · Slack).
- **`/cvr-rca <CE>`** — standalone funnel / CVR root-cause analysis.
- **`/perf-audit <CE>`** — standalone paid performance audit.
- **`/ce-health <CE>`** — standalone CE briefing packet (vitals · channels · funnel · L12M · Shapley).

Each sub-skill command is a tiny file pointing Claude at that skill's **vendored** `SKILL.md` inside the bundle with a "run standalone → its own `report.html`" instruction. This works with **no separate installs and no path config**: each sub-skill sets `SKILL_DIR` to its own folder, so its `$SKILL_DIR/../../scripts/` references resolve to the bundle's `~/.ce-rca/scripts/` and the shared renderers stay reachable. The "how to use" onboarding brief (Step 6) gains an **"Or run just one piece"** line listing the four standalone commands.

### Blast radius
- `INSTALL.md` (Step 3 command registration + the Step-6 brief), `CHANGELOG.md`, `VERSION` 2.37.0 → 2.38.0. **No skill-logic / script / `compose.py` change** — purely how commands are registered at install time. (Existing installs pick up the new commands on their next install/update; users can also just run a sub-skill via natural language pointing at `~/.ce-rca/skills/<x>/SKILL.md`.)

---

## [v2.37.0] — 2026-06-15 — Standalone HTML: perf-audit joins; + the full CE header (Omni · pre/post · pills) on standalone CE Context & CE Health

**Summary:** Two extensions of the standalone-report work (v2.36.0).

1. **perf-audit now emits a standalone HTML report.** `scripts/render_perf_audit.py` gains `--standalone` — default writes only the `perf_audit_tab.html` fragment (orchestrated path unchanged); `--standalone` also wraps it (via the shared `standalone_report` helper) into an openable `<run_dir>/report.html`. So perf-audit, run on its own, produces a browser-openable report like the other skills. (`skills/perf-audit/SKILL.md` documents the one-line invocation; graceful if the bundle renderer isn't reachable; unnecessary under `/ce-rca`.)

2. **Standalone CE Context & CE Health now carry the full composite header.** Instead of the lightweight banner, their standalone reports show the same header the orchestrator's composite does: CE identity, **📅 Pre / Post**, the **Omni dashboard link**, and the five CE-context chips — **Category · Subcategory · Evolution · Management · Status**. So a standalone CE Context report tells you, up top, *what this CE is* (e.g. *Non-POI · Day Trips · Growth · Managed · Hero*), which is exactly its job. The header is built from each skill's own data (CE Health's sidecar `metadata`; for a pure-standalone CE Context run, a new `ce_context_meta.json` written from its `dim_combined_entities` lookup) and **reuses `compose.build_header`** so it's identical to the composite — no `meta.json` dependency. perf-audit keeps a lightweight banner (the CE pills are a Context/Health concern); CVR-RCA is untouched (already has its own header).

### Blast radius
- `scripts/standalone_report.py` (new `build_omni_url`, `build_header_meta`, `build_rich_header`); `scripts/render_ce_{context,health,perf_audit}.py` (`--standalone` header wiring); `skills/{ce-context,perf-audit}/SKILL.md`; `CHANGELOG.md`; `VERSION` 2.36.1 → 2.37.0. **No `compose.py` / template / engine / CVR-RCA change.**
- **Verified** on real data: CE Context standalone header → Omni link + all 5 pills + pre/post; CE Health same; perf-audit standalone → openable doc with lightweight banner; orchestrated fragments + composite unchanged.

---

## [v2.36.1] — 2026-06-15 — Perf-audit tab: drop the redundant echo caption

**Summary:** The beautified perf-audit tab (v2.34.0) showed each section's name twice — the card title (or `<h3>`) plus a bold caption the perf-audit engine emits that merely echoes the heading (`## 3. Channel Breakdown` → `**Channel Breakdown**`; `### Ad Group Coverage` → `**Ad Group Coverage**`). `render_perf_audit.py` now drops a bold-only caption when it normalizes equal to the heading it sits under, while keeping informative labels like `**Table 1: CE Health …**`. Wording-preserving (removes only a pure duplicate the title already states). Verified on ce-3593 / ce-2174 / ce-243. Blast radius: `render_perf_audit.py` only.

---

## [v2.36.0] — 2026-06-15 — Standalone openable HTML reports for CE Health + CE Context

**Summary:** Run on their own, **CE Health** and **CE Context** now produce a browser-openable `report.html` — the same way CVR-RCA already does — so nobody collects context or runs a skill and ends up with only markdown/JSON (CE Health) or an un-openable HTML *fragment* (CE Context). The orchestrated `/ce-rca` composite is **byte-identical** to before.

**How:** the beautified renderers all emit the same `#tab-<id>`-scoped body fragment, so a single skill-agnostic wrapper serves them all.
- **New `scripts/standalone_report.py`** — `wrap_fragment(fragment, scope_id, title, banner)` builds a full `<!DOCTYPE html>` document reusing the **same visual-kit `<style>`** (from `references/visual_kit.md`) and the **same Plotly CDN** as the composite, wraps the fragment in `<div id="{scope_id}">` so its scoped CSS/JS resolves, and adds a lightweight identity banner (CE name · window · "<Skill> report") built from each skill's own JSON — no `meta.json` dependency. Standalone is a single always-visible pane, so charts render at full width immediately.
- **`render_ce_context.py` + `render_ce_health.py` gain `--standalone`.** Without the flag (the orchestrated path) they write only the fragment, exactly as before. With it, they additionally write `<run_dir>/report.html`. `skills/ce-context/SKILL.md` passes `--standalone` on standalone runs; `skills/ce-health/SKILL.md` gets an optional Step 3b (canonical artifact names + the bundle renderer, graceful if unreachable).
- **CVR-RCA** is untouched — it already hand-authors a full standalone report and remains the reference.
- **perf-audit** is a deliberate fast-follow: its `render_perf_audit.py` already emits a `#tab-perfaudit` fragment, so its standalone HTML is a one-line `--standalone` add using this same wrapper once that (concurrent) work settles. Not touched here.

### Blast radius
- New `scripts/standalone_report.py`; `--standalone` added to `scripts/render_ce_{context,health}.py`; `skills/{ce-context,ce-health}/SKILL.md`; `CHANGELOG.md`; `VERSION` 2.35.0 → 2.36.0. **No `compose.py` / template / engine / CVR-RCA / perf-audit change.**
- **Verified:** wrapper smoke (DOCTYPE + Plotly CDN + visual-kit CSS + `<div id="tab-…">` + banner); CE Context `--standalone` on real CE-3593 data → openable ~45 KB `report.html` (timeline + all blocks); CE Health `--standalone` on a real run → openable ~79 KB `report.html` (cards + Shapley waterfall); both default (no-flag) paths still emit only the fragment → composite unchanged.

---

## [v2.35.0] — 2026-06-15 — perf-audit CSV uploads collected at the Step-1 pause + owner's 8-tab Google-Sheet data dump restored (link in §B)

**Summary:** Two additions to how CE-RCA runs the vendored perf-audit. **(A)** Perf-audit's two optional Google-Ads CSVs (Auction Insights → §6b, Search Terms → §8) are read by Claude at the narrative layer, so the orchestrator now collects them **up-front at the existing Step-1 input pause** and passes the paths to the Step-2 parallel dispatch — eliminating perf-audit's mid-parallel interactive prompt. **(B)** The owner's Google-Sheet data dump (removed in the re-baseline) is restored as an 8-tab Sheet and **surfaced as a link in §B Data Sources** so it renders in the Paid-Performance tab. No engine `.py` change; standalone perf-audit synced separately; `vendor.sh` not run.

**What changed:**
- **`SKILL.md` (ce-rca) Step 1 — CSV ask consolidated into the input pause.** The **1a** input solicitation gains a 📈 Google-Ads-CSVs line: Auction Insights (competitor names → §6b) + Search Terms (clusters → §8), a short export hint inline, *attach / paste file paths / `skip`*. **1b** saves any attached/pasted file(s) into `<run_dir>/uploads/` (intact — perf-audit tells CY-vs-LY Auction Insights apart by reading line 2's date range), and carries the paths to Step 2; `skip` → none. One consolidated pause before the Step-2 dispatch — no separate prompt.
- **`SKILL.md` (ce-rca) Step 2 — perf-audit dispatch hand-off.** Passes the captured CSV paths (or `none`) and instructs perf-audit to **skip its Step-0 interactive upload prompt** (exactly as it's already told to skip its Step-1 date self-computation) and read the provided CSVs for §6b/§8, degrading gracefully if none. The existing `--l4w/p4w/ly` date-flag overrides + skip-Step-1 instruction are unchanged.
- **`skills/perf-audit/SKILL.md` Step 0 — orchestrator note.** Under an orchestrator, the CSV paths are provided (skip the prompt, consume the given files); standalone behavior unchanged.
- **`skills/perf-audit/SKILL.md` new Step 4b — 8-tab Google Sheet.** Re-added the owner's upstream Sheets step (between the Step-4 standalone funnel and the Step-5 self-eval, so the Step-6 gate-driven transcript stays LAST with `transcript_perf_audit.md` filename/contract unchanged). Owner's **try-in-order** mechanism verbatim: ① `gws` CLI → ② Sheets API v4 via `gcloud auth print-access-token` → ③ Google Drive MCP `create_file` → ④ local-CSV fallback (`.cache/perf-audits/...`). Imports **shimmed** to the bundle layout (`from scripts.perf_audit_engine_v6.sources.bq import …` → `from engine.sources.bq import …`; Tab-5 channel CASE → `engine/sources/bq.py`'s `_fetch_channel_window_v2`). Full 8 tabs: Search-term clusters · Top-50 keywords · Keyword universe · Auction insights · Campaign detail · LP funnel · Campaign×product · Ad-group audit. The link block (`**📊 Full data dump:** [Perf Audit — <CE> (<date>) ↗](<url>)` + tab list) is appended to **§B Data Sources** of the rendered `perf_audit_report.md` after Sheet creation (since `render_data_sources()` is engine-rendered, the SKILL appends it) — renders in the Paid-Performance tab. Local-fallback paths noted in §B when no Sheets/Drive access; never blocks the run.

**Verification:** Both `fetch_campaign_product_mix` and `fetch_ad_group_audit` confirmed present in the vendored `engine/sources/bq.py` and `from engine.sources.bq import …` resolves at runtime (the bundle already imports `from engine.…` internally) — no tab degrades. `engine/sources/bq.py` parses clean (no engine edits made). Gate, gate-driven transcript, Step-5b reconciliation, and the standalone funnel are all intact.

### Blast radius
- `skills/perf-audit/SKILL.md` (Step 0 orchestrator note + new Step 4b), `SKILL.md` (1a/1b CSV capture + Step-2 dispatch hand-off + changelog row m066), `CHANGELOG.md`, `VERSION` 2.34.0 → 2.35.0. **No perf-audit engine `.py` change, no `compose.py`/template/CVR-RCA change, no `vendor.sh`.** Standalone perf-audit-skill synced separately.

---

## [v2.34.0] — 2026-06-15 — Paid Performance Audit tab beautified (composite-side structured re-render, wording preserved)

**Summary:** The Paid Performance Audit tab rendered as plain markdown while CE Health and the Summary got visual_kit chrome. It now gets the **same structured re-render** — per-section `.analysis-block` cards with a coloured §1 verdict banner, beautified styled tables, and the supporting prose as grey text — via a new composite-side renderer. **perf-audit's wording is preserved verbatim:** the renderer only **relocates** the §1 Status line into the banner and **restyles** the layout; it never rewrites, summarizes, re-words, re-rounds, drops, or reorders any prose or table cell. This relaxes the old "verbatim-embed perf-audit" rule → "structured re-render, wording-preserving."

**What changed:**
- **New `scripts/render_perf_audit.py`** (clones `render_ce_health.py`, reuses its `section`/`tables_in`/`_cell`/`styled_table` helpers + `helpers.render_markdown_to_html`/`slugify`). Reads the final `perf_audit_report.md` (subfolder-first: `reports/` then root), writes a body fragment `perf_audit_tab.html` (to `tabs/` on an organized run, else root). Per `## N.`/`## A.`/`## B.` section → one `.analysis-block` card (id `perfaudit-<slug>`, slug identical to the markdown renderer so cross-tab `↗` links resolve), in order: **(1)** a `.pa-verdict` banner **only when a leading `**Status: …**` line exists** — coloured by the Status **text token, emoji ignored** (CRITICAL → red, WARNING → amber, HEALTHY/OK → green), the line shown verbatim; no Status line → neutral titled card; **(2)** every GFM table → `styled_table(...)` (§9 Red-Flags rows tinted by CRITICAL/HIGH/MED/LOW), with a scoped `#tab-perfaudit` readable-wrap style so wide tables don't crush; **(3)** the remaining paragraphs + any `###`/`####` subheadings rendered verbatim as muted grey `.pa-prose`. Tables + prose render in original document order below the banner. Degrades gracefully (prose-only, table-only, nested `###`, multiple tables) — never crashes.
- **`scripts/compose.py`** — the `perfaudit` `TAB_SPECS` entry switched from `{source: perf_audit_report.md, type: markdown}` to `{source: perf_audit_tab.html, type: html-fragment}` **with a `fallback` to `{source: perf_audit_report.md, type: markdown}}`** (mirrors the CE Health entry); `perf_audit_tab.html` registered in `_SUBDIR` (`tabs/`) for subfolder-first resolution. One-entry + one-map-line change.
- **`SKILL.md`** — new **Step 4c-perf** invokes `render_perf_audit.py --run-dir`, **non-fatal** (failure → no fragment → compose falls back to markdown); Step 4d composer note + Step 4f organize (`tabs/` move) updated; changelog row m065.
- **`references/composition_rules.md`** — cardinal rule updated: perf-audit moves verbatim-embed → wording-preserving structured re-render; new "Paid Performance Audit tab" section documents the banner/table/grey-prose/card shape + the markdown fallback.

### Blast radius
- `scripts/render_perf_audit.py` (new), `scripts/compose.py` (1 `TAB_SPECS` entry + 1 `_SUBDIR` line), `SKILL.md` (Step 4c-perf/4d/4f + changelog row m065), `references/composition_rules.md`, `CHANGELOG.md`, `VERSION` 2.33.0 → 2.34.0. **No change to the perf-audit skill, its wording, its engine, the coverage gate, or the transcript; no `vendor.sh`.** Reuses existing visual_kit classes (`.analysis-block`/`.callout` palette/`.md-content`) + one scoped `#tab-perfaudit` style. Verified on three real runs — CE 243 (CRITICAL → red), CE 3593 (CRITICAL + trailing prose → red), CE 2174 (WARNING → amber): each section a card with a beautified table + grey prose; wide §5/§9/§10 tables readable; rendered visible text byte-equal to the source markdown (only the verdict line relocated); deleting the fragment falls back to the markdown tab; all `perfaudit-*` cross-tab anchors resolve; other tabs byte-identical.

---

## [v2.33.0] — 2026-06-15 — Window confirmation → a one-click preset picker

**Summary:** The Step-0c window step was a free-text "here's the default — confirm or name your own," which made the user read a sentence and type. It's now a one-click **`AskUserQuestion`** picker (header "Window") with the standard comparisons ready to choose — the same structured-input treatment we gave the goal question (0b) and the constraint buckets (1c).

Four presets (+ the auto **"Other (custom dates)"** — the tool caps a question at four options):
- **Last 30 days vs prior 30** — the rolling default (`today−30 → today−1` vs `today−60 → today−31`).
- **Month-over-month** — last complete calendar month vs the month before.
- **Quarter-over-quarter** — last 3 complete calendar months vs the prior 3.
- **Year-over-year** — last 30 complete days vs the **same 30 dates last year** (post − 364 days).
- **Other** — any custom pre/post (non-contiguous or unequal-length allowed), honored verbatim.

Each preset resolves to **concrete dates computed from today** (windows end yesterday; today is partial/excluded) and becomes the **one run window** — the four dates (`pre_start`/`pre_end`/`post_start`/`post_end`) every component already consumes. The Step-0e CE-Health flag mapping is spelled out (preceding-equal pre → `--start/--end`; YoY/custom-gapped pre → add `--pre-start/--pre-end`), and the same dates flow to CVR-RCA's four-date args at Step 2.

### Blast radius
- `SKILL.md` Step 0c (+ changelog row m064), `CHANGELOG.md`, `VERSION` 2.32.0 → 2.33.0. **Presentation-only** — no engine / `compose.py` / sub-skill / template change; the downstream window plumbing (0e dispatch flags, CVR-RCA four-date args, CE Health sidecar `windows`) is untouched.

---

## [v2.32.0] — 2026-06-15 — perf-audit gains a Step-5b context reconciliation feeding its coverage gate; Summary anti-circularity guardrail

**Summary:** perf-audit used to read **no context lenses** — its v6.2 coverage gate (Section 9: CONFIRMED / RULED-OUT / DATA-GAP) closed from its **own paid data only**, while CVR-RCA already had a rich Step-2b reconciliation. This ports the same **four-pattern reconciliation engine** into perf-audit (in perf's own wording), over **CE Health + user-context + Slack**, feeding its coverage-gate dispositions — and adds an explicit **anti-circularity guardrail** to the Summary. **perf does NOT read CVR** — the Perf↔CVR peer weave stays confined to the neutral Summary synthesiser.

**What changed:**

1. **`skills/perf-audit/SKILL.md` — new "Step 5b — Context reconciliation"** (inserted after Step 5 self-eval, before the Step 6 gate-driven transcript). Conditional + additive. Reads whichever lenses are present in `<run_dir>`: `ce_health_report.md` (widest/upstream), `user_context.md` (intent/priors/constraints/known events), `slack_context.md` (operational colour). **Explicitly does NOT read CVR-RCA's `findings.md`/transcript/report.** Four-pattern model in perf's language — **A** corroborate (lens names same campaign/date/segment → close the gate signal CONFIRMED with the cross-citation), **B** mechanism (lens explains the *why* the paid data lacked), **C** reframe (CE Health Shapley names a non-paid headline driver → paid finding real but not the headline, point to CE Health), **D** testable gap (one bounded paid-data check, else DATA GAP), **Reject** (symptom-only). It **feeds the v6.2 coverage gate** — the reconciliation evidence disposes each Section 9 signal, and the Step-6 gate-driven transcript reflects the lens evidence — **not a parallel mechanism** (gate + transcript contract: filename/location/format unchanged). User context: constraints filter/annotate recommended actions (never recommend a disallowed lever — no same-day, PPC restriction, ticket-only), known events corroborate paid timing, priors closed with proportional output. **Standalone-safe:** no lenses → clean no-op; report, gate, and transcript identical to today; no dangling `#cehealth-*`/Slack/`(per user context)` citations.

2. **`SKILL.md` (ce-rca) Step 2 dispatch** — the perf-audit dispatch prompt now also tells perf-audit to read the three context lenses from `<run_dir>` for its Step-5b (`ce_health_report.md` always, `user_context.md`/`slack_context.md` if present) and to **NOT** read CVR-RCA's output. Date-flag overrides + skip-Step-1 instruction unchanged.

3. **`references/summary_guide.md`** — anti-circularity guardrail at the "provenance over polish" block: corroborate via independent evidence or a shared upstream CE-Health anchor, never peer-conclusion-as-proof; the cross-reference "Corroborated by" column must be an independent measurement/source, not the other tab restating the same conclusion.

**Preserved:** v6.2 engine + coverage gate + gate-driven transcript; perf's standalone funnel (no `/cvr-rca`); CVR-RCA untouched; the Perf↔CVR weave stays Summary-only. **Vendored perf-audit copy edited only — `vendor.sh` not run** (the standalone perf-audit-skill is synced separately). No perf engine / `compose.py` / template / CVR-RCA change.

---

## [v2.31.0] — 2026-06-15 — CE Health per-section grounded insight callouts, enriched from CE Context

**Summary:** Every CE Health section now **leads with a 2–3 line insight callout** that says *what the data means* — so a stakeholder reads the callout and uses the table only to verify, instead of interpreting raw numbers themselves. Three sections already carried deterministic callouts (Channels, Lead-time, Shapley); this extends a grounded one-liner to **all** sections, and — the new idea — **enriches** each with the **CE Context** tab so a data finding connects to its real-world cause (a dated event, an inventory/PPC/price constraint, a known failure mode) via a `↗` backlink to `#cecontext-*`.

**The framework — Python computes the facts, the LLM only phrases:**

1. **Facts pack (`render_ce_health.py --emit-facts`).** A new deterministic mode runs `compute_facts(run_dir)` and writes a compact `ce_health_facts.json` keyed by section id (`vitals`/`l12m`/`shapley`/`channels`/`funnel`/`tgids`/`landing-pages`/`vendors`/`leadtime`/`countries`). Each entry holds only that section's key numbers + computed flags (e.g. `funnel:{worst_step:"C2O",delta_pp:-6.3,others_ok:false}`, `tgids:{top_share_pct,top3_share_pct,classification,flagship_moves}`, `leadtime:{dominant_band,share_pct,skew}`); Channels/Lead-time/Shapley also embed their existing deterministic summary string as `det_summary`. It reads `ce_health_report.{md,json}` + the existing generators — **no bq, no raw table dumps** — so it's fast and reproducible (~4KB on ce-3593).

2. **The insights sub-agent (`references/ce_health_insights_guide.md`).** A new contract: read the facts pack (data backbone) + the run's CE Context artifacts (`ce_context_constraints.json`, `ce_context_timeline.json`, `user_context.md`, `ce_history.json`), and write `ce_health_insights.json` = `{section_id: {insight, sentiment}}`. The core is a **two-stage rule**: (1) the **data line** cites a number from *this section's facts only*, verifiable against the table beneath it; (2) **enrich** with at most **one** genuinely-relevant CE Context item, attributed with a `↗` to the right `#cecontext-*` anchor — context enriches, never overwrites, and no claim is made without a supporting fact. Includes a section→context relevance map, anti-junk checklist (preserve LP2S/S2C/C2O/TGID/AOV/TR jargon), and worked examples.

3. **Render embeds the insights.** `render_ce_health.py` loads `ce_health_insights.json` once (graceful: absent/invalid → `{}`) and at each section's `block(...)` prefers the LLM insight, **falling back** to the deterministic summary: Channels/Lead-time keep their rule-based summaries, Shapley keeps its computed `verdict` only when there's no insight (when present, the insight becomes the `summary` and the verdict is dropped), and the previously-bare sections show no callout when no insight exists. A failed or absent sub-agent never blanks or breaks the tab.

4. **Dispatch (`SKILL.md` Step 3/4).** Step 3a runs `--emit-facts`; Step 3b spawns the CE-Health-insights sub-agent (parallel to the Summary synthesis agent, both consuming finished artifacts); both are waited on before Step 4. Step 4c notes the render now also reads the insights file.

### Blast radius
- `scripts/render_ce_health.py` (`--emit-facts` + `compute_facts` + insight embedding), new `references/ce_health_insights_guide.md`, `SKILL.md` (Step 3/4 dispatch + changelog row m062), `references/composition_rules.md` (doc), `CHANGELOG.md`, `VERSION` 2.30.0 → 2.31.0.
- **No CE Health sub-skill change, no CE Context sub-skill change** (we only *read* its artifacts), no `compose.py`/template change, **no new CSS** (callouts render through the existing `block(summary=…)` → `.ceh-summary`/`.verdict-line`/`.ref-link`).
- **Verified** on ce-3593: `--emit-facts` writes a compact facts pack whose numbers match the tables (funnel C2O −6.3pp worst step, Google Search 57%, 7D+ 68% lead-time, top TGID 45%); full render with no insights file keeps §3/§9/§7 deterministic callouts (2 `.ceh-summary` + 1 `.verdict-line`, gap sections none) and the tab is intact; with an insights file present, callouts embed with `↗` links and the Shapley verdict swaps to the insight summary.

---

## [v2.30.0] — 2026-06-15 — Onboarding §1c: general-context reframe · a 5th catch-all question · 2-option simplification

**Summary:** Three refinements to the input-rich questionnaire (Step 1c), all driven by real use and all **presentation-only** — the `user_context.md` slot contract is unchanged, so nothing downstream (CVR-RCA's Signal-0/Step-2b, the `slack_probes` derivation, the CE Context renderer) is affected.

1. **General context, not window-pinned.** The four bucket questions (Supply/Availability · LP · PPC · Pricing) dropped the post-window pin ("…in `<window>`?") and now ask for constraints · notable changes · known issues **"recently or in general."** 1c's job is durable CE context — single-vendor supply, a PPC restriction, what usually breaks — which is often timeless, not period-specific recall. The questions are also kept **short and structured** (never a run-on): the bucket is the chip header, the body is one tight line, and a pre-filled bucket **leads with the MMP finding** + a brief "anything to add or correct?" — not the generic stem, the finding, and the confirm tail all stacked into a paragraph.
2. **A 5th "anything else?" catch-all.** After the 4-bucket pop-up, a second pop-up asks *"Anything else about this CE before I dig in?"* — the safety net for context that doesn't fit the four buckets or isn't in the MMP doc (an off-doc PPC restriction, a vendor-API quirk, a pricing war), prompted with 📅 known-events / 🚧 constraints / ⚠️ what-usually-breaks examples. It routes to the same `## Known events` / `## Constraints` / `## Known failure modes` slots. (It's a separate pop-up because `AskUserQuestion` caps a call at four questions, and the buckets already fill one.)
3. **Cleaner options — text box first, two buttons.** Every questionnaire question now treats the **free-text box as the primary answer** ("type what you know…") with exactly **two terminal quick-buttons — "Let Claude infer" and "Nothing to add."** The old three near-duplicate buttons (`Looks right` / `Skip` / `Let Claude infer`) are collapsed, and there's deliberately **no "Add context" button** — it's redundant with the text box and just invites pointless clicking. Two buttons is the tool's hard minimum; these are the two genuine non-typing choices.

### Blast radius
- `SKILL.md` §1c (the questionnaire) + the intro/1a/1b skip-semantics cross-references + changelog row m061; `CHANGELOG.md`; `VERSION` 2.29.0 → 2.30.0. No renderer / `compose.py` / sub-skill / template / contract change. Verified: bucket questions no longer window-pinned, the 3-option list is gone, the 5th pop-up + 2-button naming are present, and a bare run still resolves to empty slots → the autonomous path.

---

## [v2.29.0] — 2026-06-15 — CE Health §6b Top Landing Pages: MoM ↔ YoY comparison toggle

**Summary:** The §6b Top Landing Pages sales table gains a **"Compare current vs: Pre period / LY (same period)"** dropdown — the same toggle the TGID table already has (v2.19). The LY data was already fetched by `fetch_top_landing_pages` (`rev_ly / orders_ly / aov_ly / cr_ly / tr_ly`), so this is a render-layer mirror of the TGID pattern — **no new query**.

- **Engine** (`ce_health.py render_top_landing_pages`): refactored to emit **two tables** under the §6b heading — `[0]` MoM (current vs prior) and `[1]` YoY (current vs LY-same-period), via a shared `_row(t, basis)` (only the delta tokens differ). Mirrors `render_tgids_enriched`'s two-table emission.
- **Renderer** (`scripts/render_ce_health.py`): when the §6b section carries a second table, wrap both `build_landing_main` outputs in the `build_fdim_dropdown` toggle (`vs Pre period` / `vs LY (same period)`, label "Compare current vs:") — identical to the TGID toggle. MoM-only (no LY) falls back to a single table, as before.

### Blast radius
- `skills/ce-health/ce_health.py` (`render_top_landing_pages`), `scripts/render_ce_health.py` (§6b block), `CHANGELOG.md`, `VERSION` 2.28.0 → 2.29.0. No new query, no compose/template/sidecar/other-skill change.
- **Verified** on CE 243: engine emits 2 landing tables (MoM + YoY markers); render shows the §6b dropdown with both `mom`/`yoy` panels, the select widget, and 2 landing tables in the section; TGID toggle + all other CE Health sections intact.

---

## [v2.28.0] — 2026-06-15 — Re-baselined vendored perf-audit on upstream v6.2.0 + re-applied CE-RCA-compat

**Summary:** Adopts the owner's perf-audit **v6.2.0** wholesale as the vendored skill, then re-applies a thin CE-RCA compatibility layer on top. v6.2.0 is a re-architecture: a deterministic **coverage gate** (`engine/signals.py` enumerates every material mover; the Section 9 "Signals to Close" table forces a **CONFIRMED / RULED OUT / DATA GAP** disposition per signal), plus `avg_cm1`, Shapley-first driver ordering, ±5% thresholds, PMax fixes, and an output/language overhaul. The gate **supersedes** our prior hand-built tree transcript (m049) and our earlier engine consolidation — the owner's PMax/offline-CM engine is now authoritative.

**What was re-baselined (Step 1):** `engine/` wholesale (new `signals.py`, `smoke_test.py`; updated `bq.py`, `metrics.py` with `avg_cm1`, `render/audit_skeleton.py` with the gate render), plus `DIAGNOSTICS.md`, `EVAL.md`, `references/`, `README.md`, `CHANGELOG.md`, `MIN_VERSION`, `setup.sh`.

**CE-RCA-compat re-applied:**
- **Path/name shim (Step 2)** — so it runs standalone in the bundle: `perf_audit.py` `_repo_root` (one `dirname`), `from engine.cli import …`, `PERF_AUDIT_VERSION="v6.2"`, usage strings → `perf_audit.py`; `engine/cli.py` `prog="perf_audit …"`; every `scripts.perf_audit_engine_v6.*` import → `engine.*` (cli, smoke_test, bq); `smoke_test.py` `_repo_root` (two `dirname`s for the bundle layout). Whole-tree grep for `scripts.perf_audit_engine_v6` / `scripts/perf_audit_v6.py` = **0**. `VERSION` = `6.2.0`.
- **Execution Modes (Step 3)** — re-added the Mode 1 (full engine) / Mode 2 (SQL-only) section.
- **Funnel decoupled from `/cvr-rca`** — restored the standalone paid-session BQ funnel (`mixpanel_user_funnel_progression`, paid sessions only). No external-skill invocation anywhere; the deep funnel decomposition (device / experience / C2O sub-stages / LY gap) is deferred to CE-RCA's own CVR-RCA tab. Section 7 rules, Step 4, the report-structure line, the actions-table rule, and the quality checklist all rewired.
- **Google-Sheets step removed** — dropped the 8-tab Sheet creation step entirely; the campaign×product full matrix stays as a backend comment.
- **Gate-driven Step 6 transcript** — kept `transcript_perf_audit.md` (exact filename + run-dir / `orchestration.json` location + tree-map + detail format). Now it **wraps the Section 9 coverage gate**: per enumerated signal it records hypothesis → check → disposition (CONFIRMED / RULED OUT / DATA GAP) as entered in the gate. Gate = formal record; transcript = its narrative wrapper for the Transcript-tab sub-tab.

**NotFound-retry resilience (Step 4):** Upstream v6.2's `bq.py` lacked the transient-`NotFound` retry/backoff our old fork had (clone-table refresh resilience). Ported it forward as a small additive patch onto v6.2's `run_bq_query` (linear backoff, 4 attempts, re-raise on exhaustion).

### Blast radius
- `skills/perf-audit/` only — `engine/` (incl. new `signals.py`, `smoke_test.py`), `SKILL.md`, `DIAGNOSTICS.md`, `EVAL.md`, `references/`, `README.md`, `CHANGELOG.md`, `MIN_VERSION`, `setup.sh`, `VERSION`, `perf_audit.py`.
- `compose.py` / templates / other skills **untouched** — the Section 9 gate table renders verbatim as markdown.
- `vendor.sh` **intentionally NOT run** (its `PERF_AUDIT_SRC` points at the old-fork standalone and would clobber the re-baseline; the standalone perf-audit-skill is synced to v6.2 separately).
- `SKILL.md` (m059 row), `CHANGELOG.md`, `VERSION` (→ 2.28.0).

### Verification
`ast.parse` clean on signals/bq/metrics/audit_skeleton/cli/perf_audit/smoke_test; `smoke_test.py` imports resolve under the bundle layout; `perf_audit.py` dispatch + `render --help` arg-parse work from the bundle; `render_signals_checklist` emits the gate table with CONFIRMED / RULED OUT / DATA GAP dispositions; whole-tree fork-token grep = 0.

---

## [v2.27.0] — 2026-06-15 — CE Health: landing pages = sales-only (drop mislabeled "RPC") · S2O added to every funnel cut

**Summary:** Fixes a metric-naming collision and cleanly splits sales vs funnel metrics across the landing-page / funnel-by-dimension sections.

**The bug:** "RPC" meant two different things. In the **TGID** table it's a genuine per-select-view efficiency metric (`RPC = S2O × AOV × TR`, using the per-TGID funnel join). In the **Top Landing Pages (§6b)** table it was silently just **net revenue ÷ orders** (`ce_health.py` query: `SAFE_DIVIDE(rev, orders)`) — no S2O, no funnel, no clicks — i.e. "net AOV" wearing a funnel-sounding name, redundant with the AOV column beside it. Confusing and not what "RPC" implies.

**The fix (sales vs funnel split):**
- **§6b Top Landing Pages → revenue/sales only:** dropped the "RPC" column. Now `Landing Page · Rev · Share · Orders · AOV · CR · TR`. (The TGID "RPC", a real funnel-efficiency metric, is untouched.)
- **Funnel metrics now carry S2O across every cut.** Added **S2O** (order-completers ÷ select-viewers) to the **Funnel by Channel**, **Funnel by Language**, and **§10 per-Landing-Page funnel** tables — so each funnel cut shows the full set `LP Users · LP2S · S2C · C2O · S2O · (Site CVR)`. The per-landing-page funnel uses Mixpanel's refined `page_url` (language-collapsed root), as before; revenue-by-landing lives in §6b, so the funnel cut stays purely funnel.

### Blast radius
- `skills/ce-health/engine/sources/bq.py` — `_fetch_funnel_by_dim` (+`s2o`), `fetch_lp_funnel` (+`l4w_s2o`).
- `skills/ce-health/ce_health.py` — `render_funnel_by_dimension` (+S2O col), `render_landing_pages` (+S2O col), `render_top_landing_pages` (drop RPC col + its row/computation).
- `scripts/render_ce_health.py` — `_landing_groups` docstring only (column resolution is name-based, so dropping RPC needed no logic change).
- `CHANGELOG.md`, `VERSION` 2.26.1 → 2.27.0. No compose/template/sidecar/other-skill change.
- **Verified:** engine ran on CE 243 — §6b header has no RPC (`Landing Page | Rev | Share | Orders | AOV | CR | TR`); Funnel by Channel/Language + §10 Landing headers all carry S2O; TGID RPC intact; render beautifies the new columns; all CE Health sections present.

---

## [v2.26.1] — 2026-06-15 — CE Context "About this CE": scannable labeled brief, not a paragraph

**Summary:** The "About this CE" block — the first thing someone being handed a CE reads — was a dense ~6-line paragraph cramming what/market/paid-mix/supply/status/source. It's now authored as a **short labeled brief** (a markdown bullet list: `- **What:** … · **Market:** … · **Paid:** … · **Supply:** … · **Status:** …`, one per line, omit what doesn't apply), which renders as a clean scannable list in the CE Context tab. Instruction-only change in the two places that write the slot (the `user_context.md` template + the MMP-doc ingestion contract) — **zero renderer change**, since the slot is already markdown→HTML'd. Bullets (not bare labeled lines) are required because the renderer collapses single newlines into one paragraph; verified that 5 labels render as 5 list items. Adaptive — a CE without paid just drops the Paid line.

### Blast radius
- `SKILL.md` (`user_context.md` template + changelog row m057), `references/context_ingest_guide.md` (extraction instruction + return contract), `CHANGELOG.md`, `VERSION` 2.26.0 → 2.26.1. No renderer / `compose.py` / contract change.

---

## [v2.26.0] — 2026-06-15 — CE Context "Timeline of changes": bubble-density swimlane + click-to-read panel

**Summary:** The CE Context timeline plotted every event as a bare dot you could only read by hovering — so a dense week (e.g. the burst of Slack threads around the Kens cease-&-desist) became an **unreadable pile of overlapping dots**, and the hover tooltip both got clipped at the chart edge and **couldn't hold a clickable link** (the Slack permalinks were dead). Same data, far more legible now:

- **Bubble-density swimlane** — events are binned by week and the **bubble size = how many signals** that week, so a 3-thread week reads as one big bubble instead of three colliding dots. The "we pulled context across all the buckets, concentrated around the analysis window" story now lands at a glance.
- **Click-to-read panel** — clicking a bubble lists that week's events in a panel below the chart, **with working ↗ links** to the Slack threads. A hover tooltip can't do either of those; the panel solves the clipping *and* the dead links. Hover stays as a quick, left-aligned, never-truncated preview.
- Lane traces are now **named** (Prior RCAs / Known events / MMP doc / Slack); the pre/post window shading is unchanged.

**Why it's safe:** pure presentation in `build_timeline_block` — **no change to the `ce_context_timeline.json` contract** the CE Context agent emits, no other CE Context block, no `compose.py`/template change. The click-detail lookup is keyed by `[curveNumber][pointNumber]` against an embedded array (not Plotly `customdata`, which silently mangles the ragged per-bubble event lists), and everything stays scoped to `#tab-cecontext`.

### Blast radius
- `scripts/render_ce_context.py` — `build_timeline_block` rewritten + new `_event_date` / `_week_key` / `_trunc` helpers + a `datetime` import. `CHANGELOG.md`, `VERSION` 2.25.1 → 2.26.0.
- **Verified** on CE 3593 real data (14 events): 4 named lanes, the May Slack cluster collapses to a single bubble, clicking it lists the three Kens-C&D threads with ↗ links; graceful-empty + pre/post bands intact.

---

## [v2.25.1] — 2026-06-15 — Closing chat diagnosis: structured line-items, not paragraphs

**Summary:** The end-of-run chat recap Claude writes above the report ("CE X — diagnosis") was emergent and unconstrained, so it came out as dense prose paragraphs. Step 4e now governs its **format**: a scannable, **labeled one-line-per-item** recap — `Headline · Root cause · Ruled out · Forward risk · Top action` + the "report open in your browser" line — **no multi-sentence paragraphs**. Content is unchanged (each line still earns its place for a large report); only the shape is structured, mirroring the Step-1 preview's "labels and numbers do the talking" rule. Omit any non-applicable bullet; depth belongs in the report, not the recap.

### Blast radius
- `SKILL.md` Step 4e only (+ changelog row m055). No script / template / sub-skill change.

---

## [v2.25.0] — 2026-06-15 — Summary tab front-pages the driver waterfall (reused from CE Health, not re-authored)

**Summary:** The Summary tab now opens its driver story with the **§7 Revenue-Waterfall chart** — the same visual the analyst sees in CE Health — placed **directly above the driver-decomposition table** (chart, then table, one story). Crucially it is the **exact same chart, reused**, not a second one the Summary draws itself: the §7 waterfall is a corrected Query-1 decomposition that lives only in CE Health's renderer (not the sidecar), so letting the Summary re-author it would risk **two different waterfalls for the same CE**. We clone the rendered chart at compose time instead — one decomposition, guaranteed consistent across tabs.

**How it works (timing-safe):** the Summary is authored at Step 3, CE Health renders its chart at Step 4c, and compose runs at Step 4d — so both exist when we need them. The Summary agent simply emits a placeholder `<!--SUMMARY_SHAPLEY_WATERFALL-->` above the driver table; `compose.py`'s new `inject_summary_shapley()` finds it, extracts the `chart-cehealth-shapley` div + its Plotly script from the rendered CE Health tab, **re-ids it `chart-summary-shapley`** (so the two Plotly instances don't collide), wraps it as a titled `analysis-block` with a `↗` back to `#cehealth-shapley`, and substitutes it in. The Summary is the active (first) tab, so the chart renders at full width on load.

**Graceful + lean:** no placeholder → unchanged; CE Health unrendered or Query-1 failed → the placeholder (an HTML comment) simply drops out, nothing breaks; existing finished runs (whose summaries have no placeholder) are byte-identical. **`render_ce_health.py` is deliberately untouched** (it's under active concurrent editing) — the reuse approach needs only the composer.

### Blast radius
- `scripts/compose.py` — new `inject_summary_shapley()` + one call in the summary `html-fragment` branch; new `_SUMMARY_SHAPLEY_PLACEHOLDER` + `_SHAPLEY_CHART_RE`.
- `references/summary_guide.md` — the Summary agent emits the placeholder above the driver table (block "3b"); explicit "do NOT author your own waterfall" guardrail.
- `CHANGELOG.md`, `VERSION` 2.24.0 → 2.25.0. **No** `render_ce_health.py` / template / engine / sub-skill change.
- **Verified:** unit-tested `inject_summary_shapley` — placeholder replaced, chart re-id'd to `chart-summary-shapley` (no `chart-cehealth-shapley` leak), `newPlot` retargeted, verdict line not pulled in (regex stops at first `</script>`), back-link present; graceful paths (no chart → placeholder removed; no placeholder → unchanged).

---

## [v2.24.0] — 2026-06-15 — Input-rich, goal-first onboarding (gather the analyst's context before the numbers)

**Summary:** Our users are growth managers with deep first-hand context on the CE — but the old Step-1 pause was a free-text "reply *continue* or steer" prompt people reflexively skipped, so runs lost that context and the weaker output got blamed on the skill. Onboarding is now **goal-first and input-rich**: we confirm *what the user is here to do*, actively solicit their context (docs / Slack / a voice dump), ask a short structured questionnaire, and only then reveal the numbers. Everything captured writes the **same `user_context.md` contract** (plus two new slots), so **nothing downstream changed** — CVR-RCA still consumes it at L0 (Signal 0) and Step 2b exactly as before.

**The new flow (all in `SKILL.md` Steps 0–2; dispatch stays Step 2):**
- **0a–0c:** resolve + **high-confidence CE confirm** → **ask the goal** (Understand growth · Diagnose a decline · General health check · Investigate a specific issue · something-else — posture-framed) → **one-tap window confirm**.
- **0e:** CE Health fires **in the background** while the user gives context — the diagnosis is ready by the reveal, the wait is free.
- **1a–1d (intake):** solicit context (MMP doc / sheets / Slack links / voice dump) → **ingest & mine** it (a pasted Slack thread is read directly; a rich upload **pre-fills** the questionnaire) → a **goal-adaptive bucketed questionnaire** (Supply/Availability · LP · PPC · Pricing — factual, before the numbers; "general health check" gets a light path) → **confirm CE aliases** (so the Slack search finds nickname-only threads like "KSC").
- **1e (reveal):** vitals + Shapley, a conditional **goal-vs-data reconciliation**, a neutral **"context captured (N of 4)"** count, a **"what I'll run / coming soon"** panel, then — for diagnostic goals — the **driver-hypothesis ask placed *after* the numbers** (where the expert's read is sharpest, grounded not blind).

**Why this is safe / lean:**
- **Same downstream contract.** The questionnaire's answers map to the existing `## Constraints` / `## Known events` / `## Known failure modes` slots; the goal and aliases are two additive slots (`## Goal`, `## Aliases`). Consumers that don't know a slot ignore it.
- **Forcing function preserved.** `skip` at the doc-ask means "no docs to share" — the questionnaire still runs (per-bucket *Skip / Let Claude infer* is the granular out). A one-word bypass of all intake is gone.
- **Ask once.** The grounded hypothesis is optional and asked a single time — a reply that only confirms aliases or says `go` dispatches immediately; the skill never re-prompts "where should I dig first?" (fixes an observed double-ask).
- **Aliases.** Both vendored `slack_context_guide.md` copies OR `ce_aliases` into Search 1; `context_ingest_guide.md` extracts aliases from docs to pre-fill the confirm.

### Blast radius
- `SKILL.md` Steps 0–2 (the restructure + changelog row m053); `references/context_ingest_guide.md` (alias extraction); both `skills/{ce-context,cvr-rca}/references/slack_context_guide.md` (Search-1 alias broadening — vendored divergence, **no `vendor.sh`**); `CHANGELOG.md`; `VERSION` 2.23.0 → 2.24.0.
- **No** `compose.py` / template / CE-Health-engine / CVR-RCA-consumption / CE-Context-renderer change. The `user_context.md` template gained `## Goal` + `## Aliases`; CVR-RCA's Signal-0/Step-2b reads whatever slots exist, unchanged.

---

## [v2.23.0] — 2026-06-15 — CE Health stakeholder pass: Step-1 YoY · metric-trajectory selector · "Where are bookings coming from?" L12M matrix

**Summary:** Three CE Health changes from the stakeholder feedback call (two render-only, one new engine).

**1. Step-1 diagnosis vitals table gains a YoY column.** The in-chat vitals table at the pause showed Pre / Post / Δ only; it now adds a **YoY** column (Post vs `vitals.ly_current` — the same LY window the CE Health 4-window table uses), same per-metric unit rule (% for Users/Revenue/Orders/AOV, pp for CVR/Completion/Take Rate), `—` when LY is absent. The sequential delta is labeled **"Δ (vs Pre)"** (not "MoM") to match the rolling-30 window established in v2.22.0. `SKILL.md` Step-1 template only.

**2. "Metric trajectory" — single-metric trendline selector.** The trajectory section (renamed from "Revenue Trajectory") replaces the fixed Revenue+Orders dual-axis chart with **one Plotly line chart + native `updatemenus` buttons** to switch the shown metric — **Revenue · Orders · ROI · Completion · Take Rate · AOV · CVR** — one at a time, with the y-axis title/format swapping per metric (single-select sidesteps the multi-axis problem). Default Revenue. The Paid Performance chart (Clicks + Paid ROI) and the YoY view (Revenue + CVR) are unchanged. All series already existed in the monthly health table — render-only, `scripts/render_ce_health.py`.

**3. New "Where are bookings coming from? (L12M revenue)" section.** A 12-month revenue matrix with a **Channel ↔ Landing Page** dropdown: column 1 = dimension name (frozen/sticky), 12 monthly-revenue columns (horizontal scroll), and a 13th inline-SVG **sparkline**. Top-10 by 12-month revenue; last 12 complete months (partial trailing month dropped). New engine fetches `fetch_monthly_revenue_by_channel` / `fetch_monthly_revenue_by_landing_page` (reuse the `_fetch_channel_window_v2` channel-classification CASE + `fct_orders` revenue) emit two markdown tables; the renderer beautifies them via the existing `build_fdim_dropdown` + `styled_table(sticky_cols=1)` + a new `_sparkline` helper. Placed right after §4 Channel Breakdown; the existing snapshot Channel + Landing tables are kept (they carry benchmark flags / CR / funnel the matrix doesn't). Graceful: missing table → muted note.

### Blast radius
- `SKILL.md` — Step-1 vitals table (W1) + `m052`.
- `scripts/render_ce_health.py` — metric-selector chart + section rename (W2); new `cehealth-bookings-source` section + `_sparkline` (W3).
- `skills/ce-health/engine/sources/bq.py` — `_shape_monthly_matrix` + `fetch_monthly_revenue_by_channel` + `fetch_monthly_revenue_by_landing_page` (W3).
- `skills/ce-health/ce_health.py` — `render_monthly_revenue_matrix` + wiring into `run_ce_health` (W3).
- `CHANGELOG.md`, `VERSION` 2.22.0 → 2.23.0. No `compose.py` / template / sidecar / other-sub-skill change.
- **Verified:** all `.py` parse; engine ran on CE 243 (both monthly tables, 12 month columns, top-10, partial month dropped); re-render shows "Metric trajectory" + the `updatemenus` selector (Revenue default, all 7 metric buttons) and the `cehealth-bookings-source` section (Channel/Landing dropdown, sticky first column, 12 month columns, 20 SVG sparklines) right after §4; W2 selector + all other sections intact.

---

## [v2.22.0] — 2026-06-15 — One rolling-30-complete-day window, identical across every tab (not month-over-month)

**Summary:** Two related window bugs fixed so a run analyzes exactly the period the user confirms, and **every component analyzes the same period**. (1) The "default" window shown to the user (a *rolling* last-30-days comparison) was not the window actually analyzed — the orchestrator fired CE Health with `--range month`, which resolves to **last complete calendar month vs prior calendar month** (a run confirmed against 2026-05-16→06-14 was silently analyzed as May 1–31 vs Apr 1–30). (2) Even with CE Health corrected, **perf-audit recomputed its own L4W/P4W/LY from today** (last 4 complete Mon–Sun weeks = a 28-day, week-aligned window), so the paid tab compared a *different* window than the health/funnel tabs.

**Root cause — orchestration, not the engines.** CE Health's `compute_windows()` already honored explicit `--start/--end` (+ `--pre-start/--pre-end`, v2.13.0), CVR-RCA already accepts four explicit dates, and `perf_audit.py render` already accepts explicit `--l4w/--p4w/--ly` dates. But the orchestrator used `--range month` for CE Health's default and let each deep dive fall back to its native cadence.

**Fix (one window, resolved once, passed explicitly everywhere).**
- **Default relabeled** to **"last 30 complete days vs the 30 days before it (rolling, not MoM)"**. "Complete" = the window **ends yesterday**; today is partial and excluded.
- **Step 0c** resolves the default to concrete dates from today: post = `today−30 → today−1`, pre = `today−60 → today−31`. These four dates are **THE run window**.
- **Step 0e** always invokes CE Health with `--start/--end` (+ `--pre-start/--pre-end` only for a non-contiguous pre); **`--range` is never used by the orchestrator** (kept for direct CLI use only).
- **Step 2** passes the identical four dates to every deep dive: **CVR-RCA** invoked as `<id> <pre_start> <pre_end> <post_start> <post_end>`; **perf-audit** told to **skip its Step-1 date self-computation** and run with `--l4w = post`, `--p4w = pre`, `--ly = post − 364d`; **CE Context** inherits the window from CE Health's sidecar. Result: CE Health, CVR-RCA, perf-audit, and CE Context all compare the **exact same period**.

**Accepted caveat:** perf-audit's tables still read "L4W/P4W" though the window is now 30 days, not 28 — a cosmetic label mismatch, not re-labeled because perf-audit is owned upstream. The Omni "default window" pill already used relative `30 complete days ago / 30 days` (rolling), so it aligns and is unchanged.

**Blast radius:** `SKILL.md` (Invocation + Steps 0c/0e/2 + changelog row), `CHANGELOG.md`, `VERSION`. No script / `compose.py` / template / sub-skill-code change.

---

## [v2.21.0] — 2026-06-15 — CE Context v2: bucketed Known-Constraints Q&A + per-RCA history table (stakeholder feedback)

**Summary:** Reworked the CE Context tab from a stakeholder feedback call so it **answers orientation questions in structured buckets** instead of dumping free text. The tab is reordered to the stakeholder template and gains two structured, agent-synthesized → renderer-plotted artifacts.

**1. Known constraints → bucketed Q&A.** A fixed, always-shown checklist — **Supply & availability · PPC restrictions · Notable price changes · Landing-page (LP) constraints · Vendor / selling-partner (SP) constraints** — each answered explicitly (⚠️ issue · ✓ none-known · ❓ unknown) with a one-line detail + source, synthesized by the CE Context agent from `user_context.md` (Constraints / Known events / Known failure modes) **+** `slack_context.md` **+** the `slack_probes` results into `ce_context_constraints.json`. The five are a **guaranteed minimum** — the agent appends extra buckets (content/catalogue, tech/API, seasonality, …) for anything else it finds. Honesty: no signal → `none_known`; not investigable → `unknown`; never fabricated.

**2. Recent Past RCAs → per-RCA table.** Replaces the loose trajectory prose with `ce_history.json`: one row per prior RCA, most-recent-first — `Window · Pareto finding (what concentrated) · Metric impact · Moved? (moved/didn't/partial/unknown, colour-coded) · Why · ↗`. Answers, per past RCA: what we found, what moved, did the fix land, why. Falls back to the deterministic prior-run index if the JSON is absent.

**3. Reorder + Slack digested.** Tab order now matches the template: **About this CE → Timeline of changes → Recent past RCAs → Known constraints → Known failure modes → Important links → (raw Slack, collapsed)**. Slack now primarily *feeds* the constraint buckets + timeline; the raw block is kept collapsed as provenance.

### Blast radius
- `scripts/render_ce_context.py` — 7-section reorder; new `build_pastrca_block` (ce_history.json → table, fallback `prior_runs_block`) + `build_constraints_block` (ce_context_constraints.json → bucketed table with status chips) + split About / Known-failure-modes / Important-links blocks (reuse `_split_user_context_slots`, `_uctx_links_block`); new anchors `cecontext-{about,timeline,pastrca,constraints,failuremodes,links,slack}`. Timeline + Slack builders unchanged.
- `skills/ce-context/SKILL.md` — Step B now emits `ce_history.json` (per-RCA contract); **new Step D** synthesises `ce_context_constraints.json`; timeline → Step E, render → Step F; return line + render anchors updated.
- `skills/ce-context/references/ce_history_guide.md` — output contract is now the per-RCA JSON (Sections 4–5 rewritten).
- `SKILL.md` Step 4f Organize (new JSONs → `data/`) + `m050`; `references/{summary_guide,followup_guide,composition_rules}.md` anchor lists + reading order; `VERSION` 2.20.0 → 2.21.0.
- **Verified:** renderer parses/imports/runs; populated fixture → 7 sections in order, all 5 named buckets + an agent-added bucket with colored status chips, per-RCA rows with Moved? chips; graceful (no constraints JSON → honest note; no history JSON → prior-run fallback; empty run → no crash).

---

## [v2.20.0] — 2026-06-15 — Perf-audit: owner's richer DIAGNOSTICS trees + tree-driven decision transcript

**Summary:** Incorporated the perf-audit-skill owner's deeper hypothesis trees (upstream github `aaradhyaraiHO/perf-audit-skill`, 6.1) into our vendored `skills/perf-audit/`, and made the perf-audit decision transcript explicitly driven by those trees — so the "Paid Performance Audit" sub-tab of the composite Transcript tab shows the *investigation reasoning* (hypothesis → check → verdict), not a re-render of the report tables. **The CE-RCA-compat layer and the perf-audit engine are untouched, and `vendor.sh` was intentionally not run** (it would clobber these edits by re-syncing from the standalone skill, which is synced separately).

**1. Richer DIAGNOSTICS trees (additive, `skills/perf-audit/DIAGNOSTICS.md`).** Brought back the trees our fork had trimmed, merged into the existing structure:
- **§4 Step 0** — CPC×scale per-language classification (CPC↑+Scale↓ = competition; CPC flat+Scale↓ = SIS compression; CPC↓+Scale↓ = algorithm retreat OR demand; CPC↓+Scale↑ = efficiency). Forces per-cohort decomposition so a flat *blended* CPC can't mask a mix shift.
- **§4 Step 1a** — the existing 3-lens CPC↑ tree, with Lens 3 (competition) now accepting per-cohort CPC×scale as sufficient evidence on its own.
- **§4 Step 1b** — algorithm-retreat-vs-demand causal chain (TR↓ → RPC↓ → tROAS gap → bids↓ → SIS↓ → clicks↓), distinguished by demand direction.
- **§7b Take-Rate (TR)↓ tree** — SP contract/commission change, product-mix shift, completion-rate decline; tROAS bridge vs structural TR fix.
- **§10 "Other"-cohort collapse** — language-consolidation artifact detection (catch-all "Other" cohort absorbed into dedicated language campaigns).
- **§5 CVR tree** — enriched with LP2S / S2C / C2O sub-stage, device, experience and LY-gap hypothesis branches, **but kept decoupled from CVR-RCA**: perf-audit notes the funnel hypothesis from its own paid-session data and defers the deep decomposition to the CVR-RCA tab. **No hard `/cvr-rca` invocation was re-introduced** — the CE-RCA standalone-funnel design is preserved. The "show reasoning naturally, don't cite §-IDs / this file" rule is kept.

**2. Tree-driven transcript (`skills/perf-audit/SKILL.md`, Steps 3 & 6).** Step 3 now maps each report signal to the DIAGNOSTICS tree it activates and instructs the agent to keep a running **hypothesis → check → verdict** record (confirmed / ruled-out / data-gap / defer-to-CVR-RCA) as it walks the trees. Step 6 now states the `transcript_perf_audit.md` decision transcript must **mirror those walked trees** — each branch as hypothesis→check→verdict. **The Step-6 contract is unchanged**: exact filename, run-dir/`orchestration.json` location, and the tree-map+detail format are byte-identical; only the "mirror the trees" guidance was added.

**Skipped (noted for a later coordinated merge):** upstream's metric auto-validation + `engine/smoke_test.py` (27 checks). Its imports target upstream's `scripts.perf_audit_engine_v6.*` module layout, and check 3 asserts a "PMax GMV correction" that conflicts with our PMax/offline-CM engine consolidation. Porting it cleanly would require reverting that consolidation, so it was left out.

**Preserved:** path/name shim (`perf_audit.py`, `./engine/`, `PERF_AUDIT_VERSION="v6.1"`), Execution Modes, standalone funnel, no-Google-Sheets, and the engine consolidation (PMax removal, NotFound retry, A3 trend, geo Conv Δ, "Paid CVR" labels).

**Blast radius:** `skills/perf-audit/{DIAGNOSTICS.md,SKILL.md}`, `SKILL.md` changelog row (m049), `CHANGELOG.md`, `VERSION`. No engine / compose / template / sub-skill code change.

---

## [v2.19.0] — 2026-06-15 — CE Health: vendor LY-share + TGID MoM/YoY comparison toggle

**Summary:** Two comparison-depth additions to the CE Health tab, both from stakeholder asks — see how a vendor's revenue share moved *year-over-year*, and compare each TGID's current numbers against **both** the prior period *and* the same period last year.

**1. Vendor Breakdown — LY share.** The vendor table showed current-window share with a MoM revenue delta but no year-ago reference, so "is this vendor gaining or losing share over the year?" was unanswerable. `fetch_vendor_breakdown` now also fetches the LY-same-period window (its `_fetch_vendor_window` was already parameterized — one extra window query, no new SQL), and `render_vendors` adds two columns: **LY Share** and **Δ Share** (the YoY share move, in pp). Fully back-compatible: when no LY window is passed the table is exactly as before. A vendor absent last year shows "new".

**2. Top TGIDs — MoM / YoY comparison toggle.** Analysts wanted to compare each TGID's post-period numbers against the pre period **and** against LY-same-period (not one or the other). The TGID sales query already pulled all LY columns, so **no sales-query change** — and the per-experience funnel query (`fetch_tgid_funnel`) gained an optional LY window so the funnel rates (S2C/C2O) and the RPC proxy also get a real YoY delta (one widened Mixpanel query — adds the LY window's aggregations; no extra query count). `render_tgids_enriched` now emits two tables under §6 — a **vs Pre** view (deltas vs prior) and a **vs LY** view (deltas vs last year), identical columns/rows, only the delta tokens differ — and the renderer wraps them in a "Compare current vs:" dropdown reusing the existing funnel panel-switch widget (zero new JS). The toggle appears only when LY data exists; older CEs (<13 months) show the MoM table alone. The TGID×lead-time sub-table (current-window mix) is unchanged and shared below the toggle.

### Blast radius
- `skills/ce-health/engine/sources/bq.py` — `fetch_vendor_breakdown` gains an optional `ly_cur` window (additive; default keeps the old 2-window behavior).
- `skills/ce-health/ce_health.py` — `fetch_tgid_funnel` gains an optional `ly_cur` window (string-built LY SELECT/WHERE blocks; omitted → query unchanged); `render_vendors` adds LY Share + Δ Share columns (gated on LY data); `render_tgids_enriched` emits MoM + YoY tables via a shared row helper (`has_ly`-gated); two call sites pass `ly_cur`.
- `scripts/render_ce_health.py` — the §6 block builds both TGID tables and wraps them in a `build_fdim_dropdown` toggle when the YoY table is present; `build_fdim_dropdown` gains a `label` param (funnel call unchanged). Backward-compatible: an old single-table run renders with no toggle. `build_tgid_main` unchanged.

---

## [v2.18.0] — 2026-06-15 — CE Context: its own `/ce-context` skill + tab (Slack owned once, context timeline)

**Summary:** The context that orients an RCA — the analyst's own notes, the history of prior RCAs on this CE, and live Slack signals — used to be buried inside CE Health's "Historical Context" section. It's now a **first-class "CE Context" tab** (right after Summary), produced by a **new vendored sub-skill `/ce-context`** that can also run standalone. The tab opens with a **context timeline** (dated events from all streams, with the pre/post analysis window shaded) over the deterministic context tables.

**1. One Slack search per run.** CE Context **owns the Slack collector** for the whole run — it fires once, early. The `orchestration.json` handshake gains `slack_owner: "ce-context"`; CVR-RCA sees an owner other than itself and **skips its own Slack spawn**, consuming the shared `slack_context.md` at its Step 2b exactly as before (the same dedup pattern that already stops it double-firing perf-audit). A standalone `/cvr-rca` run still searches Slack itself.

**2. Context timeline chart.** The CE Context sub-agent emits a normalised `ce_context_timeline.json` (lanes: prior RCAs / known events / MMP-doc / Slack — it resolves dates, including relative ones like "last week", using the run window). `scripts/render_ce_context.py` plots a Plotly timeline with the pre/post window shaded. Best-effort: undated context stays in the tables, and an empty timeline simply omits the chart.

**3. CE Health is now a pure data/metrics tab.** Its Historical Context section is removed (`render_ce_health.py`); the three block builders it used (user context, CE history, prior-run index) are retained and **imported** by the new renderer — no duplication. Corroboration is extended: `ce_history.md` joins `context_lenses`, so CVR-RCA cross-references current findings against institutional memory ("LP2S flagged in 2 of 3 prior RCAs" → Pattern A/B).

### Blast radius
- **New:** `skills/ce-context/` (SKILL.md, INSTALL.md, vendored `slack_context_guide.md` + `ce_history_guide.md`); `scripts/render_ce_context.py`.
- **Edited:** `SKILL.md` (drop Step 0e history spawn; dispatch CE Context at Step 2 with `CE_CONTEXT_RUN_DIR`/`RENDER_SCRIPTS_DIR`; `orchestration.json` +`ce-context`/`slack_owner`/`ce_history.md`; Step 3 lens list; Step 4f Organize); `scripts/render_ce_health.py` (remove §Historical, renumber Customer Countries → 10); `scripts/compose.py` (cecontext tab after Summary + `_SUBDIR`); `skills/cvr-rca/SKILL.md` (Slack-owner guard + `ce_history.md` lens — vendored divergence, no `vendor.sh`); `references/{summary_guide,followup_guide,composition_rules}.md` (anchors + reading order); `INSTALL.md`; `VERSION` 2.17.0 → 2.18.0.
- **Verified:** renderer parses/imports/runs (empty → graceful tables-only; populated fixture → 4 blocks + timeline chart + shaded window band); re-rendered CE Health has zero `cehealth-history`; compose tab order = **Summary → CE Context → CE Health → CVR RCA → Paid Perf**.

---

## [v2.17.0] — 2026-06-15 — CE Health: landing-page revenue table + completion-rate red made to actually fire

**Summary:** Two CE Health tab changes from stakeholder feedback.

**1. New "Top Landing Pages" table (§6b), directly below TGIDs.** The TGID table answers "which experiences drive revenue"; analysts wanted the same view by **landing page**. `fct_orders` carries a `landing_page` column, so this is the TGID **sales matrix** at a new grain: a new engine fetch `fetch_top_landing_pages` clones `fetch_top_tgids` (revenue, share, orders, RPC, AOV, CR, TR — top 10 by revenue) grouped by `landing_page`. **Deliberately revenue-only — no funnel columns merged in.** Joining `fct_orders.landing_page` (full URL) to Mixpanel's `page_url` (root, language-collapsed) is not reliable enough to trust per-row, and a per-page funnel view already exists in its own section (§10 Landing Pages, fed into the Funnel block). Keeping the two tables separate avoids a fragile join, an extra fetch dependency, and uncertain output — at the cost of nothing the funnel section doesn't already cover. Rendered by a dedicated `build_landing_main` reusing the TGID formatting internals that apply to a sales table (80%-revenue concentration green, blue group dividers, CR<80 red, full-URL hover) for the single-identity-column layout — `build_tgid_main` is byte-for-byte unchanged. Collapsed by default like TGIDs.

**2. Completion-rate < 80% now actually goes red across all tables — and the S2C/C2O/S2O colour scale actually fires.** A latent bug: the conditional formatting read each cell with `numparse`, which returns `None` for a combined "value + delta" cell (e.g. `88.1% -1.8pp` → can't float `"88.1 -1.8pp"`). Since TGID rate cells *all* carry trailing deltas, the CR<80 red **and** the S2C/C2O/S2O colour scale had been **silently dormant** in the TGID table (and would have been in the new landing-page table). A new `_lead_num` helper peels off the leading value before parsing; applied to every threshold/colour-scale read in both builders. The Step-1-vitals 4-window table also now reds completion cells < 80 — matching on the **"CR"** row label (the table labels it "CR", not "Completion") and on the clean value columns (delta columns parse to None and are skipped). The Completion metric **card** turns its value red when < 80. Verified on a real run: TGID colour-scale cells went 0 → 30; a synthetic CR=75% row produces the red class.

### Blast radius
- `skills/ce-health/ce_health.py` — new `fetch_top_landing_pages` (sales query) + `render_top_landing_pages` (revenue-only renderer); 3 wiring lines (submit / result / sections list, the new section emitted right after TGIDs). No Mixpanel join, no new funnel query. Existing TGID + §10 funnel paths untouched.
- `scripts/render_ce_health.py` — new `_lead_num` + `build_landing_main` + `_landing_groups` (sales-only: concentration green, CR<80 red, group dividers, URL hover — no funnel/colour-scale logic); the `cehealth-landing-pages` block inserted after `cehealth-tgids` with subsequent block titles renumbered (7–11); CR-red on the Completion card + vitals "CR" row; `numparse → _lead_num` at every conditional-format read in `build_tgid_main`. `build_tgid_main` output unchanged except its previously-dormant CR-red / colour-scale now render.

---

## [v2.16.0] — 2026-06-15 — Step-1 diagnosis: Users (traffic) added to the Vitals table

**Summary:** Stakeholders flagged a gap in the Step-1 in-chat diagnosis (the vitals + Shapley preview shown at the pause-for-input): the Shapley driver ranking lists **Traffic** as a driver, but the Vitals table above it never showed traffic — so a reader couldn't see the user-count move that the #1 driver decomposes. The Vitals table now leads with a **Users** row (LP traffic), in funnel order: **Users → Revenue → Orders → CVR → AOV → Completion → Take Rate**. Users is the same `lp_viewers` level the Shapley `traffic` factor decomposes, so the vitals now tie directly to the driver ranking. Formatted as a plain integer count with a **% change** delta (a count metric, like Revenue/Orders — not pp).

To feed it, the CE Health engine now merges **`users` (= funnel `lp_viewers`)** onto each window's sidecar vitals, exactly mirroring the existing `cvr` merge — so `vitals.{current,prior,ly_*}.users` is available to the preview (and any downstream reader) with no new query. Verified on CE 243: sidecar emits `vitals.current.users=119,164`, `vitals.prior.users=123,687`, consistent with the negative Shapley traffic contribution.

### Blast radius
- `skills/ce-health/ce_health.py` — one merge line in `run_ce_health` (adds `vitals[*].users` alongside the existing `vitals[*].cvr` merge). Additive; no other vitals/render/Shapley logic touched.
- `SKILL.md` Step 1 — Vitals table gains the Users row + sidecar-read note (`vitals.*.users`) + delta-unit rule (Users = % change, integer count). No change to the Shapley table or the dispatch flow.

---

## [v2.15.1] — 2026-06-15 — Summary tab: driver decomposition moved up, "what we set out to check" moved last

**Summary:** Reordered two Summary-tab blocks so the front page reads in the order a stakeholder actually wants: the **Driver table (revenue decomposition + per-driver verdict)** now sits **straight after the headline callout** — so right below the TL;DR story you immediately see what moved revenue and what the RCA found for each driver, before the deeper per-tab digests. The **"What we set out to check"** table (the analyst's input vs the RCA's verdict) moves to the **last table before the cross-reference** — it closes the loop on intent right before the provenance table. New flow: Vitals → Short/long-term → Callout → **Driver table** → Per-tab digests → Next steps → **What we set out to check** → Cross-reference. Pure reordering — no block's content or semantics changed (the user-context block is still conditional on `user_context.md`).

### Blast radius
- `references/summary_guide.md` only — the reading-flow table + section headers/order. No script / `compose.py` / template change.

---

## [v2.15.0] — 2026-06-15 — Drive sync → user-run command (rollback to lean)

**Summary:** Automatic Drive sync couldn't be made to work for downloaded users. An agent reading local files and uploading them to a cloud folder is the data-exfiltration shape the auto-mode safety classifier blocks — and it fired regardless of mechanism (both the upload sub-agent and the first-party `drive_sync.py` Bash call were blocked in a real run). The only paths to fully hands-off sync were per-user permission rules (friction, and weakens each user's classifier for a sync that mainly benefits the maintainer) or having the installer write those rules — both too much complication for a downloaded skill. **The fix is simpler: don't have the agent upload — print the command and let the user run it.** A command the *user* chooses to run never touches the classifier, and Claude Code renders a one-click run button on the command block.

### What changed
- **Step 4g is now a printed, optional, user-run command** — after Organize (4f) the skill prints `python3 "$SKILL_DIR/scripts/drive_sync.py" --run-dir "<run_dir>"` with one framing line; **the orchestrator no longer runs it.** Removed the "non-optional / do not skip" framing, the verification gate, the exit-code-handling branches, and the exfiltration-shape explanation (moot once it's user-run).
- **Step 5 feedback decoupled from Drive** — `feedback.md` is still written locally (and rides along in the run folder if the user runs the 4g archive command) but is no longer auto-uploaded; the single-file `--file … --into-folder-id` upload and `DRIVE_RUN_ID` plumbing are gone from the flow.
- **`scripts/drive_sync.py` unchanged** — it's the target of the printed command (full-run mode; single-file mode left intact but unused).
- **`INSTALL.md`** Drive section trimmed to a lean "optional, user-run archive" note — scope setup, central-folder constant, and owner-share step kept; auto-sync prose dropped.

### Blast radius
- `SKILL.md` (Steps 4e / 4g / 5 + changelog row m047), `INSTALL.md`, `VERSION`. No script / `compose.py` / template / sub-skill change.

---

## [v2.14.1] — 2026-06-12 — Auto-open report + clearer two-link completion UX

**Summary:** When a CE-RCA run completes, the analyst previously had to navigate to the run folder and double-click `report.html` — not obvious, especially for new users. Step 4e now immediately **opens the report in the browser** (`open "<run_dir>/report.html"` on macOS) and emits a clickable `file://` URL in the chat — the analyst's live working copy (follow-ups keep updating it in place; just refresh the tab). The Step 4g Drive message is reworded as a **share link for stakeholders** (`📁 Share with team: <folder_url> — paste in Slack / Linear`) so the two outputs have distinct, immediately-clear roles: local file = live copy, Drive = as-delivered snapshot for the team.

### Blast radius
- `SKILL.md` Steps 4e + 4g only (message/action wording). No script, schema, or report structure change.

---

## [v2.14.0] — 2026-06-12 — VERSION sync (Drive sync already live)

*(internal — Drive sync plan was implemented in v2.12.0; VERSION bumped to align)*

---

## [v2.13.0] — 2026-06-12 — Arbitrary pre/post windows: CE Health no longer forces a preceding-equal baseline

**Summary:** A run that asked for post = May vs pre = March (skipping April as a transition month) hit a wall — CE Health only accepts one window (`--start/--end`) and *auto-derives* the baseline as the immediately-preceding equal-length block, so March was unreachable. This was an inconsistency, not a policy: **CVR-RCA already accepts four independent dates** (`pre_start pre_end post_start post_end`), so the team's standard is "let the user pick both windows." CE Health just never grew the flag. We brought it up to parity with a **minimal, additive** change (not the full 4-date rewrite, which would have ripped out CE Health's range-alias + label + LY-derivation system): a new optional `--pre-start/--pre-end` override. When supplied, the baseline is exactly what the user named — any window, contiguous or not, equal-length or not; LY-prior shifts 364 days off the explicit baseline, and the delta label becomes the neutral "vs Pre" (period-over-period glyphs like MoM/QoQ would mislead on a gapped comparison). **When omitted, behavior is unchanged** — preceding-equal auto-derive, MoM/QoQ labels, every existing call still works. The orchestrator now passes the same confirmed pre/post dates to both CE Health (`--pre-start/--pre-end`) and CVR-RCA (its four-date args), so every tab compares identical windows. Step 0b no longer snaps a user's pre window to the preceding block.

### Blast radius
- `skills/ce-health/ce_health.py` — `compute_windows` + `run_ce_health` gain optional `pre_start/pre_end`; argparse gains `--pre-start/--pre-end` with paired/custom-range-only validation. Default path untouched.
- `skills/ce-health/SKILL.md`, `ce_health.py` docstring — document the new flags.
- `SKILL.md` Steps 0b + 0d — confirm-and-honor arbitrary pre windows; map them to the new flags and to CVR-RCA's four-date args.

---

## [v2.12.2] — 2026-06-11 — Step 0a: exact CE-name resolution query (no more dataset guessing)

**Summary:** A real run wasted ~8 BigQuery round-trips resolving a CE name — the agent guessed wrong dataset paths and assumed the ID was an integer — because Step 0a only said "resolve via `dim_combined_entities`" without a path or type. Step 0a now gives the **exact** query (`` `headout-analytics.analytics_reporting.dim_combined_entities` ``, location EU; **`combined_entity_id` is a STRING — quote it**; by-id or `LIKE` by-name) so it resolves in one shot, plus a guard: the name is optional enrichment (CE Health's sidecar carries it), so if the one query doesn't resolve, skip to the window confirm — don't list datasets or retry. Deterministic for every user (no reliance on an agent's local memory).

### Blast radius
- `SKILL.md` Step 0a only. No other change.

---

## [v2.12.1] — 2026-06-11 — Hardening pass (audit follow-up; no normal-run behavior change)

**Summary:** A leanness/rigidity audit confirmed all recent features are present and the skill is still lean. This patch applies only the genuine hardening it surfaced (cosmetic trims deliberately skipped to avoid churn):
- **render_ce_health.py:** guard the one un-hardened crash path — if CE Health's §2 "CE Vitals" md table is ever missing, render cards-only (cards come from the JSON sidecar) and keep rendering the rest of the tab, instead of an IndexError.
- **SKILL.md:** scope the `CVR_RCA_RUN_DIR` dispatch wording to "only when spawning CVR-RCA"; add a Step 1b guard so a missing `context_ingest_guide.md` or unreadable source is logged and skipped, not fatal.
- **summary_guide.md:** surface the Slack-honesty rule in the top cardinal-rule list (was mid-file).

### Blast radius
- `scripts/render_ce_health.py`, `SKILL.md`, `references/summary_guide.md`. No compose/template/sub-skill change. Verified a normal ce-243 render is unchanged (vitals block + 4-window table + cards intact).

---

## [v2.12.0] — 2026-06-11 — Central Drive sync of every run + structured feedback capture

**Summary:** Every `/ce-rca` run now also lands in a **shared central Google Drive folder**, so runs across all users accumulate in one place to review and improve the skill. The Step-5 playground prompt gains a **structured feedback ask**, and that feedback rides up to Drive alongside the run. The design is **additive-only** — the Drive MCP is create-only (no update, no delete), so nothing in Drive is ever overwritten.

### What changed (orchestrator only)
- **New Step 4g — Sync the run to Drive** (after the 4f Organize, before the Step-5 prompt). A small **upload sub-agent** (keeps the multi-MB base64 out of the orchestrator's context) is given just `<run_dir>` + the central folder id (`CENTRAL_DRIVE_FOLDER_ID = 1nernSzAN2mZ531wEdh95eeNL2RV5oq30`). It:
  - **Guards** on the Drive MCP `create_file` tool — absent → returns `DRIVE_UNAVAILABLE`; the orchestrator logs "Drive sync unavailable — skipped" and continues. Drive sync never blocks a run (mirrors the Slack graceful-skip rule).
  - Creates a per-run subfolder `<run-dir basename>-<6-hex hash>` (random suffix dedups concurrent identical runs; no PII) → `DRIVE_RUN_ID`.
  - Zips the run dir (parent-relative) with an **~8 MB size guard** that re-zips excluding `data/stage*.json` (and notes it).
  - Uploads **`report.html`** (browsable — `disableConversionToGoogleType:true`, `text/html`) + the **zip** (`application/zip`) into the per-run folder.
  - Returns `DRIVE_RUN_ID` + the folder link; the orchestrator records both in `logs/_run_log.md` and tells the user where the run synced.
- **Step 5 — feedback ask + additive upload.** The playground prompt now asks: *numbers incorrect · narrative unclear · narrative incorrect · couldn't follow the report at all · other* + a line of detail. On feedback, the skill writes its **one new file** — `<run_dir>/feedback.md` (category/categories + detail + timestamp + CE/window) — and, if `DRIVE_RUN_ID` is known, uploads it as a **new** file into the same per-run folder (text, no base64). If Drive was unavailable, `feedback.md` is still written locally.
- **Follow-ups stay file-minimal and never auto-re-upload.** A promoted follow-up reuses the existing `tabs/followups.html` + the re-composed `report.html` (no per-follow-up files). The Drive copy is the as-delivered snapshot; only an explicit user request to re-sync re-runs Step 4g (a new versioned subfolder/zip — additive).

### Blast radius
- `ce-rca` master only: `SKILL.md` (Step 4g + Step 5 + changelog row m042), `INSTALL.md` (Drive-sync prerequisite doc), this `CHANGELOG.md`, `VERSION` 2.11.5 → 2.12.0. **No script / `compose.py` / template / sub-skill change** — the orchestrator drives the Drive MCP + a Bash zip directly.

---

## [v2.11.5] — 2026-06-11 — CVR-RCA writes into the orchestrator's run dir (single-folder fix)

**Summary:** Root-caused the intermittent "two folders per run" issue (stray `stage*.json` in one folder, the report in another). CVR-RCA's `run_analysis.sh` always self-named its output folder (and auto-incremented `_run2`), so under CE-RCA the query artifacts and the report landed in different places — and the Organize step only tidied the orchestrator's run dir, leaving the stray folder. Now, run under CE-RCA, CVR-RCA writes **everything into the one run dir**.

### What changed (vendored CVR-RCA copy only)
- `skills/cvr-rca/scripts/run_analysis.sh` honors a new `CVR_RCA_RUN_DIR` env var → writes `summary.json` + `stage*.json` directly into that exact dir (no `ce<id>_<dates>` subfolder, no auto-increment). `skills/cvr-rca/SKILL.md` Step 1 documents orchestrated vs standalone invocation.
- **Standalone CVR-RCA is unchanged** (env unset → self-names as before). The standalone *source* was intentionally not touched (the two now diverge on these 2 files); `vendor.sh` deliberately not run.

### Blast radius
- Vendored `skills/cvr-rca/` only. No `compose.py` / template / engine change. Vendored CVR-RCA bumped 1.30.0 → 1.30.1.

---

## [v2.11.4] — 2026-06-11 — Report-honesty fixes (Summary chrome · Slack integrity · CVR-chart basis + partial month · vitals pill)

**Summary:** Fixes five issues a colleague's run surfaced — all **presentation-layer, no engine/query/SQL change**. The Summary no longer duplicates the composite's CE header or a "Links" row; an absent Slack context is reported honestly instead of fabricated; the monthly CVR chart no longer mislabels Paid CVR as the vitals' Site CVR and no longer plots an incomplete trailing month; and the vitals delta pills now read unambiguously as an arrow + absolute + relative change.

### What changed
- **Summary chrome standardized (`references/summary_guide.md`).** The Summary fragment is **forbidden** from authoring any CE-identity header (`<header>` / `id="top"` / eyebrow / `<h1>` CE name / meta line) or a "Links"/dashboards row — the composite's top banner already shows CE identity + dashboards, and user-provided links live in **one place: CE Health §8 "Important links"**. The fragment starts deterministically at `<div class="section-label">CE-Level Summary</div>` + vitals. (Kills the phantom "extra subtab" that varied with the user's links.)
- **Slack honesty rule + dependency note (`skills/cvr-rca/references/slack_context_guide.md` vendored-only · `summary_guide.md` · `INSTALL.md`).** When `slack_context.md` is **absent**, the report states "**Slack context unavailable**" consistently and must **not** claim threads were searched, add a Slack data-source row, or cite any Slack signal/flag/chip. `INSTALL.md` documents that Slack signals require the **Slack MCP connected**; absent → gracefully skipped + reported unavailable.
- **CVR-chart basis honesty + partial month (`scripts/render_ce_health.py`).** The monthly CVR YoY chart **prefers a monthly Site-CVR column** (`site_cvr`/`site cvr`) so it matches the §2 vitals; **absent → keeps the Paid-CVR series but titles the chart "Paid CVR (monthly)"** (never conflates Site vs Paid). The **partial trailing month** (its `YYYY-MM` == `generated_at`'s month; the query ends `CURRENT_DATE()-1`) is **dropped** from both monthly tables so the truncation dip can't read as a real drop.
- **Vitals pill redesign (`render_ce_health.py` §2 + `summary_guide.md` §2).** The §2 vitals cards (CE Health + the Summary mirror) replace `Δ <x>` with an **arrow + absolute + relative** pill colored by direction: money/count e.g. `↑ +$81.9K · +28%`, rate e.g. `↓ −0.63pp · −31%`. **`Δ` stays in table column headers and the §4 funnel cards** — only the vitals cards change; all 6/7 vitals keep their order + labels.

### Engine handoff (pending, separate)
Monthly Site CVR — wiring `ce_health.py:fetch_monthly_cvr()` into the L12M `.md`/`.json` as a `site_cvr` column — is a separate Wave-B engine task. The renderer auto-prefers that column once it lands; until then it honestly shows "Paid CVR (monthly)".

### Files
`references/summary_guide.md`; `scripts/render_ce_health.py`; `skills/cvr-rca/references/slack_context_guide.md` (vendored copy only — no `vendor.sh` re-run; cvr-rca source untouched); `INSTALL.md`; `VERSION`; `SKILL.md` (m040). No `compose.py` / template / engine / query-SQL change.

---

## [v2.11.3] — 2026-06-10 — Cross-tab metric naming consistency (Site CVR / Paid CVR · LP Users / Paid sessions)

**Summary:** Eliminates cross-tab label collisions — the same word ("CVR", "Traffic") was showing different numbers across tabs because the underlying measure differs by basis (Mixpanel funnel vs paid-platform). Now there's **one canonical name per metric concept**, so a reader never mistakes a legitimately-different number for a data error. **Labeling only — no metric/SQL changes; report numbers are byte-identical.**

### What changed
- **CVR split → "Site CVR" (Mixpanel funnel, completed/LP) vs "Paid CVR" (Google-Ads clicks→conversions).** Renamed across CVR-RCA hero cards (`report_structure.md`), CE Health §4/§5/§7/§10 (`ce_health.py`) — **killing the §5 same-section funnel-vs-paid "CVR" collision** — perf-audit Table-2/cohort/AG-type/monthly headers + `metric-definitions.md`, and the Summary vitals card + driver table (`summary_guide.md`).
- **Traffic split → "LP Users" (Mixpanel funnel volume) vs "Paid sessions" (Google-Ads).** perf-audit "LP Sessions" → "Paid sessions".
- **Funnel-step basis tags** — within-session (CVR-RCA + CE Health, matches Omni) vs paid-session (perf-audit on-site funnel; basis note added).
- **New `references/metric_glossary.md`** — single source-of-truth for canonical names. **Maintainer reference, NOT loaded at runtime** (deterministic code + ~6 inline guide lines enforce the names).
- **`scripts/vendor.sh` DISARMED** (`VENDOR_FORCE=1` to override) — `ce-rca/skills/` is now the canonical edit location; a re-vendor would overwrite local edits not present upstream.

### Files
`skills/cvr-rca/references/report_structure.md`; `skills/ce-health/ce_health.py`; `skills/perf-audit/engine/render/audit_skeleton.py` + `references/metric-definitions.md`; `references/summary_guide.md` + `references/composition_rules.md`; new `references/metric_glossary.md`; `scripts/vendor.sh`. Blast radius: render/label layers + orchestrator docs. No `compose.py` / template / query-SQL change.

---

## [v2.11.2] — 2026-06-10 — CE Health funnel → within-session (matches Omni) · transient-404 resilience · deterministic PMax pill

**Summary:** Closes the last funnel mismatch and hardens the engine against a transient BigQuery failure. The CE Health funnel now matches the Omni dashboard and the CVR-RCA tab exactly; a clone-refresh 404 no longer crashes a run; and the "EXCLUDES PMAX" basis pill now renders deterministically on the CE Health funnel.

### What changed
- **CE Health funnel → within-session basis** (`skills/ce-health/ce_health.py`): `fetch_ce_funnel` (§ funnel) and `fetch_tgid_funnel` (§6) now query the within-session `mixpanel_user_page_funnel_progression` on `event_date` (was the cross-session `mixpanel_user_funnel_progression` on `session_date`). The CE Health funnel now reads the same numbers as the CVR-RCA tab + Omni — verified on CE 3593 (Mar12–Jun09): **89,268 → 82,520 LP** (matches Omni 82,507; LP2S 44.5 / S2C 33.4 / C2O 41.3). No page-type whitelist; PMax excluded. The funnel-CVR feeds the Shapley, so the §7 Shapley basis is now consistent too.
- **Deterministic "EXCLUDES PMAX" pill** (`scripts/render_ce_health.py`): the §5 Funnel header now renders the pill in code (a prior markdown note was dropped by the renderer). Also removed a stale `page_type` whitelist from `_FUNNEL_SQL` (the Shapley traffic input) so it matches the §4 funnel cards.
- **Transient NotFound (clone-refresh 404) resilience**: `run_bq_query` in `skills/ce-health/engine/sources/bq.py` and `skills/perf-audit/engine/sources/bq.py` now retry `NotFound` (4×, 10/20/30s backoff) then re-raise — the `analytics_reporting` tables are zero-copy CLONE tables that briefly 404 mid-refresh, and the BQ client does not retry NotFound by default. `skills/cvr-rca/scripts/run_analysis.sh` gains a `bq_q` CLI wrapper that retries the four query stages on "Not found".

### Blast radius
- `ce-health` engine (`ce_health.py`, `engine/sources/bq.py`) + `scripts/render_ce_health.py` + `perf-audit/engine/sources/bq.py` + `cvr-rca/scripts/run_analysis.sh`. No `compose.py` / template change. VERSION 2.11.1 → 2.11.2.

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
