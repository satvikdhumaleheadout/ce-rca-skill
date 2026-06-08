# CVR-RCA Skill Installer

You are Claude. A user has asked you to install or update the CVR-RCA skill
from this file. Execute every step below in order, narrating each action to
the user as you go. Do not ask for confirmation between steps — just do it and
report what happened.

---

## Step 0 — Detect: fresh install or update?

```bash
if [ -d "$HOME/.cvr-rca" ]; then
  EXISTING_VERSION=$(cat "$HOME/.cvr-rca/VERSION" 2>/dev/null || echo "unknown")
  echo "existing:$EXISTING_VERSION"
else
  echo "fresh"
fi
```

Tell the user:
- Fresh: "No existing install found. Installing CVR-RCA now..."
- Update: "Found CVR-RCA v`EXISTING_VERSION` installed. Updating to latest..."

---

## Step 1 — Check prerequisites

Run these checks and tell the user the result of each:

```bash
# Check bq CLI
bq version 2>&1 | head -1 || echo "NOT FOUND"
```

If `bq` is not found, tell the user:
> "The `bq` CLI is required to run queries. Install Google Cloud SDK and run
> `gcloud auth application-default login` before using the skill. Continuing
> the install anyway."

---

## Step 2 — Download and install

```bash
curl -L https://github.com/satvikdhumaleheadout/cvr-rca-skill/archive/refs/heads/main.zip \
  -o /tmp/cvr-rca-install.zip
unzip -q /tmp/cvr-rca-install.zip -d /tmp/
rm -rf ~/.cvr-rca
mv /tmp/cvr-rca-skill-main ~/.cvr-rca
rm /tmp/cvr-rca-install.zip
```

Tell the user: "Downloaded and installed skill files to `~/.cvr-rca/`."

---

## Step 3 — Register the /cvr-rca command

```bash
mkdir -p ~/.claude/commands
cat > ~/.claude/commands/cvr-rca.md << 'EOF'
---
description: CVR Root Cause Analysis for a Headout Combined Experience.
---

Read the skill file at: ~/.cvr-rca/SKILL.md
EOF
```

Tell the user: "Registered (or refreshed) the `/cvr-rca` command with Claude Code."

---

## Step 4 — Create the runs folder

```bash
mkdir -p ~/Documents/CVR\ RCA\ Runs
```

Tell the user: "Created runs folder at `~/Documents/CVR RCA Runs/` — this is
where analysis outputs will land."

---

## Step 5 — Optional: install the perf-audit companion skill

The CVR-RCA skill can spawn a sub-agent that runs a separate **perf-audit
skill** when the cascade fixes on Paid. It enriches the root cause with
traffic-quality signals (SIS, CPC trends, campaign pauses, tROAS suppression)
that CVR-RCA's funnel-table data cannot see. CVR-RCA runs fully without it —
this step is optional.

Check whether the user already has it:

```bash
if [ -d "$HOME/.perf-audit-skill" ] || [ -d "$HOME/Documents/perf-audit-skill" ]; then
  echo "perf-audit found"
else
  echo "perf-audit not found"
fi
```

If not found, ask the user: "Install the perf-audit companion skill at
`~/.perf-audit-skill`? It's optional but unlocks paid-traffic enrichment for
CVR-RCAs that route through Paid. (y/n)"

If they say yes:

```bash
curl -L https://github.com/aaradhyaraiHO/perf-audit-skill/archive/refs/heads/main.zip \
  -o /tmp/perf-audit-install.zip
unzip -q /tmp/perf-audit-install.zip -d /tmp/
rm -rf ~/.perf-audit-skill
mv /tmp/perf-audit-skill-main ~/.perf-audit-skill
rm /tmp/perf-audit-install.zip
```

Tell the user: "Installed perf-audit skill to `~/.perf-audit-skill/`. CVR-RCA
will auto-detect it whenever the cascade fixes on Paid."

If they say no, tell them: "Skipped. CVR-RCA will log `Perf-audit skill not
installed — skipped` and continue without enrichment. You can install it
later by re-running this installer."

---

## Step 6 — Confirm

```bash
cat ~/.cvr-rca/VERSION
```

Tell the user the installed version. If this was a fresh install say "installed successfully", if it was an update say "updated successfully". Summary:

> **CVR-RCA v[VERSION] installed/updated successfully.**
>
> - Skill files: `~/.cvr-rca/`
> - Command registered: `/cvr-rca`
> - Runs folder: `~/Documents/CVR RCA Runs/`
>
> **Restart Claude Code** (quit and reopen) for the changes to take effect.
>
> ---
>
> **How to run an analysis:**
>
> The basic command is:
> ```
> /cvr-rca <ce_id>
> ```
> This defaults to **last 30 days as the post period** and the **30 days
> before that as the pre period**. Use this when you've noticed a recent
> drop and want to investigate immediately.
>
> Example:
> ```
> /cvr-rca 167
> ```
>
> To investigate a specific window, use plain English or exact dates —
> either works:
> ```
> /cvr-rca 167 last complete week vs the week before it
> /cvr-rca 167 this year vs same time last year
> /cvr-rca 167 April vs March
> /cvr-rca 167 2026-03-01 2026-03-31 2026-04-01 2026-04-30
> ```
> (exact date format: `pre_start pre_end post_start post_end`)
>
> ---
>
> Optional: if you want run outputs saved to a different folder than
> `~/Documents/CVR RCA Runs/`, add this to `~/.zshrc`:
> ```
> export CVR_RCA_OUTPUT_DIR=~/Documents/your-preferred-folder
> ```
