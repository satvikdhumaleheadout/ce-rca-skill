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
have_deps()   { python3 -c "import googleapiclient, google.auth" >/dev/null 2>&1; }
bq_ok()       { command -v bq >/dev/null 2>&1 && \
                bq query --use_legacy_sql=false --project_id="$PROJECT" --format=none 'SELECT 1' \
                  </dev/null >/dev/null 2>&1; }
drive_ok()    { python3 "$SCRIPT_DIR/drive_sync.py" --recover --run-name "__onboarding_check__" \
                  >/dev/null 2>&1; }
adc_ok()      { gcloud auth application-default print-access-token >/dev/null 2>&1; }

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

# ── 2. Python deps — only if missing ──────────────────────────────
if have_deps; then
  ok "Python deps present"
else
  say "→ Installing Python deps (google-api-python-client, google-auth)…"
  pip3 install --quiet google-api-python-client google-auth \
    && ok "Python deps installed" \
    || warn "pip install failed — run: pip3 install google-api-python-client google-auth"
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

# ── 5. Re-verify and report ───────────────────────────────────────
say "→ Verifying…"
if bq_ok; then ok "BigQuery reachable — CE-RCA can run."
else fail "BigQuery still failing — you likely lack access to '$PROJECT'. Request it, then re-run."; fi
if drive_ok; then ok "Drive reachable — runs will archive to the team Shared Drive."
else warn "Drive still failing — enable the Drive API on the project, or re-run and grant Drive at sign-in. (BigQuery still works; Drive archival just skips.)"; fi

say "──────────────────────────────────────────────────────────────"
say "  Done. Open Claude Code and run, e.g.:  /ce-rca 243"
say "──────────────────────────────────────────────────────────────"
