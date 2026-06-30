#!/usr/bin/env bash
#
# CE-RCA one-time onboarding — makes a machine ready to run CE-RCA.
# Run it in a normal Terminal, OR paste the setup prompt from INSTALL.md into Claude Code
# and let it run this for you. It opens a browser for Google sign-in.
#
#   bash ~/.ce-rca/scripts/onboarding.sh
#
# CONDITIONAL + IDEMPOTENT: it checks what's already working and only fixes what's missing.
# If you're already set up (BigQuery + Drive + ADC all reachable), it does NOTHING and exits
# immediately — no browser, no re-login. Safe to run (or re-run) any time.
#
# It can set up, only as needed:
#   1. The Google Cloud SDK (gcloud + bq) — installs it only if missing.
#   2. Python deps for the Drive/Sheets uploaders — installs only if missing.
#   3a. Account sign-in (`gcloud auth login --enable-gdrive-access`) — only if bq OR Drive is
#       failing. Powers the bq CLI AND Drive uploads (drive_sync.py uses this account token,
#       which avoids ADC's quota-project/serviceusage requirement).
#   3b. ADC sign-in — only if ADC isn't already configured. Powers the Python BigQuery client
#       + optional Sheet ingestion.
#   4. Project + quota project (cheap, idempotent).
#   5. Re-verifies BigQuery AND Drive — tells you exactly what to fix if either is still off.
#
set -uo pipefail

PROJECT="${CE_RCA_PROJECT:-headout-analytics}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCOPES="openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive.file"

say()  { printf '%s\n' "$*"; }
ok()   { printf '✓ %s\n' "$*"; }
warn() { printf '⚠️  %s\n' "$*"; }
fail() { printf '❌ %s\n' "$*"; }

# ── State detectors (each is quiet; true = already working) ───────
have_gcloud() { command -v gcloud >/dev/null 2>&1; }
# Engine deps include google-cloud-bigquery (CE Health imports google.cloud.bigquery).
have_deps()   { python3 -c "import googleapiclient, google.auth, google.cloud.bigquery" >/dev/null 2>&1; }
bq_ok()       { command -v bq >/dev/null 2>&1 && \
                bq query --use_legacy_sql=false --project_id="$PROJECT" --format=none 'SELECT 1' \
                  </dev/null >/dev/null 2>&1; }
drive_ok()    { python3 "$SCRIPT_DIR/drive_sync.py" --recover --run-name "__onboarding_check__" \
                  >/dev/null 2>&1; }
adc_ok()      { gcloud auth application-default print-access-token >/dev/null 2>&1; }

# ── Python self-heal helpers ──────────────────────────────────────
# Recent gcloud needs Python ≥3.11; macOS often defaults python3 to 3.9, which makes
# gcloud/bq fail. These find or install a compatible interpreter and point gcloud at it
# AUTOMATICALLY — the user is never asked to set an env var or re-run anything.
py_ver_ok() { "$1" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,11) else 1)' >/dev/null 2>&1; }

pick_python() {  # echo the path of the first Python ≥3.11 found; nothing if none
  local c root
  if [ -n "${CLOUDSDK_PYTHON:-}" ] && py_ver_ok "$CLOUDSDK_PYTHON"; then echo "$CLOUDSDK_PYTHON"; return; fi
  for c in python3.14 python3.13 python3.12 python3.11; do
    if command -v "$c" >/dev/null 2>&1 && py_ver_ok "$(command -v "$c")"; then command -v "$c"; return; fi
  done
  for c in /opt/homebrew/bin/python3.14 /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 \
           /usr/local/bin/python3.14 /usr/local/bin/python3.13 /usr/local/bin/python3.12 /usr/local/bin/python3.11; do
    if [ -x "$c" ] && py_ver_ok "$c"; then echo "$c"; return; fi
  done
  if command -v pyenv >/dev/null 2>&1; then
    root="$(pyenv root 2>/dev/null)"
    for c in "$root"/versions/3.1[1-9]*/bin/python3; do
      [ -x "$c" ] && py_ver_ok "$c" && { echo "$c"; return; }
    done
  fi
  for c in "$HOME"/google-cloud-sdk/platform/bundledpython*/bin/python3; do
    [ -x "$c" ] && py_ver_ok "$c" && { echo "$c"; return; }
  done
}

