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

Tell the user the installed version and summarise:

> **CE-RCA v[VERSION] installed/updated successfully.**
>
> - Bundle: `~/.ce-rca/` (contains CVR-RCA, perf-audit, CE Health under `skills/`)
> - Command: `/ce-rca`
> - Runs folder: `~/Documents/CE RCA Runs/`
>
> **Restart Claude Code** for the command to take effect.
>
> **Run:** `/ce-rca <CE ID or name>` — it runs CE Health, shows the diagnosis,
> asks which directions to deep-dive, then composes a tabbed report. Everything
> runs from inside the bundle — no other setup.
>
> **Stays up to date automatically:** each run checks the published version and
> silently re-downloads the latest bundle if yours is behind — no manual updates,
> no minimum-version gate. (Offline runs use the installed bundle.)
