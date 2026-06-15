#!/usr/bin/env python3
"""
USAGE: python3 drive_sync.py --run-dir "<run_dir>" \
                            [--parent-folder-id <id>] [--max-zip-mb 8]

Syncs a finished CE-RCA run to the shared central Google Drive folder using
Application Default Credentials (ADC) — i.e. the gcloud auth the user already has.
This is a FIRST-PARTY replacement for the old Step-4g upload sub-agent: a named CLI
doing a normal authenticated upload with the user's own credentials, so it is not
the "agent reads local files and exfiltrates to an unverified endpoint" shape that
a safety classifier (rightly) blocks. No base64 ever enters a model context window.

What it does (mirrors the prior guarantees, additive / create-only):
  1. Creates a per-run subfolder  <run-dir basename>-<6-hex hash>  under the central
     folder (random suffix dedups concurrent identical runs; carries no PII).
  2. Uploads report.html (kept as a browsable HTML file, not converted to a Google Doc).
  3. Zips the whole run dir (parent-relative → one clean top folder) and uploads the zip.
     Size guard: if the zip exceeds --max-zip-mb, it is re-zipped excluding the heavy
     data/stage*.json raw dumps (transcripts / findings / summary are always kept).

It NEVER updates or deletes an existing Drive file — every call creates new objects.

Prints the per-run folder URL + ids to stdout on success. On ANY failure it exits
non-zero with a message on stderr so the orchestrator can log
"Drive sync unavailable — skipped" and continue — Drive sync is additive, never a blocker.

One-time setup (per user — see INSTALL.md). The Drive scope must be granted at LOGIN
time (passing scopes= here does NOT re-scope already-authorized gcloud user creds):
    pip3 install google-api-python-client google-auth
    gcloud auth application-default login \
        --scopes=https://www.googleapis.com/auth/cloud-platform,\
https://www.googleapis.com/auth/spreadsheets.readonly,\
https://www.googleapis.com/auth/drive.file

The minimal `drive.file` scope only grants access to files THIS app creates — never
the user's wider Drive — which is both safer and sufficient for create-subfolder + upload.

Requires MCP server: none (pure Google Drive API v3 via ADC).
"""
import argparse
import os
import secrets
import subprocess
import sys
import tempfile

# The shared central CE-RCA archive folder. Re-point the sync by changing this
# (and the SKILL.md Step 4g constant) to another folder's id.
DEFAULT_PARENT_FOLDER_ID = "1nernSzAN2mZ531wEdh95eeNL2RV5oq30"

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]