# Append a line to the user's shell rc files once (idempotent) so a fix survives into
# future shells (Claude Code's Bash tool starts shells from the user's profile).
persist_line() {
  local line="$1" rc
  for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
    { [ -e "$rc" ] || touch "$rc" 2>/dev/null; } || continue
    grep -qF "$line" "$rc" 2>/dev/null || printf '\n# added by CE-RCA onboarding\n%s\n' "$line" >> "$rc"
  done
}

# Make gcloud start (needs Python ≥3.11): find one → else brew install → else gcloud's
# bundled Python; set CLOUDSDK_PYTHON for this run AND persist it; re-check. Returns 1
# only if no compatible Python could be found or installed.
ensure_gcloud_python() {
  gcloud version >/dev/null 2>&1 && return 0
  say "→ gcloud needs Python ≥3.11 (default python3 is older). Resolving automatically…"
  local py; py="$(pick_python)"
  if [ -z "$py" ] && [ "$(uname -s)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    say "→ Installing Python 3.12 via Homebrew…"; brew install python@3.12 >/dev/null 2>&1 || true
    py="$(pick_python)"
  fi
  if [ -z "$py" ]; then
    say "→ Installing gcloud's bundled Python…"
    [ -f /tmp/gcloud_install.sh ] || curl -sSL https://sdk.cloud.google.com -o /tmp/gcloud_install.sh 2>/dev/null || true
    [ -f /tmp/gcloud_install.sh ] && bash /tmp/gcloud_install.sh --disable-prompts --install-dir="$HOME" >/dev/null 2>&1 || true
    py="$(pick_python)"
  fi
  if [ -n "$py" ]; then
    export CLOUDSDK_PYTHON="$py"
    persist_line "export CLOUDSDK_PYTHON=\"$py\""
    printf 'PYTHON_FIXED=%s\n' "$py"
    gcloud version >/dev/null 2>&1 && { ok "gcloud now runs on Python ≥3.11 ($py)"; return 0; }
  fi
  return 1
}

# Install the engine's Python deps, PEP 668-safe (newer Python/Homebrew blocks plain pip).
install_deps() {
  local pkgs="google-api-python-client google-auth google-cloud-bigquery"
  python3 -m pip install --quiet $pkgs >/dev/null 2>&1 && return 0
  python3 -m pip install --quiet --user $pkgs >/dev/null 2>&1 && return 0
  python3 -m pip install --quiet --break-system-packages $pkgs >/dev/null 2>&1 && return 0
  return 1
}

say "──────────────────────────────────────────────────────────────"
say "  CE-RCA onboarding (only fixes what's missing)"
say "──────────────────────────────────────────────────────────────"

# ── 0. Fast path — already fully set up? Do nothing. ──────────────
if have_gcloud && have_deps && bq_ok && drive_ok && adc_ok; then
  ok "Already set up — BigQuery + Drive both reachable. Nothing to do."
  say "  (Re-run any time; it stays a no-op until something needs fixing.)"
  exit 0
fi
say "Some setup is needed — I'll only do the missing pieces (a browser may open for sign-in)."

# ── 1. Google Cloud SDK (gcloud + bq) — only if missing ───────────
if have_gcloud; then
  ok "Google Cloud SDK present: $(command -v gcloud)"
else
  say "→ Installing the Google Cloud SDK (gcloud + bq)…"
  if [ "$(uname -s)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    brew install --cask google-cloud-sdk || true
  fi
  if ! have_gcloud; then
    curl -sSL https://sdk.cloud.google.com -o /tmp/gcloud_install.sh \
      && bash /tmp/gcloud_install.sh --disable-prompts --install-dir="$HOME" >/dev/null 2>&1 || true
    [ -f "$HOME/google-cloud-sdk/path.bash.inc" ] && . "$HOME/google-cloud-sdk/path.bash.inc"
    export PATH="$HOME/google-cloud-sdk/bin:$PATH"
  fi
  if have_gcloud; then
    ok "Installed: $(command -v gcloud)"
  else
    fail "Could not install gcloud automatically. Install it once, then re-run:"
    say  "      macOS:  brew install --cask google-cloud-sdk"
    say  "      any OS: https://cloud.google.com/sdk/docs/install"
    exit 1
  fi
fi

# gcloud is present — make sure it can actually START (it needs Python ≥3.11). This
# self-heals the common "gcloud requires Python 3.x" failure without asking the user.
ensure_gcloud_python || warn "gcloud still can't start — install Python ≥3.11 (e.g. 'brew install python@3.12') and re-run."
# Persist the SDK PATH for future shells when installed under \$HOME (no-admin install).
[ -d "$HOME/google-cloud-sdk/bin" ] && persist_line 'export PATH="$HOME/google-cloud-sdk/bin:$PATH"'

# ── 2. Python deps (incl. google-cloud-bigquery for the CE Health engine) ──
if have_deps; then
  ok "Python deps present"
else
  say "→ Installing Python deps (google-api-python-client, google-auth, google-cloud-bigquery)…"
  if install_deps && have_deps; then
    ok "Python deps installed"
  else
    warn "Could not install Python deps automatically — run: python3 -m pip install --user google-api-python-client google-auth google-cloud-bigquery"
  fi
fi

# ── 3a. Account sign-in (bq CLI + Drive) — only if bq OR Drive failing ──
if bq_ok && drive_ok; then
  ok "BigQuery + Drive already authorized (skipping account sign-in)"
else
  say "→ Signing in for BigQuery + Drive (a browser window opens — sign in + Allow)…"
  gcloud auth login --enable-gdrive-access \
    && ok "Account sign-in complete (bq CLI + Drive)" \
    || warn "Account sign-in didn't complete — re-run and finish the browser sign-in."
fi

# ── 3b. ADC sign-in (Python BigQuery client + Sheets) — only if missing ──
if adc_ok; then
  ok "Application Default Credentials already set up (skipping)"
else
  say "→ Authorizing application access (ADC) for the Python BigQuery client + Sheets…"
  gcloud auth application-default login --scopes="$SCOPES" \
    && ok "ADC authorization complete" \
    || warn "ADC authorization didn't complete — re-run and finish the browser sign-in."
fi

# ── 4. Project + quota project (cheap, idempotent) ────────────────
gcloud config set project "$PROJECT" >/dev/null 2>&1 || true
gcloud auth application-default set-quota-project "$PROJECT" >/dev/null 2>&1 || true

# ── 5. Re-verify and report (machine-readable status lines for Claude) ────
say "→ Verifying…"
if bq_ok; then ok "BigQuery reachable — CE-RCA can run."; echo "BQ_OK"
else fail "BigQuery still failing — you likely lack access to '$PROJECT'. Request access, then re-run."; echo "NEEDS_ACCESS"; fi
if have_deps; then ok "Python engine deps present (incl. google-cloud-bigquery)."; echo "DEPS_OK"
else warn "Python engine deps missing — CE Health may fail to import google.cloud.bigquery."; fi
if drive_ok; then ok "Drive reachable — runs will archive to the team Shared Drive."
else warn "Drive still failing — re-run and grant Drive at sign-in. (BigQuery still works; Drive archival just skips.)"; fi

say "──────────────────────────────────────────────────────────────"
say "  Done. Open Claude Code and run, e.g.:  /ce-rca 243"
say "──────────────────────────────────────────────────────────────"
