# CE-RCA — CE-level Root Cause Analysis (master skill)

CE-RCA is the **umbrella** RCA skill for a Headout Combined Entity. It gives a
C-level reader one tabbed report covering the whole CE picture, by orchestrating
purpose-built sub-skills rather than reinventing their analysis.

## What it does

```
/ce-rca <CE ID or name> [date-range]
```

1. **Runs CE Health** — a wide health briefing (Revenue / Traffic / CVR / AOV /
   Completion / Take Rate, with Shapley driver attribution).
2. **Shows you the diagnosis** in chat and asks which directions to deep-dive —
   continue with the default, or pivot.
3. **Dispatches the matching deep-dive skills** in parallel (today: CVR-RCA for
   the funnel, perf-audit for paid; more drivers plug in over time).
4. **Composes one tabbed report** — Tab 1 CE Health, Tab 2 CVR RCA, Tab 3 Paid
   Performance Audit — where each sub-skill's output appears **verbatim**.

The default window is last 30 days vs prior 30 days.

## Design principles

- **Composer, not editor.** Sub-skill outputs are shown verbatim — never
  summarized, reordered, or restyled. (A future summary skill may synthesize
  across tabs; the master never does.)
- **Sub-skills are untouched.** CE Health, CVR-RCA, and perf-audit run exactly as
  they do standalone. The only cross-skill coordination is a small
  `orchestration.json` handshake that stops perf-audit being fired twice.
- **Same look everywhere.** The composite reuses the shared `visual_kit.md`, so
  the umbrella report is visually identical to a standalone CVR-RCA report.
- **Scalable.** Adding a future deep-dive skill (AOV-RCA, Completion-RCA, …) is a
  one-row edit in `references/registry.md` plus one entry in
  `scripts/compose.py`'s `TAB_SPECS`.

## Architecture

| File | Role |
|---|---|
| `SKILL.md` | The orchestrator: Steps 0–3 (run CE Health → present + pause → dispatch → compose) |
| `references/registry.md` | Driver → sub-skill dispatch table + the orchestration handshake spec |
| `references/composition_rules.md` | How the tabbed report is assembled (verbatim fidelity, CVR-RCA extraction, styling) |
| `references/visual_kit.md` | Vendored copy of CVR-RCA's shared visual primitives (manual-sync) |
| `scripts/compose.py` | Builds the composite HTML from the run-dir artifacts |
| `scripts/helpers.py` | Markdown→HTML renderer + CVR-RCA tab/chart extraction |
| `templates/report.html` | Composite shell (header, tab bar, panes, tab JS, back-to-top) |

## Companion skills

CE-RCA orchestrates three skills, installed separately (see `INSTALL.md`):

- **CE Health** — required (the orientation step)
- **CVR-RCA** — `~/.cvr-rca/` (v1.24+ for the orchestration handshake)
- **perf-audit** — `~/.perf-audit-skill/`

Any companion that isn't installed simply won't appear as a tab — the run still
completes.

## Standalone skills still work

`/cvr-rca <CE>` and the perf-audit skill continue to run standalone exactly as
before. CE-RCA is additive — the umbrella on top, not a replacement.
