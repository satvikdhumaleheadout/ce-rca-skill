# CE-RCA Skill Installer

You are Claude. A user has asked you to install or update the CE-RCA master
skill from this file. Execute every step below in order, narrating each action
as you go. Do not ask for confirmation between steps — just do it and report.

CE-RCA is a **self-contained bundle**: it orchestrates three sub-skills (CE
Health, CVR-RCA, perf-audit) that are **vendored inside it** under `skills/`. You
install **one thing** and everything is there — no separate companion installs,
no path configuration. The master runs each sub-skill from its fixed path inside
the bundle (`skills/cvr-rca/`, `skills/perf-audit/`, `skills/ce-health/`).

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

If `bq` is missing, tell the user the sub-skills need it: "Install Google Cloud
SDK and run `gcloud auth application-default login` before using the skill.
Continuing the install anyway." Python 3.9+ is required for `compose.py`.

**Optional — Google Sheets context ingestion.** If users will point the Step 1
context layer at ad-hoc Google Sheets, enable the `read_sheet.py` helper once:

```bash
pip3 install google-api-python-client google-auth
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets.readonly
```

This lets the context-ingestion sub-agent read private sheets via your gcloud
identity. If skipped, sheet ingestion falls back to the Drive MCP (less reliable);
docs and Slack channels are unaffected.

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

## Step 3 — Register the /ce-rca command

```bash
mkdir -p ~/.claude/commands
cat > ~/.claude/commands/ce-rca.md << 'EOF'
---
description: CE-level Root Cause Analysis — runs CE Health, then dispatches CVR-RCA + perf-audit, composes one tabbed report.
---

Read the skill file at: ~/.ce-rca/SKILL.md
EOF
```

Tell the user: "Registered the `/ce-rca` command."

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
for s in cvr-rca perf-audit ce-health; do
  if [ -e "$HOME/.ce-rca/skills/$s" ]; then echo "  ✓ skills/$s"; else echo "  ✗ MISSING skills/$s"; fi
done
```

All three should be `✓`. If any is missing, the download was incomplete —
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
