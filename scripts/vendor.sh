#!/usr/bin/env bash
#
# vendor.sh — re-sync the vendored sub-skills under ce-rca/skills/ and re-apply
# the CE Health standalone patch. Run this whenever a sub-skill changes upstream;
# then commit the refreshed skills/ tree.
#
# Why this exists: the CE-RCA bundle is self-contained — it ships COPIES of
# cvr-rca, perf-audit, and ce-health under skills/ at fixed paths, so the master
# never has to hunt for them at runtime. Copies are simple but don't auto-update;
# this script is the deliberate, one-command re-sync (the alternative — git
# submodules / live links — was rejected for simplicity).
#
# Sources are configurable via env vars (defaults = the local dev checkouts).
# For distribution, point these at fresh `git clone`s of each skill's repo.
#
# Usage:
#   bash scripts/vendor.sh
#   CE_HEALTH_SRC=/path/to/ce-health bash scripts/vendor.sh
#
set -euo pipefail

# ── SAFETY GUARD (2026-06-10) ─────────────────────────────────────────────────
# ce-rca/skills/ is now the CANONICAL source of truth for edits. Local changes
# (metric-naming consistency, Omni reconciliation, etc.) live in the vendored
# copies here and are NOT present in the upstream source dirs — a re-vendor would
# OVERWRITE them. This guard refuses to run unless explicitly forced. Only force
# AFTER you've backported the bundle's edits upstream so nothing is lost.
if [ "${VENDOR_FORCE:-}" != "1" ]; then
  echo "vendor.sh is DISABLED: ce-rca/skills/ is the canonical source of truth." >&2
  echo "A re-vendor would overwrite local edits that aren't upstream." >&2
  echo "If you really mean to (upstream already in sync): VENDOR_FORCE=1 bash scripts/vendor.sh" >&2
  exit 1
fi

BUNDLE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$BUNDLE_DIR/skills"

# Canonical sources (override via env). Defaults are the local dev folders.
CVR_RCA_SRC="${CVR_RCA_SRC:-$HOME/Documents/RCA skill/cvr-rca}"
PERF_AUDIT_SRC="${PERF_AUDIT_SRC:-$HOME/Documents/perf-audit-skill}"
CE_HEALTH_SRC="${CE_HEALTH_SRC:-$HOME/Documents/ce-health-skill-main}"

RSYNC_EXCLUDES=(--exclude='.git' --exclude='__pycache__' --exclude='.DS_Store' \
                --exclude='tree/' --exclude='mmp collections/')

vendor_one () {
  local name="$1" src="$2"
  if [ ! -d "$src" ]; then
    echo "  !! source for $name not found: $src — skipping (set ${name^^}_SRC)"
    return 1
  fi
  echo "  • $name  <-  $src"
  rm -rf "${SKILLS_DIR:?}/$name"
  rsync -a "${RSYNC_EXCLUDES[@]}" "$src/" "$SKILLS_DIR/$name/"
}

mkdir -p "$SKILLS_DIR"
echo "Re-vendoring sub-skills into $SKILLS_DIR ..."
vendor_one cvr-rca   "$CVR_RCA_SRC"
vendor_one perf-audit "$PERF_AUDIT_SRC"
vendor_one ce-health "$CE_HEALTH_SRC"

# ── Re-apply the CE Health standalone patch ───────────────────────────────────
# ce_health.py was written for the monorepo layout (engine at
# scripts/perf_audit_engine_v6/, _repo_root = parent dir). In the standalone
# bundle the engine sits at ./engine/ beside ce_health.py. These 3 deterministic
# replacements make it run from its own folder with no shim and no special CWD.
# If upstream ever changes these exact lines, the sed becomes a no-op and CE
# Health will fail to import — that's the signal to revisit this patch.
CEH="$SKILLS_DIR/ce-health/ce_health.py"
if [ -f "$CEH" ]; then
  echo "Patching CE Health for standalone use ..."
  sed -i '' \
    -e 's|_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))|_repo_root = os.path.dirname(os.path.abspath(__file__))|' \
    -e 's|from scripts.perf_audit_engine_v6.sources.bq import|from engine.sources.bq import|' \
    -e 's|from scripts.perf_audit_engine_v6.render.audit_skeleton import|from engine.render.audit_skeleton import|' \
    "$CEH"
  # Verify it imports cleanly from an arbitrary CWD (no shim, no PYTHONPATH).
  if (cd /tmp && python3 "$CEH" --help >/dev/null 2>&1); then
    echo "  ✓ CE Health runs standalone"
  else
    echo "  !! CE Health still fails to import after patch — inspect $CEH" >&2
    exit 1
  fi
fi

echo "Done. Review 'git status' under skills/ and commit the refreshed tree."