def _err(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 1


def _zip_run_dir(run_dir: str, max_bytes: int) -> tuple[str, bool]:
    """Zip the run dir parent-relative. Returns (zip_path, stage_dumps_excluded)."""
    parent = os.path.dirname(os.path.abspath(run_dir.rstrip("/")))
    name = os.path.basename(os.path.abspath(run_dir.rstrip("/")))
    zip_path = os.path.join(tempfile.gettempdir(), f"{name}.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)

    subprocess.run(["zip", "-r", "-q", zip_path, name], cwd=parent, check=True)
    excluded = False
    if os.path.getsize(zip_path) > max_bytes:
        os.remove(zip_path)
        subprocess.run(
            ["zip", "-r", "-q", zip_path, name, "-x", f"{name}/data/stage*.json"],
            cwd=parent, check=True,
        )
        excluded = True
    return zip_path, excluded


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync a CE-RCA run to central Drive via ADC.")
    ap.add_argument("--run-dir", help="Absolute path to the finished run dir (full-run sync).")
    ap.add_argument("--parent-folder-id", default=DEFAULT_PARENT_FOLDER_ID,
                    help="Central Drive folder id to upload into (full-run mode).")
    ap.add_argument("--max-zip-mb", type=float, default=8.0,
                    help="Zip size cap (MB); above this, data/stage*.json is excluded. Default 8.")
    # Single-file mode (e.g. uploading feedback.md into an existing per-run folder).
    ap.add_argument("--file", help="Single file to upload (use with --into-folder-id).")
    ap.add_argument("--into-folder-id", help="Existing Drive folder id to upload --file into.")
    args = ap.parse_args()

    # ---- Single-file mode -------------------------------------------------
    if args.file or args.into_folder_id:
        if not (args.file and args.into_folder_id):
            return _err("single-file mode needs both --file and --into-folder-id")
        path = os.path.abspath(args.file)
        if not os.path.isfile(path):
            return _err(f"file not found: {path}")
        try:
            import google.auth
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError as e:
            return _err(f"missing dependency ({e}). Run: pip3 install "
                        "google-api-python-client google-auth")
        try:
            creds, _ = google.auth.default(scopes=SCOPES)
            svc = build("drive", "v3", credentials=creds, cache_discovery=False)
            mime = "text/markdown" if path.endswith(".md") else "application/octet-stream"
            f = svc.files().create(
                body={"name": os.path.basename(path), "parents": [args.into_folder_id]},
                media_body=MediaFileUpload(path, mimetype=mime, resumable=False),
                fields="id",
                supportsAllDrives=True,
            ).execute()
        except Exception as e:  # noqa: BLE001
            return _err(f"Drive upload failed: {e}")
        print(f"uploaded_file_id={f['id']}")
        return 0

    # ---- Full-run mode ----------------------------------------------------
    if not args.run_dir:
        return _err("provide --run-dir (full-run sync) or --file + --into-folder-id")
    run_dir = os.path.abspath(args.run_dir.rstrip("/"))
    if not os.path.isdir(run_dir):
        return _err(f"run dir not found: {run_dir}")
    report = os.path.join(run_dir, "report.html")
    if not os.path.isfile(report):
        return _err(f"report.html not found in run dir: {report}")

    try:
        import google.auth
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as e:
        return _err(f"missing dependency ({e}). Run: pip3 install "
                    "google-api-python-client google-auth")

    try:
        creds, _ = google.auth.default(scopes=SCOPES)
        svc = build("drive", "v3", credentials=creds, cache_discovery=False)

        # 1. Per-run subfolder (random 6-hex suffix → dedups concurrent identical runs).
        run_name = f"{os.path.basename(run_dir)}-{secrets.token_hex(3)}"
        folder = svc.files().create(
            body={
                "name": run_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [args.parent_folder_id],
            },
            fields="id",
            supportsAllDrives=True,
        ).execute()
        drive_run_id = folder["id"]

        # 2. report.html — kept browsable (no Google-Doc conversion).
        svc.files().create(
            body={"name": "report.html", "parents": [drive_run_id]},
            media_body=MediaFileUpload(report, mimetype="text/html", resumable=False),
            fields="id",
            supportsAllDrives=True,
        ).execute()

        # 3. Zip of the whole run, with the size guard.
        zip_path, excluded = _zip_run_dir(run_dir, int(args.max_zip_mb * 1024 * 1024))
        svc.files().create(
            body={"name": os.path.basename(zip_path), "parents": [drive_run_id]},
            media_body=MediaFileUpload(zip_path, mimetype="application/zip", resumable=True),
            fields="id",
            supportsAllDrives=True,
        ).execute()
        zip_bytes = os.path.getsize(zip_path)

    except subprocess.CalledProcessError as e:
        return _err(f"zip failed: {e}")
    except Exception as e:  # noqa: BLE001 — any API/auth failure → caller logs + skips
        msg = str(e)
        hint = ""
        low = msg.lower()
        if "403" in msg or "insufficient" in low or "permission" in low or "scope" in low:
            hint = ("  (Likely a missing Drive scope — re-run: gcloud auth "
                    "application-default login --scopes=...,"
                    "https://www.googleapis.com/auth/drive.file)")
        return _err(f"Drive sync failed: {msg}{hint}")

    view_url = f"https://drive.google.com/drive/folders/{drive_run_id}"
    print(f"DRIVE_RUN_ID={drive_run_id}")
    print(f"folder_url={view_url}")
    print(f"zip_bytes={zip_bytes}")
    print(f"stage_dumps_excluded={'yes' if excluded else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
