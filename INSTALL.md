# CE-RCA Skill Installer

You are Claude. A user has asked you to install or update the CE-RCA master
skill from this file. Execute every step below in order, narrating each action
as you go. Do not ask for confirmation between steps — just do it and report.

CE-RCA is an **umbrella** skill: it orchestrates three sub-skills (CE Health,
CVR-RCA, perf-audit). It is most useful when all three are installed, but it
degrades gracefully — any sub-skill that isn't installed simply won't appear as
a tab. Steps 5–7 install the companions.

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

---

## Step 2 — Download and install the master

```bash
curl -L https://github.com/satvikdhumaleheadout/ce-rca-skill/archive/refs/heads/main.zip -o /tmp/ce-rca-install.zip
unzip -q /tmp/ce-rca-install.zip -d /tmp/
rm -rf ~/.ce-rca
mv /tmp/ce-rca-skill-main ~/.ce-rca
rm /tmp/ce-rca-install.zip
```

Tell the user: "Installed CE-RCA master to `~/.ce-rca/`."

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

## Step 5 — Companion: CE Health (required for the umbrella to work)

CE Health is the orientation step — without it the master has nothing to run.

```bash
if [ -d "$HOME/.ce-health-skill" ] || [ -d "$HOME/Documents/ce-health-skill-main" ]; then
  echo "ce-health found"
else
  echo "ce-health not found"
fi
```

If not found, tell the user CE-RCA needs it and point them at the CE Health repo
to install at `~/.ce-health-skill/`. (The master resolves it via
`$CE_HEALTH_SKILL_PATH` → `~/.ce-health-skill/` → `~/Documents/ce-health-skill-main/`.)

---

## Step 6 — Companion: CVR-RCA

```bash
if [ -d "$HOME/.cvr-rca" ]; then echo "cvr-rca found"; else echo "cvr-rca not found"; fi
```

If not found, point the user at the CVR-RCA installer
(`https://github.com/satvikdhumaleheadout/cvr-rca-skill`) to install at
`~/.cvr-rca/`. CVR-RCA v1.24+ is required (it carries the `orchestration.json`
delegation check that prevents perf-audit from being fired twice).

---

## Step 7 — Companion: perf-audit

```bash
if [ -d "$HOME/.perf-audit-skill" ]; then echo "perf-audit found"; else echo "perf-audit not found"; fi
```

If not found, point the user at `https://github.com/aaradhyaraiHO/perf-audit-skill`
to install at `~/.perf-audit-skill/`.

---

## Step 8 — Confirm

```bash
cat ~/.ce-rca/VERSION
```

Tell the user the installed version and summarise:

> **CE-RCA v[VERSION] installed/updated successfully.**
>
> - Master skill: `~/.ce-rca/`
> - Command: `/ce-rca`
> - Runs folder: `~/Documents/CE RCA Runs/`
> - Companions detected: CE Health [✓/✗], CVR-RCA [✓/✗], perf-audit [✓/✗]
>
> **Restart Claude Code** for the command to take effect.
>
> **Run:** `/ce-rca <CE ID or name>` — it runs CE Health, shows the diagnosis,
> asks which directions to deep-dive, then composes a tabbed report.
