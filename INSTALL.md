# CE-RCA — Install / Update (one command)

You are Claude. A user pasted this file to set up CE-RCA. **The same command installs OR
updates** — this file auto-detects which at Step 0 and follows the matching path. Execute in
order, narrate each action, and don't ask for confirmation between steps.

CE-RCA is a **self-contained bundle**: it orchestrates four sub-skills (CE Health, CE
Context, CVR-RCA, perf-audit) vendored inside it under `skills/`. You install **one
thing** and everything is there — no separate companion installs, no path config.

---

## Step 0 — Detect: fresh install or already installed?

```bash
if [ -d "$HOME/.ce-rca" ]; then
  echo "existing:$(cat "$HOME/.ce-rca/VERSION" 2>/dev/null || echo unknown)"
else
  echo "fresh"
fi
```

- **`existing:<version>`** → this is an **update**. Say "Found CE-RCA v`<version>`. Updating…",
  then do **§ Update** below and **STOP — do not run the Fresh-install steps.**
- **`fresh`** → say "No existing install found. Installing CE-RCA now…" and go to
  **§ Fresh install (Steps 1–5)**.

---

## § Update (existing install) — version-bump + sanity check only

An update must **not** re-run the whole install. Bring the bundle to the latest version, then
only fix a prerequisite if it's actually broken.

**U1 — Update the version (whole bundle, from the repo).** Run folders under
`~/Documents/CE RCA Runs/` are never touched.
```bash
bash ~/.ce-rca/scripts/update_guard.sh
```
- **`UPDATED <old> <new>`** → "CE-RCA updated v`<old>` → v`<new>`."
- **`CURRENT <v>`** → "Already on the latest version (v`<v>`)."
- **`OFFLINE <v>`** → "Couldn't reach GitHub (3s timeout); you're on v`<v>`. Try again later."
> If `scripts/update_guard.sh` is missing (a pre-guard install), run the Fresh-install **Step 1**
> download once to refresh the bundle, then continue here.

**U2 — Sanity-check prerequisites (only fix what's broken).**
```bash
bq query --use_legacy_sql=false --project_id=headout-analytics --format=none 'SELECT 1' </dev/null >/dev/null 2>&1 && echo "BQ_OK" || echo "BQ_FAIL"
for c in ce-rca ce-context cvr-rca perf-audit ce-health; do [ -f "$HOME/.claude/commands/$c.md" ] && echo "✓ $c" || echo "✗ $c"; done
```
- **`BQ_FAIL`** → a prerequisite regressed. Re-run the idempotent setup `bash ~/.ce-rca/scripts/onboarding.sh`, then re-run the smoke query. **`BQ_OK`** → skip onboarding.
- Any command **`✗`** → re-run the Fresh-install **Step 3** registration block (it rewrites all five command files). All **`✓`** → skip.

**U3 — Confirm.** `cat ~/.ce-rca/VERSION`, then give the user **one line** with only what
changed (e.g. *"Updated v2.56.3 → v2.57.0; prerequisites and commands already in place."*). Do
**not** print the full "how to use" brief on an update. **Done — STOP here; skip everything below.**

---

## § Fresh install (Steps 1–5) — run these only when Step 0 said `fresh`

## Step 1 — Download & verify the bundle

```bash
curl -L https://github.com/satvikdhumaleheadout/ce-rca-skill/archive/refs/heads/main.zip -o /tmp/ce-rca-install.zip
unzip -q /tmp/ce-rca-install.zip -d /tmp/
rm -rf ~/.ce-rca
mv /tmp/ce-rca-skill-main ~/.ce-rca
rm /tmp/ce-rca-install.zip
```

Confirm the bundle is present and complete (master + the four vendored sub-skills) — this
must pass before Step 2, which runs a script from inside the bundle:

```bash
[ -f ~/.ce-rca/SKILL.md ] && echo "ok: $(cat ~/.ce-rca/VERSION)" || echo "FAILED"
for s in ce-context cvr-rca perf-audit ce-health; do
  [ -e "$HOME/.ce-rca/skills/$s" ] && echo "  ✓ skills/$s" || echo "  ✗ MISSING skills/$s"
done
```

If it says `FAILED` or any sub-skill is `✗ MISSING`, the download was incomplete — check
connectivity and re-run Step 1. Otherwise: "Installed CE-RCA master to `~/.ce-rca/`."

---

## Step 2 — Set up prerequisites & sign in

This is the one-time setup that makes the machine able to run CE-RCA. Run it now (use a
**long timeout** — it may install the Google Cloud SDK and opens a browser for sign-in):

```bash
bash ~/.ce-rca/scripts/onboarding.sh
```

What to expect, and how to guide the user:
- It **installs the Google Cloud SDK (gcloud + bq) if missing**, installs the Python deps,
  then opens a browser for **up to two Google sign-ins** (BigQuery + Drive). Tell the user
  to **sign in with their Headout Google account and click Allow**, and to **approve any
  permission prompt**.
- It is **conditional / idempotent** — already-set-up machines are an **instant no-op** (no
  browser), so updates don't re-prompt.
- It finishes by verifying **BigQuery** and **Drive** — relay the result to the user.

**Graceful:** if it can't finish (e.g. the user lacks access to the `headout-analytics`
BigQuery project), report exactly what it printed and **continue the install** — the skill's
own Step-0 preflight will re-hand the setup instruction at the first `/ce-rca` run. Never
leave the install half-done over this.

