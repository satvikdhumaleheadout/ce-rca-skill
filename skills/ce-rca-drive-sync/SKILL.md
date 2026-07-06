---
name: ce-rca-drive-sync
description: >
  Maintenance utility for CE-RCA runs. Sweeps every local CE-RCA run under
  ~/Documents/CE RCA Runs/, archives any that never reached the team Google Shared
  Drive (writing a reason.md explaining the earlier miss), then walks the analyst
  through giving feedback on past runs one at a time. Run /ce-rca-drive-sync.
disable-model-invocation: true
---

# CE-RCA Drive Sync — backfill runs + collect feedback

An on-demand tidy-up for CE-RCA runs: **(Phase 1)** make sure every past run is on the
team Shared Drive, and **(Phase 2)** collect the analyst's feedback on runs that have none.
Both phases are **idempotent and safe to re-run** — already-synced runs and runs that already
have feedback are skipped. It changes nothing about how RCAs are produced; it only archives
finished runs and captures feedback.

Runs live under `~/Documents/CE RCA Runs/` (override with `$CE_RCA_RUNS_DIR`). This skill is
standalone (never dispatched by the umbrella).

## Before you begin

Set `SKILL_DIR` to the directory this SKILL.md was read from (e.g. `~/.ce-rca/skills/ce-rca-drive-sync`);
the shared scripts live at `$SKILL_DIR/../../scripts/`.

```bash
SKILL_DIR="<absolute dir this SKILL.md was read from>"   # e.g. ~/.ce-rca/skills/ce-rca-drive-sync
```

### Stay on the latest version — do this first

Run the shared bundle guard (canonical `~/.ce-rca` install only; a no-op on dev checkouts):

```bash
bash "$SKILL_DIR/../../scripts/update_guard.sh"
```

- **`UPDATED <old> <new>`** — the bundle was refreshed. Tell the user one line and **re-read
  `~/.ce-rca/skills/ce-rca-drive-sync/SKILL.md`**, continuing from the top.
- **`CURRENT` / `OFFLINE` / `SKIPPED …`** — proceed on the installed version.

---

## Phase 1 — Back-fill runs to the Shared Drive

Preview first (writes nothing), show the user the table, then run it for real:

```bash
python3 "$SKILL_DIR/../../scripts/drive_backfill.py" --dry-run
python3 "$SKILL_DIR/../../scripts/drive_backfill.py"
```

The script sweeps `~/Documents/CE RCA Runs/`; for each run it checks Drive authoritatively,
and for any with a `report.html` not there it writes a `reason.md` (inferred from
`logs/_run_log.md` — skipped vs errored), archives the run (idempotent), uploads `reason.md`
into its Drive folder, and writes `_backfill_summary.md` at the runs root.

Interpret the summary for the user:
- **BACKFILLED** — now on Drive, with a `reason.md` explaining the earlier miss.
- **ALREADY-ON-DRIVE** — was fine (a sidecar is recorded so it's not re-checked next time).
- **NO-REPORT** — a partial/standalone run with no `report.html`; nothing to archive.
- **ARCHIVE-FAILED** — Drive isn't set up on this machine. Tell the user to run
  `bash "$SKILL_DIR/../../scripts/onboarding.sh"` (finish the Google sign-in), then re-run this skill.

If the script prints the classify-only warning (Drive not reachable), relay the same
onboarding instruction and skip Phase 2's uploads (feedback still saves locally).

---

## Phase 2 — Collect feedback, one run at a time

Feedback is what improves the skill. Go through runs that have a `report.html` and **no**
`feedback.md` (check both `<run>/feedback.md` and `<run>/reports/feedback.md`), **newest first**
(by the dates in the folder name), **one at a time** — don't dump them all at once.

1. Tell the user how many there are; they can reply **skip**, **open**, or **stop** anytime.
2. For each run, present a compact **recall card**:
   - **CE + window** (from the folder name);
   - a **one-line headline** — read the `<title>` of `report.html`, or the top finding from
     `reports/findings.md` / the summary — so they remember it without opening;
   - the **report link**: `file://<absolute run path>/report.html` (and offer: say **open** and
     you'll run `open "<absolute run path>/report.html"` to view it in the browser);
   - the **Drive link** if archived.
   Then ask: *"What's your feedback on this run? Reply with anything — even 'looked good' —
   or `skip` / `open` / `stop`."*
3. **On a feedback reply** → append to `<run>/feedback.md` (the detail + a category if obvious +
   timestamp + CE/window), then upload it into the run's Drive folder:
   ```bash
   DRIVE_RUN_ID=$(python3 -c "import json;print(json.load(open('<run>/logs/_drive_run_id.json'))['DRIVE_RUN_ID'])" 2>/dev/null)
   [ -n "$DRIVE_RUN_ID" ] && python3 "$SKILL_DIR/../../scripts/drive_sync.py" --file "<run>/feedback.md" --into-folder-id "$DRIVE_RUN_ID"
   ```
   (No sidecar → keep it local and skip the upload.) Move to the next run.
4. **skip** → next run. **open** → open the report, wait, then ask again. **stop** → summarize
   how many you captured and end.

Keep it light and fast — capture positives too (they're signal), and never force feedback.
