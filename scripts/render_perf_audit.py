#!/usr/bin/env python3
"""
render_perf_audit.py — beautify the Paid Performance Audit tab for the CE-RCA composite.

perf-audit ships a regular GFM markdown report (`perf_audit_report.md`): a title
block, then `## N. …` sections (Exec Summary … Recommended Actions) plus `## A.`
/ `## B.` appendix sections, each a mix of tables and NARRATIVE prose. This
renderer re-renders that markdown into visual_kit chrome — the same
"structured re-render" `render_ce_health.py` applies to CE Health's markdown —
and writes a body fragment `<run_dir>/perf_audit_tab.html` (or `tabs/…` on an
organized run) that `compose.py` embeds verbatim as the perf-audit tab
(`html-fragment` type, with a markdown fallback).

Fidelity contract (see references/composition_rules.md):
  • perf-audit's WORDING is preserved verbatim. The renderer only RELOCATES the
    §1 verdict line into a coloured banner and RESTYLES the layout — it never
    rewrites, summarizes, re-words, re-rounds, drops, or reorders prose / cells.
    Visible text is byte-equal to the source (modulo HTML-escaping + the
    bold/italic markdown→HTML the source already used).
  • Per `## N.` section → one `.analysis-block` card (id `perfaudit-<slug>`,
    slug matching the markdown anchor scheme so cross-tab `↗` links resolve):
      1. Verdict banner IF a leading `**Status: …**` line exists (only §1 has
         one). Coloured by the Status TEXT token (ignore emoji): CRITICAL → red
         `.callout`, WARNING → amber `.callout.neutral`, HEALTHY/OK → green
         `.callout.improve`. No verdict line → no banner (neutral titled card).
      2. Beautified table(s) — every GFM table → styled_table(...).
      3. Grey supporting prose — the remaining paragraphs, verbatim, muted.
    Banner → table(s) → prose ordering; within (2)/(3) the original document
    order (incl. `###` subsections) is preserved so nothing is reshuffled.
  • Degrades gracefully: prose-only, table-only, nested `###`, multiple tables,
    irregular sections — never crashes; a parse it can't card-ify still renders
    its content. A render failure leaves no `perf_audit_tab.html` → compose
    falls back to the verbatim markdown tab.

Usage:
    python3 scripts/render_perf_audit.py --run-dir <run_dir>
"""
from __future__ import annotations

import argparse
import html as _html
import re
import sys
from pathlib import Path