**Optional — connect a Slack MCP** (the one dependency `onboarding.sh` can't set up, because
it's a Claude Code connector, not a CLI tool). It adds operational Slack context (supply/PPC
changes, known-issue threads) to the CE Context tab. Tell the user: *"Optional — for Slack
signals, connect any Slack MCP in Claude Code (Settings → Connectors). The skill auto-detects
it by tool name; no specific server is required. Without it, Slack context is gracefully
skipped and everything else runs normally."* This is the **only** external piece beyond
BigQuery + Drive (both handled above) — there are no other MCPs or connectors to set up.

---

## Step 3 — Register the commands (`/ce-rca` + the four sub-skills)

The umbrella `/ce-rca` runs everything and composes the tabbed report. The four sub-skills
are vendored inside the bundle and each can also be run **on its own** → its own openable
`report.html`. Register a slash command for each:

```bash
mkdir -p ~/.claude/commands

# Umbrella — runs CE Health → CE Context + CVR-RCA + perf-audit → one composite report.
cat > ~/.claude/commands/ce-rca.md << 'EOF'
---
description: CE-level Root Cause Analysis — runs CE Health, CE Context, CVR-RCA + perf-audit, composes one tabbed report.
---

Read the skill file at: ~/.ce-rca/SKILL.md
EOF

# CE Context — standalone CE orientation brief (about / timeline / past RCAs / constraints / Slack).
cat > ~/.claude/commands/ce-context.md << 'EOF'
---
description: CE Context — standalone orientation brief for a CE (what it is, known constraints, prior RCAs, Slack). Produces its own report.html.
---

Read the skill file at: ~/.ce-rca/skills/ce-context/SKILL.md and run it STANDALONE for
the CE the user names (resolve the CE, confirm the window, and on render pass
`--standalone` so an openable `report.html` lands in the run dir).
EOF

# CVR-RCA — standalone funnel/CVR root-cause analysis.
cat > ~/.claude/commands/cvr-rca.md << 'EOF'
---
description: CVR-RCA — standalone CVR / funnel root-cause analysis for a CE. Produces its own report.html.
---

Read the skill file at: ~/.ce-rca/skills/cvr-rca/SKILL.md and run it STANDALONE for the
CE the user names (it self-names a run dir and writes its own report.html).
EOF

# perf-audit — standalone paid performance audit.
cat > ~/.claude/commands/perf-audit.md << 'EOF'
---
description: Perf-Audit — standalone paid performance audit for a CE. Produces its own report.html.
---

Read the skill file at: ~/.ce-rca/skills/perf-audit/SKILL.md and run it STANDALONE for
the CE the user names (after the report markdown is final, render the HTML with
`~/.ce-rca/scripts/render_perf_audit.py --run-dir <run_dir> --standalone` → report.html).
EOF

# CE Health — standalone CE briefing packet (vitals, channels, funnel, Shapley).
cat > ~/.claude/commands/ce-health.md << 'EOF'
---
description: CE Health — standalone CE briefing packet (vitals, channels, funnel, L12M, Shapley). Produces its own report.html.
---

Read the skill file at: ~/.ce-rca/skills/ce-health/SKILL.md and run it STANDALONE for the
CE the user names (write artifacts with the canonical `ce_health_report.{md,json}` names
into a run dir, then `~/.ce-rca/scripts/render_ce_health.py --run-dir <run_dir> --standalone`
→ report.html).
EOF
```

