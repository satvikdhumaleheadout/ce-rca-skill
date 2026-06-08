# CE-RCA Skill Installer

You are Claude. A user has asked you to install or update the CE-RCA master
skill from this file. Execute every step below in order, narrating each action
as you go. Do not ask for confirmation between steps — just do it and report.

CE-RCA is a **self-contained bundle**: it orchestrates three sub-skills (CE
Health, CVR-RCA, perf-audit) that are **vendored inside it** under `skills/`. You
install **one thing** and everything is there — no separate companion installs,
no path configuration. The master runs each sub-skill from its fixed path inside
the bundle (`skills/cvr-rca/`, `skills/perf-audit/`, `skills/ce-health/`).

**Private repo:** access is gated by a **read-only, repo-scoped fine-grained token** the user
mints once and saves to `~/.ce-rca-token` (the bootstrap snippet does this; see README →
*Getting your access token*). All downloads here authenticate with it. The token is stored only
on the user's machine, never in this repo, and is reused by the skill's auto-update.

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

**Verify the access token (required — the repo is private).** The bootstrap snippet the user
pasted saves a read-only, repo-scoped GitHub token to `~/.ce-rca-token`. Confirm it's present:

```bash
if [ -s ~/.ce-rca-token ]; then chmod 600 ~/.ce-rca-token; echo "token: present"; else echo "token: MISSING"; fi
```

If `MISSING`, **stop** and tell the user: "I need your CE-RCA access token first — save it with
`printf '%s' '<YOUR_TOKEN>' > ~/.ce-rca-token && chmod 600 ~/.ce-rca-token`, then re-run. See
README → *Getting your access token* to mint a fine-grained read-only token." Do not continue
without it. (The same file is reused by the skill's auto-update, so the user pastes the token once.)

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

## Step 2 — Download and install the master (token-authenticated)

The repo is **private**, so download via the GitHub API using the read-only token saved at
`~/.ce-rca-token` (Step 1). The API `zipball` extracts to an SHA-suffixed folder, so auto-detect
it rather than hardcoding the name:

```bash
TOKEN=$(cat ~/.ce-rca-token 2>/dev/null)
curl -sL --max-time 120 -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/satvikdhumaleheadout/ce-rca-skill/zipball/main" -o /tmp/ce-rca-install.zip
rm -rf /tmp/ce-rca-x && mkdir -p /tmp/ce-rca-x
unzip -q /tmp/ce-rca-install.zip -d /tmp/ce-rca-x
SRC=$(find /tmp/ce-rca-x -maxdepth 1 -mindepth 1 -type d | head -1)
rm -rf ~/.ce-rca && mv "$SRC" ~/.ce-rca
rm -rf /tmp/ce-rca-install.zip /tmp/ce-rca-x
```

Then confirm the download succeeded:

```bash
[ -f ~/.ce-rca/SKILL.md ] && echo "ok: $(cat ~/.ce-rca/VERSION)" || echo "FAILED"
```

If it says `FAILED`, the token is missing/invalid/expired — tell the user to re-mint the
fine-grained token (README → "Getting your access token") and re-save it to `~/.ce-rca-token`,
then re-run. Otherwise: "Installed CE-RCA master to `~/.ce-rca/`."

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
