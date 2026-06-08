"""
validate.py — advisory completeness linter for a finished CVR-RCA report.

This runs ONCE, at the very end, AFTER report.html is written. It is purely
cosmetic/advisory:

  - It never sees or influences the investigation. Claude's freedom to explore,
    form hypotheses, and decide what matters is untouched.
  - It only READS the finished HTML and prints what looks missing or orphaned.
  - It NEVER edits the report and NEVER blocks (exit code is always 0).
  - Claude decides per finding: add the element, or consciously skip it (a report
    can legitimately omit something — the linter has no veto).

The point is to catch silent structural gaps — most importantly a chart
placeholder `<div>` with no matching render script, which renders as an empty
gap (this is exactly what happened to the 90-day chart on CE 243).

Usage:
    python3 validate.py --report <path/to/report.html> [--run-dir <dir>] [--json]

Fast (string/regex only, no queries). Output is a short human-readable list,
or JSON with --json.

Python 3.9 compatible.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def lint(html: str, run_dir: Path | None) -> list[dict]:
    findings: list[dict] = []

    # ── Generic chart-integrity check (the strongest, least-rigid rule) ───────
    # Every *leaf* chart container must have a matching Plotly.newPlot call.
    # Catches the 90-day failure AND any future orphaned chart without
    # enumerating a fixed chart list.
    #
    # Important: a `chart-*` / `trend-*` id can legitimately belong to an
    # `.analysis-block` *wrapper* (the anchor convention names a chart-bearing
    # block `chart-daily-s2c`, while the actual Plotly div inside is a separate
    # element). Those wrappers are NOT plot targets, so we skip any id whose
    # opening <div> carries `analysis-block`. We only require a render script for
    # leaf containers (typically `class="chart-container"` or a bare div).
    for m in re.finditer(r'<div\b([^>]*\bid="((?:chart|trend)-[a-z0-9-]+)"[^>]*)>', html):
        attrs, cid = m.group(1), m.group(2)
        if "analysis-block" in attrs:
            continue  # section wrapper anchored with a chart id, not a plot target
        if (f"Plotly.newPlot('{cid}'" not in html
                and f'Plotly.newPlot("{cid}"' not in html):
            findings.append({
                "kind": "orphaned-chart",
                "what": cid,
                "hint": f"<div id=\"{cid}\"> is a chart container but has no "
                        f"Plotly.newPlot('{cid}') call — it will render as an empty "
                        "gap. Add the render script or remove the placeholder.",
            })

    # ── Always-on element presence ───────────────────────────────────────────
    always_on = [
        ("metric cards", r'class="metric-card"',
         "the headline metric cards (CVR / LP2S / S2C / C2O / Traffic)"),
        ("90-day trend chart", r'id="trend-90day"',
         "the always-on 90-day CVR + LY trend chart (Section 1b)"),
        ("root-cause callout", r'class="callout"',
         "the Section 1 root-cause callout"),
        ("hypotheses block", r'block-hypotheses',
         "the Hypotheses Explored block (always last in Section 3)"),
    ]
    for name, pattern, hint in always_on:
        if not re.search(pattern, html):
            findings.append({
                "kind": "missing-element",
                "what": name,
                "hint": f"no {hint} found in the report.",
            })

    # ── Provenance consistency: cited externally but no External Signals table ─
    # If the report leans on external lenses (inline citations / cross-tab links)
    # but has no External Signals & Corroboration table, the provenance contract
    # is half-applied. Only checked when we can see the run dir's lens artifacts.
    cited_external = bool(re.search(
        r'per perf-audit|prompted by perf-audit|#perfaudit-|#cehealth-|per CE Health|'
        r'CE Health:|slack-?thread|\(per [A-Z]',
        html))
    has_signals_table = 'id="block-market-context"' in html
    lens_files_present = False
    if run_dir is not None:
        for f in ("slack_context.md", "perf_audit_report.md",
                  "perf_audit_summary.md", "ce_health_report.md"):
            p = run_dir / f
            if p.exists() and p.stat().st_size > 0:
                lens_files_present = True
                break
    if (cited_external or lens_files_present) and not has_signals_table:
        findings.append({
            "kind": "provenance-gap",
            "what": "External Signals & Corroboration table",
            "hint": "external lenses were available and/or cited inline, but there is "
                    "no External Signals table (id=block-market-context). Per the "
                    "provenance contract, every external signal you USED should also "
                    "appear as a table row. (If you used no external signal, this is a "
                    "fine skip.)",
        })

    return findings


def main():
    p = argparse.ArgumentParser(description="Advisory completeness linter for a finished report.")
    p.add_argument("--report", required=True, help="Path to the finished report.html")
    p.add_argument("--run-dir", default=None, help="Run directory (to check lens artifacts)")
    p.add_argument("--json", action="store_true", help="Emit findings as JSON")
    args = p.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"validate: report not found at {report_path} — nothing to check.")
        return  # exit 0 — advisory only, never blocks

    html = report_path.read_text(encoding="utf-8")
    run_dir = Path(args.run_dir) if args.run_dir else report_path.parent
    findings = lint(html, run_dir)

    if args.json:
        print(json.dumps({"findings": findings}, indent=2))
        return

    if not findings:
        print("✓ validate: no missing or orphaned elements. Report looks complete.")
        return

    print(f"validate: {len(findings)} advisory finding(s) — ADD each, or consciously "
          "skip it (a report can legitimately omit something; your judgment is final):\n")
    for i, f in enumerate(findings, 1):
        print(f"  {i}. [{f['kind']}] {f['what']}")
        print(f"     {f['hint']}")
    print("\n(Advisory only — nothing here blocks. Decide per item, then finalize.)")


if __name__ == "__main__":
    main()
