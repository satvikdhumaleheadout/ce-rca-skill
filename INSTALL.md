# CE-RCA Skill Installer

You are Claude. A user has asked you to install or update the CE-RCA master
skill from this file. Execute every step below in order, narrating each action
as you go. Do not ask for confirmation between steps — just do it and report.

CE-RCA is a **self-contained bundle**: it orchestrates four sub-skills (CE
Health, CE Context, CVR-RCA, perf-audit) that are **vendored inside it** under
`skills/`. You install **one thing** and everything is there — no separate
companion installs, no path configuration. The master runs each sub-skill from its
fixed path inside the bundle (`skills/ce-context/`, `skills/cvr-rca/`,
`skills/perf-audit/`, `skills/ce-health/`).

---

## Step 0 — Detect: fresh install or update?

```bash
if [ -d "$HOME/.ce-rca" ]; then
  EXISTING_VERSION=$(cat "$HOME/.ce-rca/VERSION" 2>/dev/null || echo "unknown")
  echo "existing:$EXISTING_VERSION"
else
  echo "fresh"
fi
```

- Fresh: "No existing install found. Installing CE-RCA now..."
- Update: "Found CE-RCA v`EXISTING_VERSION`. Updating to latest..."

---

## Step 1 — Check prerequisites

```bash
bq version 2>&1 | head -1 || echo "NOT FOUND"
python3 --version 2>&1 | head -1 || echo "NOT FOUND"
```

If `bq` is missing, tell the user: "Install Google Cloud SDK before using the skill.
Continuing the install anyway." Python 3.9+ is required for `compose.py`.

**Live query check — can they actually run BigQuery? (this is what the skill needs).**
Presence of `bq` is not enough; the skill fails at runtime if `gcloud` auth isn't set up or the
user has no access to the `headout-analytics` project. Run a 1-row smoke query:

```bash
if bq query --use_legacy_sql=false --project_id=headout-analytics --format=none 'SELECT 1' </dev/null >/dev/null 2>&1; then
  echo "QUERY OK"
else
  echo "QUERY FAILED"
fi
```

- **`QUERY OK`** → "✓ BigQuery is reachable — you're ready to run CE-RCA." Continue.
- **`QUERY FAILED`** → the install still completes (files are placed), but **warn prominently** that
  the skill won't work until this is fixed, and give the exact remedy:

  > ⚠️ **BigQuery query failed — your gcloud auth isn't set up (or you lack access to
  > `headout-analytics`).** CE-RCA can't run until this passes. Fix it with:
  > ```
  > gcloud auth application-default login
  > ```
  > Then re-run the smoke query above. If it still fails, you don't yet have access to the
  > `headout-analytics` BigQuery project — request it, then retry. (Everything else installed fine;
  > no need to reinstall — just fix auth.)

  Do not claim the skill is ready to run if this failed.

**Optional — Google Sheets context ingestion + Drive archive.** Both the `read_sheet.py`
helper (Step 1 ad-hoc Sheet ingestion) and `drive_sync.py` (the optional Step 4g run-archive
command) use your gcloud ADC. Enable them once with the dependency + a login that grants the
**Sheets read** and **Drive file** scopes together:

```bash
pip3 install google-api-python-client google-auth
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,\
https://www.googleapis.com/auth/spreadsheets.readonly,\
https://www.googleapis.com/auth/drive.file
```

The `drive.file` scope is minimal by design — it only grants access to files the
script **creates** (its per-run subfolders + uploads), never your wider Drive. If
skipped, sheet ingestion falls back to the Drive MCP (less reliable) and the optional
Drive archive command just errors when run; docs and Slack channels are unaffected.

**Optional — Slack signals (operational context).** The **CE Context** sub-skill pulls
operational Slack signals (bug alerts, supply/inventory, campaign changes, known-issue
probes) — it **owns the single Slack search** for the whole run, surfaces them in the CE
Context tab, and CVR-RCA corroborates findings against the same `slack_context.md` (it does
not search Slack again under the umbrella; a standalone `/cvr-rca` still does its own). This
requires the **Slack MCP connected** in your environment. If the Slack MCP is **not**
connected, Slack collection is **gracefully skipped** — no `slack_context.md` is produced,
and the report reports Slack as **"unavailable"** (it will never claim threads were searched
or cite Slack signals when the MCP was absent). Everything else runs normally; Slack is
purely additive context.

**Optional Drive archive (user-run, for review).** At the end of a run (Step 4g) CE-RCA
**prints a command** the user can run to archive the finished run — `report.html` + a zip of
the run folder — into a **shared central Google Drive folder**, so runs accumulate in one
place to review and improve the skill. The skill **does not upload anything itself**: an agent
auto-uploading local files trips the safety classifier as data-exfiltration, whereas a command
the user chooses to run does not (Claude Code shows a one-click run button on the command).
The archive is driven by the first-party **`scripts/drive_sync.py`** helper using your gcloud
ADC (see the scope setup above), is **additive-only** (create, never update/delete), and the
central folder is a constant in the script:

