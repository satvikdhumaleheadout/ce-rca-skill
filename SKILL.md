---
name: ce-rca
description: >
  CE-level Root Cause Analysis for a Headout Combined Entity (CE) — the umbrella
  skill. Use this whenever someone wants a full picture of what's happening with
  a CE, asks "what's going on with CE X", "run a CE RCA", "diagnose this CE", or
  wants health + funnel + paid in one report. It runs CE Health first, shows the
  diagnosis, asks which directions to deep-dive, then fires the matching skills
  (CVR-RCA, perf-audit, and future AOV / completion-rate skills) and assembles
  one tabbed report. Run /ce-rca <CE> to start. For a CVR-only funnel RCA use
  /cvr-rca directly; this skill is the multi-skill umbrella on top of it.
---

# CE Root Cause Analysis — Master Orchestrator

This skill is a **thin orchestrator**. It owns no investigation logic of its own.
It runs CE Health, asks the user which directions to pursue, dispatches the
matching deep-dive skills, and composes their outputs into one tabbed report.

**The cardinal rule: this skill is a composer, not an editor.** Every sub-skill
(CE Health, CVR-RCA, perf-audit, future skills) runs exactly as it does
standalone, and its output appears in the composite report **verbatim** — no
summarizing, no restructuring, no re-wording. The sub-skills are never modified.

## Before you begin

Derive the skill directory from the path of this SKILL.md:

```bash
SKILL_DIR=~/.ce-rca   # or wherever this file was read from
```

Read references lazily, by phase:

| Phase | Read |
|---|---|
| Step 2 (dispatch) | `references/registry.md` |
| Step 3 (synthesise) | the Summary sub-agent reads `references/summary_guide.md` — you just point it there |
| Step 4 (compose) | `references/composition_rules.md` (and `references/visual_kit.md` is consumed by `compose.py`, not by you) |

You do **not** need to read the sub-skills' SKILL.md files yourself — each
sub-agent reads its own. You only orchestrate.

## Invocation

```
/ce-rca <CE> [date-range]
```

