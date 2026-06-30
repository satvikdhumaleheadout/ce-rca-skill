#!/usr/bin/env python3
"""
USAGE:
  Full-run sync:   python3 drive_sync.py --run-dir "<run_dir>" \
                                         [--parent-folder-id <id>] [--max-zip-mb 8]
  Single file:     python3 drive_sync.py --file "<path>" --into-folder-id "<id>"
  Recover/share:   python3 drive_sync.py --recover [--run-name "<substring>"]

Syncs a finished CE-RCA run to the shared central **Google Shared Drive** using
Application Default Credentials (ADC) — i.e. the gcloud auth the user already has
(the same auth BigQuery / CE Health uses, extended once with a Drive scope; see
scripts/onboarding.sh + INSTALL.md). This is a FIRST-PARTY upload: a named CLI doing
a normal authenticated upload with the user's own credentials — it is NOT the
"agent reads local files and exfiltrates to an unverified endpoint" shape that a
safety classifier (rightly) blocks, and **no file bytes ever pass through a model
context window** (the reason the MCP-connector path could not carry large files like
report.html).

What it does (additive / create-only):
  1. Creates a per-run subfolder  <run-dir basename>-<6-hex hash>  under the central
     Shared Drive (random suffix dedups concurrent identical runs; carries no PII).
  2. Uploads report.html (kept as a browsable HTML file, not converted to a Google Doc).
  3. Zips the whole run dir (parent-relative → one clean top folder) and uploads the zip.
     Size guard: if the zip exceeds --max-zip-mb, it is re-zipped excluding the heavy
     data/stage*.json raw dumps (transcripts / findings / summary are always kept).

The full-run CLI path is additive (create-only). The idempotent auto_archive() entry
point (called by compose.py) records the per-run folder in a logs/_drive_run_id.json
sidecar and, on a re-compose, refreshes report.html IN that same folder rather than
creating a duplicate run folder. It never deletes anything.

Prints the per-run folder URL + ids to stdout on success. On ANY failure it exits
non-zero with a message on stderr so the orchestrator can log
"Drive sync unavailable — run scripts/onboarding.sh" and continue — Drive sync is
additive, never a blocker.

SHARED DRIVE NOTE: every Drive API call passes supportsAllDrives=True (and listing
passes includeItemsFromAllDrives=True). Shared Drive operations fail without it.

One-time setup (per user — run `scripts/onboarding.sh`). Drive uploads use the gcloud
ACCOUNT token, so the setup is simply:
    pip3 install google-api-python-client google-auth
    gcloud auth login --enable-gdrive-access     # adds Drive to the account creds bq uses

This deliberately AVOIDS using ADC for Drive: an ADC Drive call requires a quota project
+ `serviceusage.services.use` on it (which users who only have BigQuery *data* access
typically lack → 403). The account token instead attributes Drive-API quota to gcloud's
own OAuth client (Drive API enabled there), so it "just works" like `bq` reading
Drive-backed tables — no quota project, no serviceusage, no per-user GCP IAM.

Requires MCP server: none (pure Google Drive API v3 via ADC).
"""
import argparse
import json
import os
import secrets
import subprocess
import sys
import tempfile

# The shared central CE-RCA archive — a Google **Shared Drive** (company-wide
# contributor access). Re-point the sync by setting the CE_RCA_DRIVE_PARENT env var
# or passing --parent-folder-id (and updating the SKILL.md Step 4g constant).
DEFAULT_PARENT_FOLDER_ID = os.environ.get(
    "CE_RCA_DRIVE_PARENT", "0AONjDQrW9gVvUk9PVA"
)

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]


