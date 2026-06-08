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
sub-skills come with it. **No GitHub CLI needed.** The repo is private, so access is
gated by a **read-only, repo-scoped token** you mint once (see *Getting your access
token* below).

In Claude Code / Cowork, paste this (replace `<YOUR_TOKEN>` with your token):

```
Install the CE-RCA skill. First save my access token, then fetch and run INSTALL.md:

printf '%s' '<YOUR_TOKEN>' > ~/.ce-rca-token && chmod 600 ~/.ce-rca-token
TOKEN=$(cat ~/.ce-rca-token)
curl -sL -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github.raw" \
  "https://api.github.com/repos/satvikdhumaleheadout/ce-rca-skill/contents/INSTALL.md"

Then follow every step of that INSTALL.md.
```

Claude saves the token to `~/.ce-rca-token`, downloads the bundle to `~/.ce-rca/`,
registers the `/ce-rca` command, checks prerequisites (`bq`, Python 3.9+), and creates
the runs folder. Then `/ce-rca <CE>`.

**Always-latest, automatically.** At the start of every run the skill checks the
published `VERSION` (using your saved token) and, if the local bundle is behind,
**silently re-downloads the latest and continues** — you never run a stale version, and
there's no minimum-version gate. No token / offline → it runs the installed bundle.

### Getting your access token

A **fine-grained personal access token**, read-only, scoped to just this repo:

1. GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. **Resource owner:** `satvikdhumaleheadout`. **Repository access:** *Only select repositories* → `ce-rca-skill`.
3. **Permissions:** *Repository permissions* → **Contents: Read-only** (Metadata: Read is added automatically). Nothing else.
4. **Expiration:** pick a window (e.g. 90 days) and re-mint when it lapses, or set a longer one per your security posture.
5. Generate, copy the `github_pat_…` value, and drop it into the install snippet above.

**Security:** the token grants *read of this one repo only* — nothing else, no write. It lives
only in `~/.ce-rca-token` on your machine (chmod 600), is never committed to the repo, and is
revocable any time from the same GitHub settings page. Don't paste it into shared chats or docs;
share the install snippet privately. (Maintainers: to widen or restrict access later, rotate or
revoke the token — no code change needed.)

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