`<CE>` is a CE ID or CE name. `[date-range]` is optional; default is **last 30
days vs prior 30 days** (matching CVR-RCA's default). Examples:

```
/ce-rca 252
/ce-rca "Louvre Museum"
/ce-rca 252 last complete week vs the week before it
```

---

## Step 0 — Resolve CE, create run dir, fire CE Health

**0a. Resolve the CE.** If the user passed a CE name, resolve it to a CE ID via
`dim_combined_entities` (same lookup CVR-RCA uses). If they passed an ID, use it.
Resolve the pre/post date windows from the invocation (default 30/30).

**0b. Create the run directory:**

```
~/Documents/CE RCA Runs/<ce-slug>-<post_start>-to-<post_end>/
```

Refer to this as `<run_dir>`. Write a preliminary `<run_dir>/meta.json` with
what you know so far:

```json
{
  "ce_id": 252,
  "pre_period": "<pre_start> to <pre_end>",
  "post_period": "<post_start> to <post_end>",
  "post_start": "<post_start>",
  "post_end": "<post_end>",
  "generated_date": "<today>"
}
```

Open `<run_dir>/transcript.md` and log the run start.

**0c. Fire CE Health (foreground — we need it before we can ask the user).**
Resolve the CE Health skill path (`$CE_HEALTH_SKILL_PATH` → `~/.ce-health-skill/`
→ `$SKILL_DIR/../ce-health-skill-main/`). Spawn a sub-agent that runs:

```bash
cd <ce-health-install-dir>
python3 ce_health.py --ce-id <id> --range month --output <run_dir>/ce_health_report.md
```

(Use `--range month` for the 30/30 default, or `--start/--end` for a custom
window.) CE Health writes `ce_health_report.md` + a `.json` sidecar. Wait for it.

If CE Health can't be resolved or fails, tell the user plainly and stop — CE
Health is the entry point of this skill; without it there's nothing to orient on.

**0d. Enrich `meta.json`.** Read CE Health's JSON sidecar and fill in
`combined_entity_name`, `combined_entity_type`, `market`, `country`, and
`top_page_url` if present. Add the `dashboards` array (Omni + Sentra URL
templates with the CE ID substituted — same templates CVR-RCA's
`report_structure.md → "Dashboards row"` documents).

---

## Step 1 — Present the CE Health diagnosis and pause

Read `ce_health_report.md` (and its JSON sidecar). Synthesise a short preview
**in chat** (not a file) — 5–8 lines: CE name, window, top-line vitals deltas,
and the Shapley driver ranking. Then state the default deep-dive and ask the
user to confirm or pivot. Shape:

```
CE Health — <CE name> (CE <id>) · <pre> vs <post>

Top-line: Revenue <Δ>, CVR <Δ>, AOV <Δ>, Completion <Δ>, Take Rate <Δ>.
Shapley driver ranking: 1) <driver> (<x>%), 2) <driver> (<x>%), ...

Default deep-dive based on this diagnosis: <skills, e.g. "CVR-RCA + perf-audit">.

Reply "continue" to proceed with the default, or describe a different direction
(e.g. "focus on supply", "skip perf-audit", "CVR only").
```

**Then stop and wait for the user's reply.** Do not dispatch until they respond.
Parse their reply in natural language — there's no rigid command set. "continue"
/ empty / "yes" → the default set. Anything else → interpret their intent against
the registry and resolve a final dispatch set. If they name a driver with no
registered sub-skill (e.g. AOV today), say so and proceed with what's available.

**Future hook — user context paste.** A later version will let the user paste
files / notes / hypotheses here, landing as `<run_dir>/user_context.md` for the
sub-skills to read. Not implemented yet; if the user offers context now, accept
it into `user_context.md` and mention sub-skills don't consume it automatically
yet.

---

## Step 2 — Dispatch the matched sub-skills

Read `references/registry.md`. Map the confirmed drivers to sub-skills, apply the
**CVR ⇒ also-fire-perf-audit** pairing rule, and resolve each sub-skill's install
path. Skip (with a logged note) any that don't resolve.

**Write the orchestration handshake first** — before spawning anything — to
`<run_dir>/orchestration.json`:

```json
{
  "orchestrator": "ce-rca",
  "version": "<this skill's VERSION>",
  "fired_by_master": ["perf-audit-skill", "cvr-rca"],
  "context_lenses": ["ce_health_report.md", "perf_audit_report.md", "slack_context.md"],
  "run_dir": "<absolute run_dir path>"
}
```

`fired_by_master` lists every sub-skill you're about to fire. This is the
contract that stops CVR-RCA from double-firing perf-audit: CVR-RCA checks this
file and, seeing `perf-audit-skill` listed, skips its own perf-audit spawn and
consumes the master's output instead.

`context_lenses` is the **cross-skill manifest** — the list of lens artifacts the
deep dives should reconcile against at their synthesis step. Always include
`ce_health_report.md` (CE Health ran in Step 0, so it's available to every deep
dive). Include `perf_audit_report.md` when perf-audit is firing, and
`slack_context.md` (CVR-RCA's own Slack sub-agent writes it). This is what makes
the tabs talk: CVR-RCA reads this manifest at its Step 2b and folds CE Health's
CE-level facts into its funnel findings (e.g. corroborating a TGID's S2C drop
against CE Health's RPC drop for that same TGID). See `cvr-rca/SKILL.md → Step 2b
→ "Context reconciliation"`.

**Spawn the sub-skills in parallel** (one sub-agent each, single message,
multiple Agent calls). Each sub-agent prompt says: read your skill's SKILL.md at
`<resolved path>` and run it exactly as written, using `<run_dir>` as the run
directory (do not create your own), for CE `<id>`, pre `<pre>`, post `<post>`.
Pass nothing else — the sub-skills own their own logic.

Wait for **all** sub-agents to finish before synthesising.

Log each spawn in `transcript.md`. If a sub-skill fails, note it and continue —
the composite simply won't carry that tab.

---

## Step 3 — Synthesise (the Summary tab)

Once every deep dive has finished, fire a **Summary synthesis sub-agent** that
reads all the tab outputs and writes the front-page cross-cutting synthesis. This
is the surface where the tabs truly talk to each other — it traces the headline
revenue driver across CE Health, CVR-RCA, and perf-audit, and builds the
cross-reference table that links every finding to its corroboration.

Spawn one sub-agent with this prompt: read `$SKILL_DIR/references/summary_guide.md`
and follow it exactly. Run dir: `<run_dir>`. Available lens artifacts:
`<the context_lenses list + cvr_rca findings.md/report.html>`. It writes
`<run_dir>/summary_report.html` (a polished HTML body fragment using visual-kit
chrome — vitals cards + root-cause callout + cross-reference table + per-driver
blocks). It is **pure synthesis** — it weaves existing findings and never runs
queries or computes new numbers.

Wait for `summary_report.html`. **Graceful degradation:** if the Summary agent
fails or doesn't produce the file, log it in `transcript.md` and proceed to
compose — the composite simply won't carry a Summary tab (the deep-dive tabs are
unaffected).

---

## Step 4 — Compose the report

Read `references/composition_rules.md` for the full spec. The mechanics:

**4a. Rename CVR-RCA's report** (if cvr-rca ran) so `compose.py` can read it
without a same-path read/write against the composite output:

```bash
mv "<run_dir>/report.html" "<run_dir>/cvr_rca_report.html"
```

(Only if cvr-rca ran and wrote `report.html`. perf-audit, CE Health, and the
Summary write artifacts that need no rename.)

**4b. Run the composer:**

```bash
python3 "$SKILL_DIR/scripts/compose.py" --run-dir "<run_dir>"
```

This reads the present artifacts (`summary_report.html`, `ce_health_report.md`,
`cvr_rca_report.html`, `perf_audit_report.md`), builds one tab each in fixed
reading order (**Summary → CE Health → CVR RCA → Paid Performance Audit**),
embeds the Summary verbatim, converts the markdown tabs verbatim, extracts
CVR-RCA's CVR content + charts, injects the shared visual_kit styling, and writes
the composite to `<run_dir>/report.html`.

**4c. Report the result.** Tell the user where the composite landed and which
tabs it contains. Keep it short — the report is the deliverable, not a chat recap.

---

## What this skill does NOT do

- **Investigate.** All investigation lives in the sub-skills. The master never
  forms hypotheses or runs diagnostic queries.
- **Edit sub-skill output.** Verbatim, always. The Summary tab synthesises
  *across* tabs but never paraphrases or restyles any tab's own content.
- **Modify the sub-skills.** CE Health, CVR-RCA, and perf-audit run as-is. The
  cross-skill wiring is: CVR-RCA reads `orchestration.json` (to avoid
  double-firing perf-audit, and to pick up the `context_lenses` manifest so it
  reconciles CE Health at its Step 2b). perf-audit and CE Health are untouched.

## Cross-skill data flow (how the tabs talk)

```
CE Health (Step 0, upstream)  ──┐  facts available to all deep dives
                                ▼
CVR-RCA reads the context_lenses manifest at its Step 2b and reconciles its
funnel findings against CE Health + perf-audit + Slack (four-pattern model) →
its tab cites CE Health (e.g. a TGID's RPC drop) inline.

Summary (Step 3, downstream)  ◄── reads ALL finished tabs → cross-reference table
+ headline root cause spanning every tab. The peer↔peer weave lives here.
```

- **Upstream → deep dives:** one-directional, clean (CE Health finished first).
- **Deep dive ↔ deep dive:** CVR reads perf (it fires it); the full peer weave is
  the Summary's job (avoids circular dependency).
- **Everything → Summary:** the front-page synthesis.

## Future hooks (designed-in, deferred)

1. **Summary → arbiter.** Today the Summary is **pure synthesis** — it weaves
   existing findings and never re-queries. The deferred upgrade lets it fire one
   tie-break query when two tabs genuinely contradict. Noted in `summary_guide.md`.
2. **perf-audit cross-skill enrichment (owner hand-off).** perf-audit should also
   read CE Health (and CVR-RCA findings) at its own synthesis and cite them in its
   tab — mirroring CVR-RCA's manifest context layer. perf-audit is owned by
   another team, so this is a hand-off, not our change. See `references/registry.md`.
3. **User context paste** — `<run_dir>/user_context.md` slot exists; wiring it
   into the `context_lenses` manifest (so deep dives + Summary read user-supplied
   context) is deferred.
4. **More drivers** — AOV-RCA, Completion-RCA, Take-Rate-RCA plug into
   `registry.md` and `compose.py`'s `TAB_SPECS` as one-row / one-entry additions.

## Changelog

| # | Date | Changes |
|---|------|---------|
| m001 | 2026-06-03 | Initial version. Top-down master orchestrator for CE-level RCAs. Step 0 runs CE Health (foreground); Step 1 presents the diagnosis and pauses for free-form user confirmation; Step 2 dispatches matched deep-dive skills (CVR-RCA + perf-audit today) in parallel after writing the `orchestration.json` handshake; Step 3 composes a tabbed report via `scripts/compose.py`. Sub-skill outputs appear verbatim (composer, not editor). Registry-driven dispatch (`references/registry.md`) makes new sub-skills one-row additions. Visual kit vendored from cvr-rca; composite styling extracted from it at build time so the umbrella report is visually identical to a standalone CVR-RCA report. Future hooks (user context paste, cross-skill references, summary skill) designed-in but deferred. |
| m002 | 2026-06-03 | **Cross-skill RCA: Summary synthesis tab + context manifest.** Two additions make the tabs talk to each other. **(1) Context manifest:** `orchestration.json` gains a `context_lenses` array listing the lens artifacts deep dives should reconcile against (CE Health + perf-audit + Slack). CVR-RCA reads this at its Step 2b (v1.25) and folds CE Health's CE-level facts into its funnel findings — e.g. corroborating a TGID's S2C drop against CE Health's RPC drop for that same TGID. **(2) Summary tab:** new Step 3 (Synthesise) fires a pure-synthesis sub-agent (`references/summary_guide.md`) that reads every finished tab and writes `summary_report.html` — a polished HTML fragment (vitals cards + root-cause callout + cross-reference table + per-driver blocks) that traces the headline revenue driver across all tabs with `↗` cross-tab links. Compose renumbered to Step 4; `compose.py` adds the Summary as the first tab via a new `html-fragment` type (embedded verbatim). Tab order: Summary → CE Health → CVR RCA → Paid Performance Audit. Summary is the peer↔peer weave surface (avoids circular cross-referencing in individual deep-dive tabs). Graceful degradation: if the Summary agent fails, the composite still builds without that tab. Pure-synthesis for now — an arbiter upgrade (tie-break query on contradiction) is a documented TODO. perf-audit cross-skill enrichment is a hand-off TODO for its owner. |
