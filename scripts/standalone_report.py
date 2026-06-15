#!/usr/bin/env python3
"""
standalone_report.py — wrap a single CE-RCA body fragment into a full, openable HTML
document.

The beautified sub-skill renderers (`render_ce_health.py`, `render_ce_context.py`,
and `render_perf_audit.py`) each emit a **body fragment**: a `#tab-<id>`-scoped
`<style>` + content + inline `<script>` (Plotly.newPlot / collapse / resize). Those
fragments are designed to be dropped inside the composite shell (`compose.py` +
`templates/report.html`), so on their own they have no `<html>`/`<head>`, no Plotly
CDN, and no `<div id="tab-<id>">` parent for their scoped CSS/JS — i.e. they're not
browser-openable.

This module is the **standalone counterpart of the composite shell**: given one
fragment, it produces a complete `<!DOCTYPE html>` document that opens in a browser —
reusing the SAME shared visual-kit `<style>` (from `references/visual_kit.md`) and the
SAME Plotly CDN as the composite, plus a lightweight per-skill banner. It is
deliberately skill-agnostic (keyed only by `scope_id`), so every fragment renderer
shares one wrapper and perf-audit can adopt it with a one-line `--standalone` add.

The orchestrated (multi-tab) path is unaffected — `compose.py` is not touched; this is
only used when a sub-skill is run on its own.

Usage (library):
    from standalone_report import wrap_fragment, build_banner
    html = wrap_fragment(frag, scope_id="tab-cehealth", title="CE Health — CE 243",
                         banner_html=build_banner(243, "Eiffel Tower", "Apr vs May", "CE Health"))

Usage (CLI — wrap an existing fragment file):
    python3 scripts/standalone_report.py --fragment <frag.html> --scope tab-cehealth \
        --title "CE Health — CE 243" --output <report.html>
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html as _html
import re
from pathlib import Path

# Omni dashboard — absolute BETWEEN template (correct for ANY window; matches the
# composite's custom-window form in cvr-rca/references/report_structure.md). The
# BETWEEN upper bound is exclusive, so we pass post_end + 1 day.
_OMNI_BETWEEN = (
    "https://headout.omniapp.co/dashboards/5368ab53?"
    "f--iv8lWOuS=%7B%22values%22%3A%5B%22{ce_id}%22%5D%7D"
    "&f--uvd3KWWJ=%7B%22kind%22%3A%22BETWEEN%22%2C%22left_side%22%3A%22{post_start}%22%2C"
    "%22right_side%22%3A%22{post_end_excl}%22%2C%22ui_type%22%3A%22BETWEEN%22%2C"
    "%22offset_interval_string%22%3Anull%7D"
)


def build_omni_url(ce_id, post_start: str, post_end: str) -> str:
    """Omni dashboard URL for this CE + post window (absolute BETWEEN; end-exclusive).
    '' if any input is missing/unparseable — the header just omits the Omni pill."""
    if ce_id in (None, "") or not post_start or not post_end:
        return ""
    try:
        excl = (_dt.date.fromisoformat(post_end) + _dt.timedelta(days=1)).isoformat()
    except Exception:  # noqa: BLE001
        return ""
    return _OMNI_BETWEEN.format(ce_id=ce_id, post_start=post_start, post_end_excl=excl)

# Same Plotly the composite template loads (templates/report.html) — keep in sync.
PLOTLY_CDN = '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>'

# visual_kit.md is the single source of the shared <style> (same block compose.py uses).
_DEFAULT_VISUAL_KIT = Path(__file__).resolve().parent.parent / "references" / "visual_kit.md"


def extract_style_block(visual_kit_path: Path) -> str:
    """Pull the shared `<style>…</style>` out of visual_kit.md. Self-contained copy of
    compose.py's extractor so this module doesn't couple to that (heavily-edited) file;
    the CSS itself still lives once, in visual_kit.md. Anchors on the universal reset
    (`* { … }`) so a prose mention of `<style>` in the doc can't mis-trigger the match."""
    try:
        if not visual_kit_path.exists():
            return ""
        text = visual_kit_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""
    m = re.search(r"<style>\s*\*\s*\{.*?</style>", text, flags=re.DOTALL)
    if m:
        return m.group(0)
    m = re.search(r"<style>.*?</style>", text, flags=re.DOTALL)
    return m.group(0) if m else ""


def build_banner(ce_id, ce_name: str, window_label: str = "", report_label: str = "") -> str:
    """A lightweight identity banner for a standalone single-skill report — reuses the
    visual-kit `<header>`/`.eyebrow`/`.meta` classes so it matches the composite's look.
    All fields optional; built from the skill's OWN data (no meta.json dependency)."""
    name = _html.escape(str(ce_name or (f"CE {ce_id}" if ce_id not in (None, "") else "CE")))
    eyebrow = _html.escape(report_label or "CE-RCA")
    meta_bits = []
    if ce_id not in (None, ""):
        meta_bits.append(f"CE {_html.escape(str(ce_id))}")
    if window_label:
        meta_bits.append(_html.escape(str(window_label)))
    meta = " · ".join(meta_bits)
    meta_html = f'<div class="meta">{meta}</div>' if meta else ""
    return (f'<header id="top"><div class="eyebrow">{eyebrow}</div>'
            f'<h1>{name}</h1>{meta_html}</header>')