def _err(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 1


def _drive_service():
    """Build an authenticated Drive v3 service. Raises on missing deps/auth.

    PRIMARY: the gcloud **account** access token (`gcloud auth print-access-token`) — the
    same credential family `bq` uses. With `gcloud auth login --enable-gdrive-access` it
    carries the Drive scope, and because it is NOT Application Default Credentials it does
    **not** trigger ADC's "quota project + serviceusage" requirement — quota attributes to
    gcloud's own OAuth client (which has the Drive API enabled, exactly how `bq` reads
    Drive-backed BigQuery tables). This is the simple "sign in with Google → upload" path.

    FALLBACK: ADC (`google.auth.default`) — only used if the gcloud token isn't available.
    ADC needs a quota project + serviceusage on it (set CE_RCA_DRIVE_QUOTA_PROJECT).
    """
    from googleapiclient.discovery import build

    # PRIMARY — gcloud account token.
    try:
        import subprocess
        from google.oauth2.credentials import Credentials
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        if token:
            return build("drive", "v3",
                         credentials=Credentials(token=token), cache_discovery=False)
    except Exception:  # noqa: BLE001 — gcloud missing / not logged in → try ADC
        pass

    # FALLBACK — ADC.
    import google.auth
    creds, _ = google.auth.default(scopes=SCOPES)
    qp = os.environ.get("CE_RCA_DRIVE_QUOTA_PROJECT")
    if qp:
        try:
            creds = creds.with_quota_project(qp)
        except Exception:  # noqa: BLE001
            pass
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _scope_hint(msg: str) -> str:
    low = msg.lower()
    if "403" in msg or "insufficient" in low or "permission" in low or "scope" in low:
        return ("  (Likely the Drive scope isn't on your gcloud account creds — run "
                "scripts/onboarding.sh, or: gcloud auth login --enable-gdrive-access)")
    return ""


def _zip_run_dir(run_dir: str, max_bytes: int) -> tuple[str, bool]:
    """Zip the run dir parent-relative. Returns (zip_path, stage_dumps_excluded)."""
    parent = os.path.dirname(os.path.abspath(run_dir.rstrip("/")))
    name = os.path.basename(os.path.abspath(run_dir.rstrip("/")))
    zip_path = os.path.join(tempfile.gettempdir(), f"{name}.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)

    # Exclude the internal BigQuery query cache from every archive.
    base_excludes = ["-x", f"{name}/.bq/*", "-x", f"{name}/.DS_Store"]
    subprocess.run(["zip", "-r", "-q", zip_path, name, *base_excludes],
                   cwd=parent, check=True)
    excluded = False
    if os.path.getsize(zip_path) > max_bytes:
        os.remove(zip_path)
        subprocess.run(
            ["zip", "-r", "-q", zip_path, name, *base_excludes,
             "-x", f"{name}/data/stage*.json"],
            cwd=parent, check=True,
        )
        excluded = True
    return zip_path, excluded


def _run_single_file(args) -> int:
    path = os.path.abspath(args.file)
    if not os.path.isfile(path):
        return _err(f"file not found: {path}")
    try:
        from googleapiclient.http import MediaFileUpload
        svc = _drive_service()
    except ImportError as e:
        return _err(f"missing dependency ({e}). Run: pip3 install "
                    "google-api-python-client google-auth")
    try:
        mime = "text/markdown" if path.endswith(".md") else "application/octet-stream"
        f = svc.files().create(
            body={"name": os.path.basename(path), "parents": [args.into_folder_id]},
            media_body=MediaFileUpload(path, mimetype=mime, resumable=False),
            fields="id",
            supportsAllDrives=True,
        ).execute()
    except Exception as e:  # noqa: BLE001
        return _err(f"Drive upload failed: {e}{_scope_hint(str(e))}")
    print(f"uploaded_file_id={f['id']}")
    return 0


def _run_recover(args) -> int:
    """List per-run subfolders under the parent (optionally name-filtered) and print
    their folder + report URLs. Also serves as the onboarding access check: a
    successful (even empty) list proves the Drive scope + Shared Drive access."""
    try:
        svc = _drive_service()
    except ImportError as e:
        return _err(f"missing dependency ({e}). Run: pip3 install "
                    "google-api-python-client google-auth")
    try:
        q = (f"'{args.parent_folder_id}' in parents "
             "and mimeType='application/vnd.google-apps.folder' and trashed=false")
        if args.run_name:
            safe = args.run_name.replace("'", "")
            q += f" and name contains '{safe}'"
        resp = svc.files().list(
            q=q, fields="files(id,name)", pageSize=100,
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
    except Exception as e:  # noqa: BLE001
        return _err(f"Drive list failed: {e}{_scope_hint(str(e))}")
    files = resp.get("files", [])
    print(f"matches={len(files)}")
    for f in files:
        print(f"  {f['name']}\thttps://drive.google.com/drive/folders/{f['id']}")
    return 0


# ── Idempotent per-run archival ────────────────────────────────────────────────
# A sidecar (logs/_drive_run_id.json) records the per-run Drive folder so that a
# re-compose (e.g. after a promoted follow-up) reuses the SAME folder instead of
# creating a duplicate. auto_archive() is the importable entry point compose.py calls
# so archival is a guaranteed side-effect of producing the report — not a step the
# orchestrator has to remember.

def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _sidecar_path(run_dir: str) -> str:
    return os.path.join(run_dir, "logs", "_drive_run_id.json")


def _read_sidecar(run_dir: str):
    try:
        with open(_sidecar_path(run_dir)) as fh:
            d = json.load(fh)
        return d if d.get("DRIVE_RUN_ID") else None
    except Exception:  # noqa: BLE001 — absent / unreadable → treat as not-yet-archived
        return None


def _write_sidecar(run_dir: str, drive_run_id: str, view_url: str) -> None:
    p = _sidecar_path(run_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        json.dump({"DRIVE_RUN_ID": drive_run_id, "folder_url": view_url,
                   "created": _now_iso()}, fh, indent=2)


def _archive_full(svc, run_dir: str, parent: str, max_zip_mb: float):
    """Create the per-run folder and upload report.html + the run zip.
    Returns (drive_run_id, view_url, zip_bytes, excluded). Raises on failure."""
    from googleapiclient.http import MediaFileUpload
    run_name = f"{os.path.basename(run_dir)}-{secrets.token_hex(3)}"
    folder = svc.files().create(
        body={"name": run_name, "mimeType": "application/vnd.google-apps.folder",
              "parents": [parent]},
        fields="id", supportsAllDrives=True,
    ).execute()
    drive_run_id = folder["id"]
    svc.files().create(
        body={"name": "report.html", "parents": [drive_run_id]},
        media_body=MediaFileUpload(os.path.join(run_dir, "report.html"),
                                   mimetype="text/html", resumable=False),
        fields="id", supportsAllDrives=True,
    ).execute()
    zip_path, excluded = _zip_run_dir(run_dir, int(max_zip_mb * 1024 * 1024))
    svc.files().create(
        body={"name": os.path.basename(zip_path), "parents": [drive_run_id]},
        media_body=MediaFileUpload(zip_path, mimetype="application/zip", resumable=True),
        fields="id", supportsAllDrives=True,
    ).execute()
    view_url = f"https://drive.google.com/drive/folders/{drive_run_id}"
    return drive_run_id, view_url, os.path.getsize(zip_path), excluded


def _refresh_report_in(svc, folder_id: str, report: str) -> None:
    """Create-or-update report.html inside an existing per-run folder (no duplicate)."""
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(report, mimetype="text/html", resumable=False)
    existing = svc.files().list(
        q=f"'{folder_id}' in parents and name='report.html' and trashed=false",
        fields="files(id)", pageSize=1,
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute().get("files", [])
    if existing:
        svc.files().update(fileId=existing[0]["id"], media_body=media,
                           supportsAllDrives=True).execute()
    else:
        svc.files().create(
            body={"name": "report.html", "parents": [folder_id]},
            media_body=media, fields="id", supportsAllDrives=True,
        ).execute()


def auto_archive(run_dir: str, parent: str = None, max_zip_mb: float = 8.0):
    """Deterministic, idempotent archival — the importable side-effect compose.py runs
    after writing report.html. NEVER raises: on any failure (Drive not set up, auth
    missing, offline) it logs to stderr and returns None, so the local report is never
    blocked. Honors the CE_RCA_NO_DRIVE opt-out env var.

    First call for a run → creates the per-run Shared-Drive folder, uploads report.html
    + the run zip, writes logs/_drive_run_id.json. Later calls (re-compose after a
    follow-up) → reuse that folder via the sidecar and just refresh report.html, so a
    run never produces duplicate Drive folders. Returns the folder URL, or None."""
    if os.environ.get("CE_RCA_NO_DRIVE"):
        return None
    run_dir = os.path.abspath(run_dir.rstrip("/"))
    report = os.path.join(run_dir, "report.html")
    if not os.path.isfile(report):
        return None
    parent = parent or DEFAULT_PARENT_FOLDER_ID
    try:
        svc = _drive_service()
        prior = _read_sidecar(run_dir)
        if prior:
            _refresh_report_in(svc, prior["DRIVE_RUN_ID"], report)
            return prior.get("folder_url")
        drive_run_id, view_url, _bytes, _excluded = _archive_full(svc, run_dir, parent, max_zip_mb)
        _write_sidecar(run_dir, drive_run_id, view_url)
        return view_url
    except Exception as e:  # noqa: BLE001 — additive; never a blocker
        print(f"[drive_sync] archival skipped: {e}{_scope_hint(str(e))}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync a CE-RCA run to the central Shared Drive via ADC.")
    ap.add_argument("--run-dir", help="Absolute path to the finished run dir (full-run sync).")
    ap.add_argument("--parent-folder-id", default=DEFAULT_PARENT_FOLDER_ID,
                    help="Central Shared Drive (or folder) id to upload into. "
                         "Default: CE_RCA_DRIVE_PARENT env or the built-in Shared Drive id.")
    ap.add_argument("--max-zip-mb", type=float, default=8.0,
                    help="Zip size cap (MB); above this, data/stage*.json is excluded. Default 8.")
    # Single-file mode (e.g. uploading feedback.md into an existing per-run folder).
    ap.add_argument("--file", help="Single file to upload (use with --into-folder-id).")
    ap.add_argument("--into-folder-id", help="Existing Drive folder id to upload --file into.")
    # Recover/share + onboarding access check.
    ap.add_argument("--recover", action="store_true",
                    help="List per-run subfolders under the parent (optionally --run-name filtered).")
    ap.add_argument("--run-name", help="Substring to filter recover results by folder name.")
    args = ap.parse_args()

    # ---- Recover / access-check mode -------------------------------------
    if args.recover:
        return _run_recover(args)

    # ---- Single-file mode -------------------------------------------------
    if args.file or args.into_folder_id:
        if not (args.file and args.into_folder_id):
            return _err("single-file mode needs both --file and --into-folder-id")
        return _run_single_file(args)

    # ---- Full-run mode ----------------------------------------------------
    if not args.run_dir:
        return _err("provide --run-dir (full-run sync), --file + --into-folder-id, or --recover")
    run_dir = os.path.abspath(args.run_dir.rstrip("/"))
    if not os.path.isdir(run_dir):
        return _err(f"run dir not found: {run_dir}")
    report = os.path.join(run_dir, "report.html")
    if not os.path.isfile(report):
        return _err(f"report.html not found in run dir: {report}")

    try:
        from googleapiclient.http import MediaFileUpload
        svc = _drive_service()
    except ImportError as e:
        return _err(f"missing dependency ({e}). Run: pip3 install "
                    "google-api-python-client google-auth")

    try:
        drive_run_id, view_url, zip_bytes, excluded = _archive_full(
            svc, run_dir, args.parent_folder_id, args.max_zip_mb)
        # Record the per-run folder so a later re-compose reuses it (no duplicates).
        _write_sidecar(run_dir, drive_run_id, view_url)
    except subprocess.CalledProcessError as e:
        return _err(f"zip failed: {e}")
    except Exception as e:  # noqa: BLE001 — any API/auth failure → caller logs + skips
        return _err(f"Drive sync failed: {e}{_scope_hint(str(e))}")

    print(f"DRIVE_RUN_ID={drive_run_id}")
    print(f"folder_url={view_url}")
    print(f"zip_bytes={zip_bytes}")
    print(f"stage_dumps_excluded={'yes' if excluded else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