```
DEFAULT_PARENT_FOLDER_ID = 1nernSzAN2mZ531wEdh95eeNL2RV5oq30
# https://drive.google.com/drive/folders/1nernSzAN2mZ531wEdh95eeNL2RV5oq30
```

- **Owner, one-time:** **share this central folder (edit access) with the team** so everyone's
  runs can upload into it. Each run creates its own per-run subfolder (`<run-name>-<hash>`).
- **To re-point** at a different folder, change `DEFAULT_PARENT_FOLDER_ID` in
  `scripts/drive_sync.py`, or pass `--parent-folder-id` on the command.

---

## Step 2 — Download and install the master

```bash
curl -L https://github.com/satvikdhumaleheadout/ce-rca-skill/archive/refs/heads/main.zip -o /tmp/ce-rca-install.zip
unzip -q /tmp/ce-rca-install.zip -d /tmp/
rm -rf ~/.ce-rca
mv /tmp/ce-rca-skill-main ~/.ce-rca
rm /tmp/ce-rca-install.zip
```

Then confirm the download succeeded:

```bash
[ -f ~/.ce-rca/SKILL.md ] && echo "ok: $(cat ~/.ce-rca/VERSION)" || echo "FAILED"
```

If it says `FAILED`, the download was incomplete — check connectivity and re-run Step 2.
Otherwise: "Installed CE-RCA master to `~/.ce-rca/`."

---

## Step 3 — Register the commands (`/ce-rca` + the four sub-skills)

The umbrella `/ce-rca` runs everything and composes the tabbed report. The four
sub-skills are **vendored inside the bundle** and each can also be run **on its own**
(its own window, its own decision logic) → its own openable `report.html`. Register a
slash command for each so users can invoke any of them directly:

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

Tell the user: "Registered `/ce-rca` + the four sub-skill commands (`/ce-context`,
`/cvr-rca`, `/perf-audit`, `/ce-health`)." Each sub-skill command points at its
vendored `SKILL.md` inside the bundle, so its `$SKILL_DIR/../../scripts/` references
resolve to `~/.ce-rca/scripts/` — the shared renderers stay reachable.

---

## Step 4 — Create the runs folder

```bash
mkdir -p ~/Documents/CE\ RCA\ Runs
```

Tell the user: "Created runs folder at `~/Documents/CE RCA Runs/`."

---

## Step 5 — Verify the bundle is complete

The sub-skills ship inside the bundle, so there are no separate companion
installs. Just confirm they're present:

```bash
for s in ce-context cvr-rca perf-audit ce-health; do
  if [ -e "$HOME/.ce-rca/skills/$s" ]; then echo "  ✓ skills/$s"; else echo "  ✗ MISSING skills/$s"; fi
done
```

All four should be `✓`. If any is missing, the download was incomplete —
re-run Step 2. (Maintainers refreshing the vendored copies use
`bash ~/.ce-rca/scripts/vendor.sh`.)

---

## Step 6 — Confirm

```bash
cat ~/.ce-rca/VERSION
```

Tell the user the installed version, then give them this **structured "how to use"
brief** (keep it exactly this tight — it's their onboarding):

> **✅ CE-RCA v[VERSION] installed.** Restart Claude Code, then you're ready.
>
> **What it does** — One command gives you the full picture of a Combined Entity:
> its health (revenue, traffic, CVR, AOV, completion, take-rate), *why* the number
> moved (funnel + paid deep-dives), and what to do — as **one tabbed report**.
>
> **How to run it**
> ```
> /ce-rca <CE ID or name>
> ```
> e.g. `/ce-rca 252` or `/ce-rca "Louvre Museum"`. Default window is last 30 days
> vs the prior 30.
>
> **Or run just one piece** — each sub-skill works standalone and gives its own
> openable `report.html`:
> `/ce-context <CE>` (CE orientation brief) · `/cvr-rca <CE>` (funnel / CVR) ·
> `/perf-audit <CE>` (paid performance) · `/ce-health <CE>` (vitals briefing).
>
> **What it'll ask you (3 quick checkpoints)**
> 1. **Window** — confirm the default 30-vs-30, or give your own dates.
> 2. **Direction** — after a quick CE Health diagnosis, it asks which areas to dig
>    into (or just say *continue* to take its recommendation).
> 3. **Context (optional)** — you can add what you already know to sharpen the run:
>    a focus area, a known event + date ("price change Apr 8"), or a link to a doc /
>    Google Sheet / Slack channel. Skip it by saying *continue* — zero friction.
>
> **What you get** — a tabbed HTML report: **Summary** (the whole story, standalone)
> · **CE Health** · **CVR RCA** · **Paid Performance Audit** · **Transcript**. It
> opens in your browser; the file lives in `~/Documents/CE RCA Runs/`.
>
> **Ask follow-ups after** — the report isn't the end. In the same chat, just ask:
> *"why is S2C the top driver?"*, *"club TGIDs 3909 + 3910"*, *"split the drop by
> device"*. It answers from the run's data (or a quick re-query) and can fold the
> Q&A into the report if you want. **Note:** changing the **time window** starts a
> fresh run, not a follow-up.
>
> **Stays current automatically** — each run self-updates to the latest version if
> yours is behind; offline runs use what's installed. No manual updates.