def build_header_meta(md: dict, *, ce_id=None, ce_name: str = "", windows: dict = None) -> dict:
    """Map a CE Health sidecar `metadata` block (or any equivalent dict carrying the CE
    pill fields) into the `meta` dict `build_header()` expects — adding the pre/post
    period strings and the Omni dashboard pill. `windows` is `{"current":[s,e],
    "prior":[s,e]}` (the sidecar shape). Missing fields degrade gracefully (build_header
    omits empty pills / dashboards)."""
    md = md or {}
    windows = windows or {}
    cur, pri = windows.get("current"), windows.get("prior")

    def _per(w):
        return f"{w[0]} to {w[1]}" if w and len(w) == 2 else ""

    post_start = cur[0] if cur and len(cur) == 2 else ""
    post_end = cur[1] if cur and len(cur) == 2 else ""
    omni = build_omni_url(ce_id, post_start, post_end)
    return {
        "ce_id": ce_id if ce_id is not None else md.get("combined_entity_id", ""),
        "combined_entity_name": ce_name or md.get("combined_entity_name", ""),
        "combined_entity_type": md.get("combined_entity_type", ""),
        "market": md.get("market", ""),
        "country": md.get("country", ""),
        "pre_period": _per(pri),
        "post_period": _per(cur),
        "top_page_url": md.get("top_page_url", ""),
        "combined_entity_category": md.get("combined_entity_category"),
        "combined_entity_subcategory": md.get("combined_entity_subcategory"),
        "evolution_bucket": md.get("evolution_bucket"),
        "management_type": md.get("management_type"),
        "headout_status": md.get("headout_status"),
        "dashboards": [{"url": omni, "label": "Omni"}] if omni else [],
    }


def build_rich_header(meta: dict, eyebrow: str = None) -> str:
    """The FULL composite header (CE identity + pre/post + geo + LP link + Omni
    dashboard pill + the Category/Subcategory/Evolution/Management/Status chips) — by
    reusing `compose.build_header(meta)` so a standalone report's header is identical
    to the composite's. `meta` is built by the caller from its own sidecar (no
    `meta.json` needed). Optional `eyebrow` replaces the default "CE Root Cause
    Analysis" label (e.g. "CE Context"). Falls back to the lightweight banner if
    `compose` can't be imported."""
    try:
        from compose import build_header
    except Exception:  # noqa: BLE001
        wl = ""
        if meta.get("post_period"):
            wl = meta["post_period"] + (f" (vs {meta['pre_period']})" if meta.get("pre_period") else "")
        return build_banner(meta.get("ce_id"), meta.get("combined_entity_name", ""), wl, eyebrow or "CE-RCA")
    header = build_header(meta)
    if eyebrow:
        header = header.replace(
            '<div class="eyebrow">CE Root Cause Analysis</div>',
            f'<div class="eyebrow">{_html.escape(eyebrow)}</div>', 1)
    return header


def wrap_fragment(fragment_html: str, *, scope_id: str, title: str,
                  banner_html: str = "", visual_kit_path: Path = None) -> str:
    """Wrap a `#tab-<scope_id>`-scoped body fragment into a full openable HTML document.

    The fragment is placed inside `<div id="{scope_id}">` (so its scoped CSS/JS resolve)
    with the Plotly CDN + the shared visual-kit `<style>` in `<head>`. Standalone has a
    single always-visible pane, so the fragment's inline Plotly charts render at full
    width immediately (no hidden-tab resize problem)."""
    style_block = extract_style_block(visual_kit_path or _DEFAULT_VISUAL_KIT)
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        f"<title>{_html.escape(title)}</title>\n"
        f"{PLOTLY_CDN}\n"
        f"{style_block}\n"
        # Standalone niceties: comfortable page gutter + a styled single pane.
        "<style>body{margin:0;background:#f7f8fb;}"
        "#standalone-wrap{max-width:1280px;margin:0 auto;padding:0 18px 48px;}</style>\n"
        "</head>\n<body>\n"
        '<div id="standalone-wrap">\n'
        f"{banner_html}\n"
        f'<div id="{_html.escape(scope_id)}">\n{fragment_html}\n</div>\n'
        "</div>\n</body>\n</html>\n"
    )


def main():
    ap = argparse.ArgumentParser(description="Wrap a CE-RCA body fragment into a standalone HTML document.")
    ap.add_argument("--fragment", required=True, help="Path to the body-fragment HTML file.")
    ap.add_argument("--scope", required=True, help="Scope id the fragment's CSS is keyed to, e.g. tab-cehealth.")
    ap.add_argument("--title", default="CE-RCA report", help="Document <title>.")
    ap.add_argument("--output", required=True, help="Where to write the full HTML document.")
    ap.add_argument("--banner", default="", help="Optional pre-built banner HTML.")
    args = ap.parse_args()
    frag = Path(args.fragment).read_text(encoding="utf-8")
    doc = wrap_fragment(frag, scope_id=args.scope, title=args.title, banner_html=args.banner)
    Path(args.output).write_text(doc, encoding="utf-8")
    print(f"wrote {args.output} ({len(doc)} bytes)")


if __name__ == "__main__":
    main()
