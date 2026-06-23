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

> ### 🚀 First-time setup — easiest path (no Terminal needed)
> **Paste this prompt into Claude Code and send it.** Claude runs the onboarding script on your
> machine; you just complete the Google sign-ins when the browser opens:
>
> ```
> Set up CE-RCA on my machine. Run `bash ~/.ce-rca/scripts/onboarding.sh` with a long
> timeout (it can take several minutes and may install the Google Cloud SDK). Approve any
> permission prompt. It will open a browser TWICE for Google sign-in — both times, sign in
> with my Headout Google account and click Allow. When it's done, tell me whether BigQuery
> and Drive both verified, and what to do if either failed.
> ```
>
> That's it — **install → paste this → approve → two browser logins → done.** (The two sign-ins
> need a human click; Google won't let that be automated.)
>
> **Equivalent in a Terminal**, if you prefer:
> ```bash
> bash ~/.ce-rca/scripts/onboarding.sh
> ```
> Either way it **installs the Google Cloud SDK if missing** (gcloud + bq), installs the Python deps,
> does the Google sign-ins (bq CLI + Drive, then ADC), sets the project/quota project, and verifies
> **both BigQuery and Drive** — no manual CLI setup per user. It's **conditional**: it only does the
> pieces that are missing, so it's **an instant no-op for anyone already set up** (no browser) and
> safe to run or re-run. The checks below are the manual equivalents (useful for diagnosing a failed
> onboarding).

```bash
bq version 2>&1 | head -1 || echo "NOT FOUND"
python3 --version 2>&1 | head -1 || echo "NOT FOUND"
```

If `bq` is missing, tell the user: "Run `scripts/onboarding.sh` (it installs the Google Cloud SDK),
or install it manually before using the skill." Python 3.9+ is required for `compose.py`.

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

**Optional — Google Sheets context ingestion.** The `read_sheet.py` helper (Step 1 ad-hoc Sheet
ingestion) uses your gcloud ADC. Enable it once with the dependency + a login that grants the
**Sheets read** scope:

```bash
pip3 install google-api-python-client google-auth
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,\
https://www.googleapis.com/auth/spreadsheets.readonly
```

If skipped, sheet ingestion falls back to the Drive MCP (less reliable); docs and Slack channels
are unaffected. (You don't need to run this separately — **`scripts/onboarding.sh`** below grants
the Sheets, BigQuery, and Drive scopes in one login.)

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

**Drive archive of every run (for review & skill improvement).** At the end of each run
(Step 4g) CE-RCA uploads the finished `report.html` **plus a zip of the whole run** — and any
`feedback.md` / follow-up log captured in the playground — into a **shared central Google Shared
Drive**, so runs accumulate in one place for review and easy sharing. This uses the first-party
uploader `scripts/drive_sync.py`, which uploads via the **gcloud account token** + the Drive API —
**not** the Drive MCP connector (it embeds bytes in the tool call and can't carry large files like
`report.html`), and **not** ADC (an ADC Drive call demands a quota project + `serviceusage` that
data-only BigQuery users lack). The account-token path is the same credential family `bq` uses, so
it "just works" with no quota project / serviceusage / per-user IAM. One-time setup, run once per
machine in a normal Terminal:

```bash
bash "$SKILL_DIR/scripts/onboarding.sh"
```

`onboarding.sh` is idempotent and sets up **everything the skill needs in one go**: it checks
`gcloud` is installed (prints the install line if not), installs the Python deps
(`google-api-python-client`, `google-auth`), then does **two browser sign-ins** — **[1/2]**
`gcloud auth login --enable-gdrive-access` (account creds → powers the **bq CLI + Drive uploads**)
and **[2/2]** an ADC login (→ the Python BigQuery client + optional Sheet ingestion) — sets the
project + ADC quota project, and verifies **both BigQuery and Drive**.

```
# Central Google Shared Drive (company-wide contributor access already granted):
CE_RCA_DRIVE_PARENT = 0AONjDQrW9gVvUk9PVA
# https://drive.google.com/drive/folders/0AONjDQrW9gVvUk9PVA
```

- **Scope tradeoff (be aware).** `--enable-gdrive-access` grants gcloud's **full Drive scope** (the
  same access `bq` uses for Drive-backed tables), which is **broader than the narrow `drive.file`**
  — the credential *can* see your Drive. The chosen tradeoff: it's the only path that avoids the
  ADC quota-project/`serviceusage` wall (i.e. zero per-user GCP IAM). The **script itself only ever
  creates and writes its own per-run folders** in the Shared Drive — it never reads or modifies your
  other files. (If/when the team moves to a setup where `drive.file` works, downgrade the scope.)
- **Access — already done, no per-user step.** The central Shared Drive grants **all-company
  contributor** access, so there is **no per-user sharing/IAM** — every member can write the moment
  they've signed in.
- **Classifier-safe.** `drive_sync.py` is a named CLI doing a normal authenticated upload with your
  own creds (no base64 through any context window), so it is **not** the data-exfiltration shape a
  safety check blocks. If a `pip`/`gcloud` step in onboarding ever prompts under auto-mode, add an
  allow-rule for it to `~/.claude/settings.json` under `permissions.allow`.
- **Graceful:** if onboarding hasn't run (no ADC / no Drive scope / deps absent), the run still
  completes — the report is delivered locally and the Drive sync is logged + skipped, never blocks.
- **Recover / share later:** `python3 "$SKILL_DIR/scripts/drive_sync.py" --recover --run-name "<ce-or-date>"`.
- **To re-point** at a different Shared Drive/folder, set the `CE_RCA_DRIVE_PARENT` env var (or pass
  `--parent-folder-id`); the built-in default also lives in `scripts/drive_sync.py`.

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

> **✅ CE-RCA v[VERSION] installed.** Restart Claude Code, then do the one-time setup below.
>
> **① First-time setup (once per machine) — paste this into Claude Code and send:**
> ```
> Set up CE-RCA on my machine. Run `bash ~/.ce-rca/scripts/onboarding.sh` with a long
> timeout (it can take several minutes and may install the Google Cloud SDK). Approve any
> permission prompt. It will open a browser TWICE for Google sign-in — both times, sign in
> with my Headout Google account and click Allow. When done, tell me whether BigQuery and
> Drive both verified.
> ```
> Claude runs the setup for you; you just complete the two Google logins in the browser. (Prefer
> a terminal? `bash ~/.ce-rca/scripts/onboarding.sh` does the same thing.) You only do this once.
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
