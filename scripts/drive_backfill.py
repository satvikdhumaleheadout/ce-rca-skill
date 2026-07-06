#!/usr/bin/env python3
"""
drive_backfill.py — sweep local CE-RCA runs and archive any missing from the team
Shared Drive, writing a per-run `reason.md` (why it wasn't archived) into each.

Used by the `/ce-rca-drive-sync` sub-skill (Phase 1). For every run under the runs dir
(default ~/Documents/CE RCA Runs, or $CE_RCA_RUNS_DIR):
  1. Authoritatively check Drive — query the run's folder (a local sidecar may be absent
     on older runs). If found, (re)write the logs/_drive_run_id.json sidecar and skip.
  2. If NOT on Drive and the run has a report.html: infer WHY from logs/_run_log.md
     (the only Drive-relevant artifact — the RCA transcript is about the analysis, not
     Drive), write reason.md, archive via drive_sync.auto_archive(), and upload reason.md
     into the run's Drive folder.
  3. Print a table + write _backfill_summary.md at the runs root.

Deterministic and re-runnable. Never deletes anything. Graceful: if Drive isn't set up it
runs classify-only (reports what it *would* do) and tells you to run scripts/onboarding.sh.

USAGE:  python3 drive_backfill.py [--runs-dir DIR] [--dry-run]
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_sync as ds  # noqa: E402


def _runs_root(cli):
    return (cli or os.environ.get("CE_RCA_RUNS_DIR")
            or os.path.expanduser("~/Documents/CE RCA Runs"))


def _find(run, name):
    for p in (os.path.join(run, name),
              os.path.join(run, "logs", name),
              os.path.join(run, "reports", name)):
        if os.path.isfile(p):
            return p
    return None


def _classify_reason(run):
    """Infer why a run was never archived, from logs/_run_log.md."""
    p = _find(run, "_run_log.md")
    if not p:
        return "unknown", "No _run_log.md found (older run format) — reason indeterminate."
    try:
        log = open(p, errors="ignore").read()
    except Exception as e:  # noqa: BLE001
        return "unknown", f"Couldn't read _run_log.md: {e}"
    lines = [ln.strip() for ln in log.splitlines()
             if "drive" in ln.lower() or "DRIVE_RUN_ID" in ln]
    if not lines:
        return "skipped", "No Drive attempt recorded in _run_log.md — the archival step was skipped."
    joined = " | ".join(lines)
    low = joined.lower()
    if ("drive_run_id" in low) or ("folder" in low and "http" in low):
        return "was-archived", f"_run_log.md shows a prior Drive archive: {joined}"
    if any(w in low for w in ("skip", "block", "unavailable", "error", "fail")):
        return "errored/skipped", f"_run_log.md notes: {joined}"
    return "unclear", f"Drive-related log lines: {joined}"


def _write_reason_md(run, base, status, reason):
    body = (
        "# Drive archival — backfill note\n\n"
        f"- **Run:** `{base}`\n"
        f"- **Checked:** {datetime.now(timezone.utc).isoformat()}\n"
        "- **On Drive before backfill:** no\n"
        f"- **Inferred status:** {status}\n"
        f"- **Evidence:** {reason}\n"
        "- **Action:** backfilled to Drive now\n"
    )
    try:
        with open(os.path.join(run, "reason.md"), "w") as fh:
            fh.write(body)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] couldn't write reason.md in {base}: {e}", file=sys.stderr)


def _upload_file(svc, folder_id, path):
    if not os.path.isfile(path):
        return
    from googleapiclient.http import MediaFileUpload
    svc.files().create(
        body={"name": os.path.basename(path), "parents": [folder_id]},
        media_body=MediaFileUpload(path, mimetype="text/markdown", resumable=False),
        fields="id", supportsAllDrives=True,
    ).execute()


def _summary(root, rows, dry):
    print(f"\n{'RUN':46} STATUS")
    print("-" * 70)
    for base, st, _reason, url in rows:
        print(f"{base:46} {st}{('  ' + url) if url else ''}")
    counts = {}
    for _b, st, _r, _u in rows:
        counts[st] = counts.get(st, 0) + 1
    print("\nSummary:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "(no runs)")
    if dry:
        print("\n(dry-run — no files written; re-run without --dry-run to backfill)")
        return
    hdr = ["# CE-RCA Drive backfill summary",
           f"_generated: {datetime.now(timezone.utc).isoformat()}_", "",
           "| Run | Status | Reason | Drive |", "|---|---|---|---|"]
    for base, st, reason, url in rows:
        hdr.append(f"| {base} | {st} | {reason} | {url} |")
    try:
        with open(os.path.join(root, "_backfill_summary.md"), "w") as fh:
            fh.write("\n".join(hdr) + "\n")
        print(f"\nWrote {os.path.join(root, '_backfill_summary.md')}")
    except Exception as e:  # noqa: BLE001
        print(f"[warn] couldn't write summary: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Backfill CE-RCA runs to the Shared Drive.")
    ap.add_argument("--runs-dir", help="Runs root (default ~/Documents/CE RCA Runs or $CE_RCA_RUNS_DIR).")
    ap.add_argument("--dry-run", action="store_true", help="Classify + report only; upload nothing.")
    a = ap.parse_args()

    root = _runs_root(a.runs_dir)
    if not os.path.isdir(root):
        print(f"runs dir not found: {root}")
        return 1

    svc = None
    if not a.dry_run:
        try:
            svc = ds._drive_service()
        except Exception as e:  # noqa: BLE001
            print(f"[warn] Drive not reachable ({e}). Classify-only mode — run "
                  f"scripts/onboarding.sh, then re-run to upload.")
            a.dry_run = True

    rows = []
    for run in sorted(d.path for d in os.scandir(root) if d.is_dir()):
        base = os.path.basename(run)
        status, reason = _classify_reason(run)

        folder_url = ""
        on_drive = False
        if svc is not None:
            try:
                fid = ds.find_existing_folder(svc, ds.DEFAULT_PARENT_FOLDER_ID, base)
            except Exception:  # noqa: BLE001
                fid = None
            if fid:
                on_drive = True
                folder_url = f"https://drive.google.com/drive/folders/{fid}"
                try:
                    ds._write_sidecar(run, fid, folder_url)
                except Exception:  # noqa: BLE001
                    pass

        if not os.path.isfile(os.path.join(run, "report.html")):
            rows.append((base, "NO-REPORT", "no report.html — nothing to archive", ""))
            continue
        if on_drive:
            rows.append((base, "ALREADY-ON-DRIVE", "already archived", folder_url))
            continue
        if a.dry_run:
            rows.append((base, "WOULD-BACKFILL", reason, ""))
            continue

        _write_reason_md(run, base, status, reason)
        url = ds.auto_archive(run)
        if url:
            try:
                sc = ds._read_sidecar(run)
                if sc:
                    _upload_file(svc, sc["DRIVE_RUN_ID"], os.path.join(run, "reason.md"))
            except Exception:  # noqa: BLE001
                pass
            rows.append((base, "BACKFILLED", reason, url))
        else:
            rows.append((base, "ARCHIVE-FAILED",
                         reason + " (upload failed — run scripts/onboarding.sh)", ""))

    _summary(root, rows, a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