Tell the user: "Registered `/ce-rca` + the four sub-skill commands." Each points at its
vendored `SKILL.md`, so its `$SKILL_DIR/../../scripts/` references resolve to
`~/.ce-rca/scripts/` — the shared renderers stay reachable.

---

## Step 4 — Create the runs folder

```bash
mkdir -p ~/Documents/CE\ RCA\ Runs
```

"Created runs folder at `~/Documents/CE RCA Runs/`."

---

## Step 5 — Confirm

```bash
cat ~/.ce-rca/VERSION
```

Tell the user the installed version, then give them this **structured "how to use" brief**
(keep it exactly this tight):

> **✅ CE-RCA v[VERSION] installed and set up.** Restart Claude Code — you're ready.
>
> **What it does** — One command gives you the full picture of a Combined Entity: its
> health (revenue, traffic, CVR, AOV, completion, take-rate), *why* the number moved
> (funnel + paid deep-dives), and what to do — as **one tabbed report**.
>
> **The commands** — `<CE>` is a CE ID or name (e.g. `252` or `"Louvre Museum"`):
> - **`/ce-rca <CE>`** — the full picture: CE health + funnel + paid, composed into one tabbed report. *Start here.* — e.g. `/ce-rca 252`
> - **`/ce-context <CE>`** — orientation brief: what the CE is, known constraints, prior RCAs, Slack signals. — e.g. `/ce-context 252`
> - **`/cvr-rca <CE>`** — funnel / conversion-rate root-cause (where the funnel leaks). — e.g. `/cvr-rca 252`
> - **`/perf-audit <CE>`** — paid-performance audit (spend, clicks, CPC, take rate, ROI). — e.g. `/perf-audit 252`
> - **`/ce-health <CE>`** — vitals briefing (revenue, traffic, CVR, AOV, completion, take-rate, Shapley). — e.g. `/ce-health 252`
>
> `/ce-rca` is the umbrella (runs the other four and composes them); the rest are standalone and each
> writes its own openable `report.html`. Default window is the last 30 days vs the prior 30.
>
> **What it'll ask you (3 quick checkpoints)**
> 1. **Window** — confirm the default 30-vs-30, or give your own dates.
> 2. **Direction** — after a quick CE Health diagnosis, it asks which areas to dig into
>    (or just say *continue* to take its recommendation).
> 3. **Context (optional)** — add what you know to sharpen the run (a focus area, a known
>    event + date, a doc / Sheet / Slack link). Skip with *continue* — zero friction.
>
> **What you get** — a tabbed HTML report: **Summary · CE Health · CVR RCA · Paid Performance
> Audit · Transcript**. It opens in your browser; the file lives in `~/Documents/CE RCA Runs/`,
> and every run also auto-archives to the team Shared Drive.
>
> **Ask follow-ups after** — in the same chat: *"why is S2C the top driver?"*, *"club TGIDs
> 3909 + 3910"*, *"split the drop by device"*. It answers from the run's data (or a quick
> re-query). Changing the **time window** starts a fresh run, not a follow-up.
>
> **Stays current automatically** — each run self-updates if yours is behind. No manual updates.

---

## Appendix — Optional & troubleshooting

- **Fix auth anytime:** re-run `bash ~/.ce-rca/scripts/onboarding.sh` — it's a no-op if
  everything's already fine, and only fixes what's missing.
- **No BigQuery access:** if onboarding reports you lack access to the `headout-analytics`
  project, request it, then re-run onboarding. (BigQuery is required; without it CE-RCA can't run.)
- **Slack (optional):** see Step 2 — connect any Slack MCP in Claude Code for operational Slack
  context; gracefully skipped if absent.
- **Drive archive:** every run uploads `report.html` + a full-run zip to the team **Shared
  Drive** (set up by onboarding). Recover or share a past run later:
  `python3 ~/.ce-rca/scripts/drive_sync.py --recover --run-name "<ce-or-date>"`.
  (Scope/mechanics details are in `SKILL.md` / `CHANGELOG.md`.)
- **Google Sheets ingestion** (for the optional "share a Sheet" context step) is covered by
  onboarding's ADC scope — no separate setup.
