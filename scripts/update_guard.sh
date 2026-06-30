#!/usr/bin/env bash
#
# CE-RCA bundle update guard — the single "stay on latest" check shared by EVERY
# entry point (the /ce-rca umbrella AND each standalone sub-skill). It updates the
# WHOLE ce-rca bundle in place when behind — never an individual sub-skill — so a
# standalone /cvr-rca, /perf-audit, /ce-context or /ce-health can never run a stale
# bundle. The bundle is self-contained: the only update source is the ce-rca-skill
# repo; sub-skills never point at their own former repos.
#
#   bash "<bundle>/scripts/update_guard.sh" [RUN_DIR]
#
# Self-guarding (safe to call unconditionally as the first step of any skill):
#   - Only the CANONICAL install (~/.ce-rca) is ever rewritten. A dev checkout or
#     any other path is a no-op (so this repo, /Users/.../ce-rca, is never clobbered).
#   - Skips when DISPATCHED by the umbrella — pass the run dir and it detects the
#     umbrella's orchestration.json, or set CE_RCA_NO_UPDATE=1 — because the umbrella
#     already ran this check before dispatching its sub-skills.
#
# Single-line stdout contract for the caller (Claude) to read:
#   UPDATED <old> <new>   — bundle was refreshed; re-read the freshly-installed SKILL.md
#   CURRENT <ver>         — already latest; proceed
#   OFFLINE <ver>         — couldn't reach GitHub (3s timeout); proceed on installed
#   SKIPPED dev           — not the canonical install; proceed untouched
#   SKIPPED dispatched    — running under the umbrella; proceed (umbrella already checked)
#
set -uo pipefail

CANON="$HOME/.ce-rca"
VERSION_URL="https://raw.githubusercontent.com/satvikdhumaleheadout/ce-rca-skill/main/VERSION"
ZIP_URL="https://github.com/satvikdhumaleheadout/ce-rca-skill/archive/refs/heads/main.zip"

# scripts/ lives at the bundle root → bundle = parent of this script's directory.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_DIR="${1:-}"

# Dispatched by the umbrella? It already updated the bundle — skip.
if [ -n "${CE_RCA_NO_UPDATE:-}" ] || { [ -n "$RUN_DIR" ] && [ -f "$RUN_DIR/orchestration.json" ]; }; then
  echo "SKIPPED dispatched"; exit 0
fi

# Only ever rewrite the canonical install.
if [ "$BUNDLE_DIR" != "$CANON" ]; then
  echo "SKIPPED dev"; exit 0
fi

INSTALLED="$(cat "$BUNDLE_DIR/VERSION" 2>/dev/null || echo '0.0.0')"
LATEST="$(curl -s --max-time 3 "$VERSION_URL" 2>/dev/null | tr -d '[:space:]')"
echo "$LATEST" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || { echo "OFFLINE $INSTALLED"; exit 0; }

NEEDS=$(python3 -c "
a='$INSTALLED'.strip(); b='$LATEST'.strip()
pa=[int(x) for x in a.split('.')]; pb=[int(x) for x in b.split('.')]
n=max(len(pa),len(pb)); pa+=[0]*(n-len(pa)); pb+=[0]*(n-len(pb))
print('yes' if pa<pb else 'no')
" 2>/dev/null || echo 'no')

if [ "$NEEDS" != "yes" ]; then echo "CURRENT $INSTALLED"; exit 0; fi

# Stale → re-install the whole bundle in place (run folders under ~/Documents are untouched).
TMP="$(mktemp -d)"
if curl -sL --max-time 60 "$ZIP_URL" -o "$TMP/bundle.zip" 2>/dev/null \
   && unzip -q -o "$TMP/bundle.zip" -d "$TMP" 2>/dev/null \
   && [ -d "$TMP/ce-rca-skill-main" ]; then
  rm -rf "$CANON" && mv "$TMP/ce-rca-skill-main" "$CANON"; rm -rf "$TMP"
  echo "UPDATED $INSTALLED $(cat "$CANON/VERSION" 2>/dev/null || echo "$LATEST")"
else
  rm -rf "$TMP"; echo "OFFLINE $INSTALLED"
fi
