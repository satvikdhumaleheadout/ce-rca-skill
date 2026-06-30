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
| `SKILL.md` | The orchestrator: auto-update check → Steps 0–5 (run CE Health → present + pause → dispatch → compose → follow-ups) |
| `skills/{cvr-rca,perf-audit,ce-health}/` | Vendored sub-skills, run from fixed paths inside the bundle |
| `references/registry.md` | Driver → sub-skill dispatch table + the orchestration handshake spec |
| `references/composition_rules.md` | How the tabbed report is assembled (verbatim fidelity, CVR-RCA extraction, styling) |
| `references/visual_kit.md` | Vendored copy of CVR-RCA's shared visual primitives (manual-sync) |
| `scripts/compose.py` | Builds the composite HTML from the run-dir artifacts |
| `scripts/helpers.py` | Markdown→HTML renderer + CVR-RCA tab/chart extraction |
| `templates/report.html` | Composite shell (header, tab bar, panes, tab JS, back-to-top) |

## Install

CE-RCA is a **self-contained bundle** — you install one thing and the three
sub-skills come with it. **No GitHub CLI needed.** In Claude Code / Cowork, paste:

```
Install the CE-RCA skill from:
https://raw.githubusercontent.com/satvikdhumaleheadout/ce-rca-skill/main/INSTALL.md
```

Claude runs the installer: downloads the bundle to `~/.ce-rca/`, registers the
`/ce-rca` command, checks prerequisites (`bq`, Python 3.9+), and creates the runs
folder. Then `/ce-rca <CE>`.

**Always-latest, automatically.** At the start of **every** run — the `/ce-rca` umbrella
**and** any standalone sub-skill (`/ce-context`, `/cvr-rca`, `/perf-audit`, `/ce-health`) —
the skill checks the published `VERSION` and, if the local bundle is behind, **silently
re-downloads the whole bundle and continues**. Running any single piece updates the **entire**
CE-RCA, so you can never run a stale version from a sub-skill. No minimum-version gate; offline
runs proceed on the installed bundle.

**One command for install *and* update.** To update manually, paste the **same** command as
install (above) — `INSTALL.md` auto-detects: if CE-RCA is already installed it does a lean
**update only** (bumps the version, and re-runs sign-in / command registration *only if a
sanity check finds them missing*); if it's a fresh machine it does the full install. No
separate update command to remember.

## Bundled sub-skills

The three sub-skills are **vendored inside the bundle** under
`~/.ce-rca/skills/` — no separate installs, no path configuration:

- **CE Health** — `skills/ce-health/` (the orientation step; required)
- **CVR-RCA** — `skills/cvr-rca/` (the funnel deep-dive)
- **perf-audit** — `skills/perf-audit/` (the paid deep-dive)

Maintainers refresh these snapshots with `bash ~/.ce-rca/scripts/vendor.sh`
before a release. A sub-skill not selected for a run simply won't appear as a
tab — the run still completes.

## Standalone skills still work

`/cvr-rca <CE>` and the perf-audit skill continue to run standalone exactly as
before. CE-RCA is additive — the umbrella on top, not a replacement.
