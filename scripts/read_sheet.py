#!/usr/bin/env python3
"""
USAGE: python3 read_sheet.py --url "<sheet URL or ID>" [--range "Tab!A1:Z"] \
                             [--max-rows 200] [--format csv|md]

Reads a Google Sheet via the Sheets API v4 using Application Default Credentials
(ADC) — i.e. the gcloud auth the user already has. Prints the values to stdout
for the calling agent to read and distil. Context-frugal: output is row-capped.

This is the PRIMARY sheet-reading path for the CE-RCA context-ingestion sub-agent
(more robust/scalable than the Drive MCP, which the sub-agent uses only as a
fallback). On any failure this script exits non-zero with a message on stderr so
the caller can fall back.

One-time setup (per user — see INSTALL.md):
    gcloud auth application-default login \
        --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets.readonly
    pip3 install google-api-python-client google-auth

Requires MCP server: none (pure Google API via ADC).
"""
import argparse
import re
import sys


def extract_sheet_id(url_or_id: str) -> str:
    """Accept a full Sheets URL or a bare spreadsheet ID."""
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url_or_id)
    if m:
        return m.group(1)
    # Bare ID (no slashes, reasonable length)
    if re.fullmatch(r"[a-zA-Z0-9-_]{20,}", url_or_id.strip()):
        return url_or_id.strip()
    raise ValueError(f"Could not extract a spreadsheet ID from: {url_or_id!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Read a Google Sheet via ADC.")
    ap.add_argument("--url", required=True, help="Sheet URL or spreadsheet ID")
    ap.add_argument("--range", default=None,
                    help="A1 range incl. tab, e.g. 'Sheet1!A1:Z'. Default: first tab.")
    ap.add_argument("--max-rows", type=int, default=200,
                    help="Cap rows printed (context frugality). Default 200.")
    ap.add_argument("--format", choices=["csv", "md"], default="csv")
    args = ap.parse_args()

    try:
        import google.auth
        from googleapiclient.discovery import build
    except ImportError as e:
        print(f"ERROR: missing dependency ({e}). Run: pip3 install "
              "google-api-python-client google-auth", file=sys.stderr)
        return 2

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    try:
        sheet_id = extract_sheet_id(args.url)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    try:
        creds, _ = google.auth.default(scopes=SCOPES)
        svc = build("sheets", "v4", credentials=creds, cache_discovery=False)

        rng = args.range
        if not rng:
            meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheets = meta.get("sheets", [])
            if not sheets:
                print("ERROR: spreadsheet has no tabs.", file=sys.stderr)
                return 1
            rng = sheets[0]["properties"]["title"]

        resp = (svc.spreadsheets().values()
                .get(spreadsheetId=sheet_id, range=rng,
                     majorDimension="ROWS").execute())
        rows = resp.get("values", [])
    except Exception as e:  # noqa: BLE001 — any API/auth failure → caller falls back
        msg = str(e)
        hint = ""
        if "403" in msg or "PERMISSION_DENIED" in msg or "insufficient" in msg.lower():
            hint = ("  (If this is a scope error, re-run: gcloud auth "
                    "application-default login --scopes=...spreadsheets.readonly)")
        print(f"ERROR reading sheet: {msg}{hint}", file=sys.stderr)
        return 1

    if not rows:
        print("(sheet range is empty)", file=sys.stderr)
        return 1

    truncated = len(rows) > args.max_rows
    rows = rows[: args.max_rows]

    if args.format == "md":
        width = max(len(r) for r in rows)
        def fmt(r):
            cells = [str(c) for c in r] + [""] * (width - len(r))
            return "| " + " | ".join(cells) + " |"
        print(fmt(rows[0]))
        print("| " + " | ".join(["---"] * width) + " |")
        for r in rows[1:]:
            print(fmt(r))
    else:
        import csv
        w = csv.writer(sys.stdout)
        for r in rows:
            w.writerow(r)

    if truncated:
        print(f"\n[note: output capped at {args.max_rows} rows — sheet has more]",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
