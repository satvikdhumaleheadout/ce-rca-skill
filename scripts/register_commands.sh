#!/usr/bin/env bash
#
# register_commands.sh — the SINGLE source of truth for CE-RCA slash commands.
# Writes every ~/.claude/commands/*.md file (idempotent). Called at install
# (INSTALL.md Step 3), on every bundle update (INSTALL.md § Update, update_guard.sh,
# and the umbrella's in-run update block). Add a NEW command HERE once and it
# propagates to all users on their next install/update — nowhere else to touch.
#
set -uo pipefail
CMD_DIR="$HOME/.claude/commands"
mkdir -p "$CMD_DIR"

cat > "$CMD_DIR/ce-rca.md" << 'CMD'
---
description: CE-level Root Cause Analysis — runs CE Health, CE Context, CVR-RCA + perf-audit, composes one tabbed report.
---

Read the skill file at: ~/.ce-rca/SKILL.md
CMD

cat > "$CMD_DIR/ce-context.md" << 'CMD'
---
description: CE Context — standalone orientation brief for a CE (what it is, known constraints, prior RCAs, Slack). Produces its own report.html.
---

Read the skill file at: ~/.ce-rca/skills/ce-context/SKILL.md and run it STANDALONE for
the CE the user names (resolve the CE, confirm the window, and on render pass
`--standalone` so an openable `report.html` lands in the run dir).
CMD

cat > "$CMD_DIR/cvr-rca.md" << 'CMD'
---
description: CVR-RCA — standalone CVR / funnel root-cause analysis for a CE. Produces its own report.html.
---

Read the skill file at: ~/.ce-rca/skills/cvr-rca/SKILL.md and run it STANDALONE for the
CE the user names (it self-names a run dir and writes its own report.html).
CMD

cat > "$CMD_DIR/perf-audit.md" << 'CMD'
---
description: Perf-Audit — standalone paid performance audit for a CE. Produces its own report.html.
---

Read the skill file at: ~/.ce-rca/skills/perf-audit/SKILL.md and run it STANDALONE for
the CE the user names (after the report markdown is final, render the HTML with
`~/.ce-rca/scripts/render_perf_audit.py --run-dir <run_dir> --standalone` → report.html).
CMD

cat > "$CMD_DIR/ce-health.md" << 'CMD'
---
description: CE Health — standalone CE briefing packet (vitals, channels, funnel, L12M, Shapley). Produces its own report.html.
---

Read the skill file at: ~/.ce-rca/skills/ce-health/SKILL.md and run it STANDALONE for the
CE the user names (write artifacts with the canonical `ce_health_report.{md,json}` names
into a run dir, then `~/.ce-rca/scripts/render_ce_health.py --run-dir <run_dir> --standalone`
→ report.html).
CMD

cat > "$CMD_DIR/ce-rca-drive-sync.md" << 'CMD'
---
description: Sync past CE-RCA runs to the team Google Drive (archive any that were missed, each with a reason) and collect feedback on them one at a time.
---

Read the skill file at: ~/.ce-rca/skills/ce-rca-drive-sync/SKILL.md and run it.
CMD

echo "Registered CE-RCA commands: /ce-rca /ce-context /cvr-rca /perf-audit /ce-health /ce-rca-drive-sync"