# Reuse the proven helpers from the CE Health renderer + the markdown renderer.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_ce_health import section, tables_in, _cell, styled_table  # noqa: E402,F401
from helpers import render_markdown_to_html, slugify  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Scoped style — readable wide-table wrap (§5/§9/§10/appendix tables have many
# columns; styled_table's base cells would otherwise crush prose columns to one
# word per line). Mirrors the shipped `.md-table-wrap` readable-wrap fix, scoped
# to #tab-perfaudit so it can't leak into other tabs / the shared visual_kit.
# ─────────────────────────────────────────────────────────────────────────────
PERF_TABLE_STYLE = (
    "<style>"
    # Cells wrap at a readable width; the wrapper scrolls horizontally only if the
    # columns together still exceed the container. Short cells (numbers) stay
    # compact at min-width; long prose wraps at <=340px instead of collapsing.
    "#tab-perfaudit .analysis-block th,"
    "#tab-perfaudit .analysis-block td{white-space:normal;vertical-align:top;"
    "min-width:64px;max-width:340px;overflow-wrap:break-word;}"
    # Grey supporting prose under the table(s) — muted, smaller, verbatim text.
    "#tab-perfaudit .pa-prose{font-size:13px;line-height:1.6;color:#555;}"
    "#tab-perfaudit .pa-prose p{margin:8px 0;}"
    "#tab-perfaudit .pa-prose strong{color:#3a3a52;}"
    "#tab-perfaudit .pa-prose ul,#tab-perfaudit .pa-prose ol{margin:8px 0 12px 22px;}"
    "#tab-perfaudit .pa-prose li{margin:4px 0;}"
    "#tab-perfaudit .pa-prose h3{font-size:13px;font-weight:700;color:#2a2a44;margin:16px 0 6px;}"
    "#tab-perfaudit .pa-prose h4{font-size:12px;font-weight:700;color:#2a2a44;"
    "margin:14px 0 6px;text-transform:uppercase;letter-spacing:.05em;}"
    "#tab-perfaudit .pa-prose a{color:#3a4a8a;text-decoration:none;border-bottom:1px solid rgba(58,74,138,.3);}"
    "#tab-perfaudit .pa-prose code{font-family:'SF Mono',Menlo,monospace;font-size:12px;"
    "background:#f5f6fa;padding:2px 6px;border-radius:4px;color:#c62828;}"
    # Verdict banner — the hoisted §1 Status line. Colour by Status token.
    "#tab-perfaudit .pa-verdict{font-size:14px;font-weight:600;border-radius:8px;"
    "padding:12px 16px;margin:0 0 16px;border-left:4px solid #e53935;background:#fff;"
    "border-top:1px solid #e8ebf4;border-right:1px solid #e8ebf4;border-bottom:1px solid #e8ebf4;}"
    "#tab-perfaudit .pa-verdict.crit{border-left-color:#e53935;color:#1a1a2e;}"
    "#tab-perfaudit .pa-verdict.crit .pa-verdict-tag{color:#c62828;}"
    "#tab-perfaudit .pa-verdict.warn{border-left-color:#f57c00;color:#1a1a2e;}"
    "#tab-perfaudit .pa-verdict.warn .pa-verdict-tag{color:#e07000;}"
    "#tab-perfaudit .pa-verdict.ok{border-left-color:#2e7d32;color:#1a1a2e;}"
    "#tab-perfaudit .pa-verdict.ok .pa-verdict-tag{color:#2e7d32;}"
    "#tab-perfaudit .pa-verdict-tag{font-weight:800;letter-spacing:.3px;}"
    # Severity row tints in the §9 Red-Flags table.
    "#tab-perfaudit tr.pa-sev-crit td:first-child,"
    "#tab-perfaudit tr.pa-sev-high td:first-child{font-weight:700;}"
    "#tab-perfaudit tr.pa-sev-crit td:first-child{color:#c62828;}"
    "#tab-perfaudit tr.pa-sev-high td:first-child{color:#e07000;}"
    "#tab-perfaudit tr.pa-sev-med td:first-child{color:#b08900;}"
    "#tab-perfaudit tr.pa-sev-low td:first-child{color:#5a6478;}"
    "</style>"
)


# ─────────────────────────────────────────────────────────────────────────────
# Verdict detection — only §1 carries a leading `**Status: …**` line.
# ─────────────────────────────────────────────────────────────────────────────

# A Status line: a markdown bold-led line whose bold span starts with "Status:".
# The rest of the line (trailing prose after the bold span, e.g. ce-3593's
# "— sequential, not annual. Revenue is …") is preserved verbatim in the banner.
_STATUS_LINE = re.compile(r'^\s*\*\*\s*Status:.*', re.IGNORECASE)


def _status_token_class(status_line: str):
    """Classify a Status line by its TEXT token (emoji ignored) → a CSS class.
    CRITICAL → 'crit' (red), WARNING → 'warn' (amber), HEALTHY/OK → 'ok' (green).
    Returns 'crit'|'warn'|'ok' or None if no recognized token is present."""
    up = status_line.upper()
    if "CRITICAL" in up:
        return "crit"
    if "WARNING" in up or "WARN" in up:
        return "warn"
    if "HEALTHY" in up or re.search(r'\bOK\b', up):
        return "ok"
    return None


def _verdict_banner(status_line: str) -> str:
    """Render the hoisted §1 verdict line VERBATIM as a coloured banner.
    The whole source line is shown (Status token + any emoji + trailing prose);
    only the leading `**Status:` bold span is given a coloured tag wrapper. The
    text is byte-equal to the source (modulo HTML-escape + bold/italic→HTML)."""
    cls = _status_token_class(status_line) or "crit"
    # Render the full line with INLINE-only conversion (escape + bold/italic) so a
    # single line never gets mis-parsed as a block (a leading "1." would become an
    # <ol>, a leading "- " a <ul>). `_cell` is escape + **bold** + *italic* only —
    # exactly the inline set the Status line uses; its wording is byte-preserved.
    inner = _cell(status_line.strip())
    # Colour the first <strong>…</strong> (the "Status: …" bold span).
    inner = re.sub(r'<strong>(.*?)</strong>',
                   r'<span class="pa-verdict-tag"><strong>\1</strong></span>',
                   inner, count=1, flags=re.DOTALL)
    return f'<div class="pa-verdict {cls}">{inner}</div>'


# ─────────────────────────────────────────────────────────────────────────────
# Block-level parse of a section body — preserves document order so prose,
# subsection headings, and tables are never reshuffled relative to one another.
# ─────────────────────────────────────────────────────────────────────────────

def _is_table_sep(line: str) -> bool:
    return bool(re.match(r'^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$', line))


def _parse_blocks(body: str):
    """Split a section body into ordered ('table', (hdr, rows)) and
    ('prose', text) blocks. `###`/`####` subheadings stay inside the prose
    stream (rendered verbatim by render_markdown_to_html) so their wording +
    position are preserved. Contiguous non-table lines coalesce into one prose
    block; each GFM pipe table is its own table block."""
    lines = body.split("\n")
    blocks = []
    prose_buf = []
    i = 0

    def _flush_prose():
        if prose_buf:
            txt = "\n".join(prose_buf).strip("\n")
            if txt.strip():
                blocks.append(("prose", txt))
            prose_buf.clear()

    while i < len(lines):
        line = lines[i]
        # GFM table: header row + separator row.
        if "|" in line and i + 1 < len(lines) and _is_table_sep(lines[i + 1]):
            hdr = [c.strip() for c in line.strip().strip("|").split("|")]
            j = i + 2
            rows = []
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            _flush_prose()
            blocks.append(("table", (hdr, rows)))
            i = j
            continue
        prose_buf.append(line)
        i += 1
    _flush_prose()
    return blocks


# Severity row classes for the §9 Red Flags table (cheap, optional — never fatal).
_SEV_CLASS = {
    "CRITICAL": "pa-sev-crit",
    "HIGH": "pa-sev-high",
    "MEDIUM": "pa-sev-med",
    "MED": "pa-sev-med",
    "LOW": "pa-sev-low",
}


def _severity_row_classes(hdr, rows):
    """If the first column is a severity column (CRITICAL/HIGH/MED/LOW), return a
    list of per-row classes to tint the severity cell; else None."""
    if not rows:
        return None
    first_hdr = (hdr[0] if hdr else "").strip().lower()
    if "severity" not in first_hdr:
        return None
    out = []
    for r in rows:
        tok = (r[0].strip().strip('*').upper() if r else "")
        out.append(_SEV_CLASS.get(tok, ""))
    return out if any(out) else None


def _render_table(hdr, rows) -> str:
    """One GFM table → a beautified styled_table, with optional §9 severity tints.
    Wrapped so the scoped readable-wrap style applies. Wording preserved verbatim
    (styled_table escapes + converts bold/italic only)."""
    row_classes = _severity_row_classes(hdr, rows)
    return styled_table(hdr, rows, row_classes=row_classes)


def _render_prose(text: str) -> str:
    """Remaining paragraphs (and any `###` subheadings) rendered VERBATIM as muted
    grey supporting text. render_markdown_to_html preserves headings, lists,
    bold/italic, links, code — no word changes. `###`/`####` subheadings get the
    `perfaudit-` anchor prefix so their ids match the markdown-fallback tab's."""
    html = render_markdown_to_html(text, anchor_prefix="perfaudit-")
    return f'<div class="pa-prose">{html}</div>'


# ─────────────────────────────────────────────────────────────────────────────
# Redundant-caption de-dup. The perf-audit engine emits a bold caption that often
# just echoes the heading (e.g. `## 3. Channel Breakdown` then `**Channel
# Breakdown**`; `### Ad Group Coverage` then `**Ad Group Coverage**`). Since we
# render the heading as the card title (and `###` as a sub-heading), that echo is
# a visible duplicate. Drop a bold-only line ONLY when it normalises equal to the
# heading it sits under — informative labels like `**Table 1: CE Health …**` are
# kept (they don't echo the heading). Wording-preserving: we remove a pure
# duplicate the title already states, never anything that adds information.
# ─────────────────────────────────────────────────────────────────────────────
_BOLD_ONLY = re.compile(r'^\s*\*\*(.+?)\*\*\s*$')
_SUBHEAD = re.compile(r'^\s*#{3,4}\s+(.*\S)\s*$')


def _norm_heading(s: str) -> str:
    s = re.sub(r'\*\*|\*|`', '', s.strip())                 # strip md emphasis/code
    s = re.sub(r'^\s*[0-9A-Za-z]{1,3}\.\s+', '', s)         # strip "3. " / "A3. " enumerator
    s = re.sub(r'[\s:–—-]+$', '', s)                        # trailing punctuation
    return re.sub(r'\s+', ' ', s).strip().lower()


def _strip_echo_captions(body: str, heading_text: str) -> str:
    """Drop bold-only caption lines that merely echo the section/subsection heading."""
    cur = _norm_heading(heading_text)
    out = []
    for ln in body.split("\n"):
        mh = _SUBHEAD.match(ln)
        if mh:
            cur = _norm_heading(mh.group(1))
            out.append(ln)
            continue
        mb = _BOLD_ONLY.match(ln)
        if mb and _norm_heading(mb.group(1)) == cur:
            continue  # redundant echo of the heading → drop
        out.append(ln)
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# Card assembly
# ─────────────────────────────────────────────────────────────────────────────

def _card(title_text: str, bid: str, body_html: str) -> str:
    """A neutral titled `.analysis-block` card. `title_text` is the section's
    heading text rendered verbatim — INLINE-only conversion (`_cell`: escape +
    bold/italic) so a leading "1. " / "A. " survives literally instead of being
    swallowed by the block renderer's ordered-list rule."""
    title_html = _cell(title_text)
    return (
        f'<div class="analysis-block" id="{bid}">'
        f'<div class="block-title">{title_html}</div>'
        f'{body_html}'
        f'</div>'
    )


def _render_section(heading_text: str, body: str) -> str:
    """Build one section card: hoist a leading `**Status:` verdict line into a
    coloured banner, then render the section's tables (beautified) and remaining
    prose (grey) IN DOCUMENT ORDER below it. Wording is preserved verbatim — only
    the verdict line is relocated and the layout restyled."""
    # 0) Drop bold captions that merely echo the heading (engine emits these).
    body = _strip_echo_captions(body, heading_text)
    # 1) Hoist a leading verdict line if present (keep the rest of body verbatim).
    banner_html = ""
    body_lines = body.split("\n")
    kept = []
    hoisted = False
    for ln in body_lines:
        if not hoisted and ln.strip() and _STATUS_LINE.match(ln):
            banner_html = _verdict_banner(ln)
            hoisted = True
            continue
        kept.append(ln)
    rest = "\n".join(kept)

    # 2)/3) Tables (beautified) + prose (grey), in original document order.
    parts = []
    for kind, payload in _parse_blocks(rest):
        if kind == "table":
            hdr, rows = payload
            parts.append(_render_table(hdr, rows))
        else:
            parts.append(_render_prose(payload))

    bid = "perfaudit-" + slugify(heading_text)
    return _card(heading_text, bid, banner_html + "".join(parts))


# ─────────────────────────────────────────────────────────────────────────────
# Top-level split into sections (preserve the leading H1 title block)
# ─────────────────────────────────────────────────────────────────────────────

# A `## ` section header line (captures the heading text after the ##).
_H2 = re.compile(r'^##\s+(.+?)\s*#*\s*$')


def _split_sections(md: str):
    """Return (preamble_md, [(heading_text, body_md), …]) — the leading content
    before the first `## ` (the `# title` block: Market/Date/Period/Landing Page)
    as preamble, then each `## ` section with its body (everything up to the next
    `## `). Order preserved exactly."""
    lines = md.split("\n")
    preamble = []
    sections = []
    cur_head = None
    cur_body = []
    started = False
    for ln in lines:
        m = _H2.match(ln)
        if m:
            if started:
                sections.append((cur_head, "\n".join(cur_body)))
            else:
                started = True
            cur_head = m.group(1).strip()
            cur_body = []
        elif started:
            cur_body.append(ln)
        else:
            preamble.append(ln)
    if started:
        sections.append((cur_head, "\n".join(cur_body)))
    return "\n".join(preamble), sections


def _render_preamble(preamble_md: str) -> str:
    """Render the title block (the `# …` title + Market/Date/Period/Landing Page
    lines and any leading `---`) verbatim as a small muted header above the cards.
    '' if there's nothing before the first section."""
    txt = preamble_md.strip()
    # Drop a lone trailing horizontal rule that separated the title from §1.
    txt = re.sub(r'\n-{3,}\s*$', '', txt).strip()
    if not txt:
        return ""
    return f'<div class="md-content" style="margin-bottom:18px;">{render_markdown_to_html(txt)}</div>'


def build_fragment(md: str) -> str:
    """Build the perf-audit tab body fragment from the report markdown."""
    preamble, sections = _split_sections(md)
    parts = [PERF_TABLE_STYLE]
    head = _render_preamble(preamble)
    if head:
        parts.append(head)
    if not sections:
        # No `## ` sections at all (unexpected) — degrade to a verbatim render so
        # the tab still shows content rather than crashing.
        parts.append(f'<div class="pa-prose">{render_markdown_to_html(md)}</div>')
        return "\n".join(parts)
    for heading_text, body in sections:
        parts.append(_render_section(heading_text, body))
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Input/output resolution — subfolder-first, like compose.resolve. The report
# lands in `reports/perf_audit_report.md` on an organized run, else the run-dir
# root. The fragment is written to `tabs/` when that layout is in use, else root
# (matching where compose looks for `perf_audit_tab.html`).
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_input(run_dir: Path) -> Path:
    sub = run_dir / "reports" / "perf_audit_report.md"
    if sub.exists():
        return sub
    return run_dir / "perf_audit_report.md"


def _resolve_output(run_dir: Path, input_path: Path) -> Path:
    # If the input came from reports/ (organized) or a tabs/ dir already exists,
    # write into tabs/ so compose's subfolder-first resolve finds it; else root.
    organized = input_path.parent.name == "reports" or (run_dir / "tabs").is_dir()
    out_dir = (run_dir / "tabs") if organized else run_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "perf_audit_tab.html"


def _write_standalone(run_dir: Path, frag: str, md: str):
    """Wrap the perf-audit fragment into an openable `report.html` (standalone runs).
    Lightweight banner (label from the report's H1); the CE-metadata header pills are a
    CE Context / CE Health concern, not perf-audit's. Graceful if the wrapper is gone."""
    try:
        from standalone_report import wrap_fragment, build_banner
    except Exception as e:  # noqa: BLE001
        print(f"standalone wrap unavailable ({e}) — fragment written, no report.html", file=sys.stderr)
        return
    m = re.search(r'^#\s+(.+)$', md, flags=re.MULTILINE)
    label = m.group(1).strip() if m else "Paid Performance Audit"
    banner = build_banner(None, label, "", "Paid Performance Audit")
    title = f"Paid Performance Audit — {label}" if m else "Paid Performance Audit"
    doc = wrap_fragment(frag, scope_id="tab-perfaudit", title=title, banner_html=banner)
    out = run_dir / "report.html"
    out.write_text(doc, encoding="utf-8")
    print(f"wrote {out} ({len(doc)} bytes) [standalone]")


def main():
    ap = argparse.ArgumentParser(description="Render the beautified perf-audit tab fragment.")
    ap.add_argument("--run-dir", required=True, help="Run directory with the perf-audit report.")
    ap.add_argument("--standalone", action="store_true",
                    help="Also wrap the fragment into an openable standalone report.html.")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).expanduser()

    src = _resolve_input(run_dir)
    if not src.exists():
        print(f"WARN: {src.name} not found in {run_dir}; nothing to render "
              "(compose falls back to markdown).", file=sys.stderr)
        return
    md = src.read_text(encoding="utf-8")
    if not md.strip():
        print(f"WARN: {src} is empty; nothing to render.", file=sys.stderr)
        return

    frag = build_fragment(md)
    out = _resolve_output(run_dir, src)
    out.write_text(frag, encoding="utf-8")
    print(f"wrote {out} ({len(frag)} bytes)")
    if args.standalone:
        _write_standalone(run_dir, frag, md)


if __name__ == "__main__":
    main()
