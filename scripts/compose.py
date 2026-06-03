"""
compose.py — assemble the CE-RCA composite report.

Reads the sub-skill artifacts that landed in a run directory and stitches them
into one tabbed HTML deliverable, reusing the shared visual kit so the umbrella
report looks identical to a standalone CVR-RCA report.

The master orchestrator (SKILL.md) runs every sub-skill first, then calls:

    python3 scripts/compose.py --run-dir <run_dir>

Inputs expected in <run_dir> (each tab is emitted ONLY if its artifact exists):
    meta.json              — header info (CE id/name, dates, market, dashboards)
    ce_health_report.md    — CE Health tab (markdown → HTML, verbatim)
    cvr_rca_report.html    — CVR-RCA tab (CVR content extracted, charts re-injected)
    perf_audit_report.md   — Paid Performance Audit tab (markdown → HTML, verbatim)
    orchestration.json     — (optional) which skills the master fired; for logging only

Output:
    <run_dir>/report.html  — the composite (this is what the user opens)

Design principle: this script is a COMPOSER, not an editor. Sub-skill content is
rendered/extracted verbatim — never summarized, reordered, or restyled. Adding a
future tab is one entry in TAB_SPECS, no other change.

Python 3.9 compatible.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from helpers import render_markdown_tab, extract_cvr_rca_tab


def extract_style_block(visual_kit_path: Path) -> str:
    """Pull the shared <style>...</style> block out of the vendored visual_kit.md.

    Keeping the composite's CSS sourced from visual_kit (rather than hand-copied
    into the template) means a visual_kit sync automatically updates the
    composite's styling — no drift between the kit and the umbrella report.
    """
    if not visual_kit_path.exists():
        return ""
    text = visual_kit_path.read_text(encoding="utf-8")
    # The file mentions the literal "<style>" several times in prose ("the shared
    # <style> block"), so a naive `<style>.*?</style>` would start at a prose
    # mention and swallow the HTML examples in between. Anchor on the real CSS
    # signature — the block opens with `* { ... }`, the universal reset.
    m = re.search(r"<style>\s*\*\s*\{.*?</style>", text, flags=re.DOTALL)
    if m:
        return m.group(0)
    # Defensive fallback — broad match (should not be needed)
    m = re.search(r"<style>.*?</style>", text, flags=re.DOTALL)
    return m.group(0) if m else ""


# ─────────────────────────────────────────────────────────────────────────────
# Tab manifest — ordered. A tab is emitted only when its `source` file exists.
# Reading order matches the C-level mental model: zoom out (CE Health) → zoom in
# (CVR funnel) → zoom further (paid). Adding a future tab = one entry here.
# ─────────────────────────────────────────────────────────────────────────────

TAB_SPECS = [
    {
        "id": "cehealth",
        "label": "CE Health",
        "source": "ce_health_report.md",
        "type": "markdown",
        "anchor_prefix": "cehealth-",
    },
    {
        "id": "cvr-rca",
        "label": "CVR RCA",
        "source": "cvr_rca_report.html",
        "type": "html-extract",
    },
    {
        "id": "perfaudit",
        "label": "Paid Performance Audit",
        "source": "perf_audit_report.md",
        "type": "markdown",
        "anchor_prefix": "perfaudit-",
    },
]


def build_header(meta: dict) -> str:
    """Build the dark header block: eyebrow, CE name, meta row, dashboards row."""
    ce_id = meta.get("ce_id", "")
    ce_name = meta.get("combined_entity_name") or f"CE {ce_id}"
    ce_type = meta.get("combined_entity_type", "")
    market = meta.get("market", "")
    country = meta.get("country", "")
    pre_period = meta.get("pre_period", "")
    post_period = meta.get("post_period", "")
    top_url = meta.get("top_page_url", "")

    # CE name links to the live page when we have a URL
    if top_url:
        name_html = (
            f'<a href="{top_url}" target="_blank" rel="noopener" '
            f'style="color:#fff;text-decoration:none;border-bottom:2px solid rgba(255,255,255,.4);">'
            f"{ce_name}</a>"
        )
    else:
        name_html = ce_name

    geo_bits = " · ".join([b for b in (market, country) if b])

    meta_spans = []
    if pre_period:
        meta_spans.append(f"<span>📅 Pre: {pre_period}</span>")
    if post_period:
        meta_spans.append(f"<span>📅 Post: {post_period}</span>")
    if geo_bits:
        meta_spans.append(f"<span>🌍 {geo_bits}</span>")
    if top_url:
        meta_spans.append(
            f'<span>🔗 <a href="{top_url}" target="_blank" '
            f'style="color:#b0bec5;text-decoration:underline;">{top_url}</a></span>'
        )

    # Dashboards row — pill links owned by the master's meta (CE-scoped)
    dash_html = ""
    dashboards = meta.get("dashboards", [])
    if dashboards:
        pills = "".join(
            f'<a href="{d.get("url", "#")}" target="_blank" class="dash-link">'
            f'{d.get("label", "Dashboard")} ↗</a>'
            for d in dashboards
        )
        dash_html = (
            '<div class="dashboards"><span class="dash-label">DASHBOARDS</span>'
            f"{pills}</div>"
        )

    sub_bits = " · ".join([b for b in (f"CE {ce_id}", ce_type) if b])

    return f"""<header id="top">
  <div class="eyebrow">CE Root Cause Analysis</div>
  <h1>{name_html}</h1>
  <div style="font-size:12px;color:#8892a4;margin-top:4px;">{sub_bits}</div>
  <div class="meta">{''.join(meta_spans)}</div>
  {dash_html}
</header>"""


def build_tabs(run_dir: Path) -> tuple[str, str, str]:
    """Build (tab_bar_html, panes_html, chart_scripts_html) from present artifacts."""
    present = []
    for spec in TAB_SPECS:
        if (run_dir / spec["source"]).exists():
            present.append(spec)

    if not present:
        # Should not happen — CE Health always runs — but degrade gracefully.
        return (
            "",
            '<div class="container"><div class="md-content"><p>No sub-skill '
            "artifacts found in the run directory.</p></div></div>",
            "",
        )

    buttons = []
    panes = []
    chart_scripts = []

    for idx, spec in enumerate(present):
        active = " active" if idx == 0 else ""
        aria = "true" if idx == 0 else "false"
        buttons.append(
            f'<button class="tab-button{active}" data-tab="{spec["id"]}" '
            f'role="tab" aria-selected="{aria}">{spec["label"]}</button>'
        )

        src_path = run_dir / spec["source"]
        if spec["type"] == "markdown":
            pane_body = render_markdown_tab(src_path, spec["anchor_prefix"])
        elif spec["type"] == "html-extract":
            html = src_path.read_text(encoding="utf-8")
            body, scripts = extract_cvr_rca_tab(html)
            pane_body = body
            if scripts:
                chart_scripts.append(scripts)
        else:
            pane_body = '<div class="md-content"><p>Unknown tab type.</p></div>'

        panes.append(
            f'<div class="tab-pane{active}" id="tab-{spec["id"]}" role="tabpanel">'
            f"{pane_body}</div>"
        )

    tab_bar = f'<div class="tab-bar" role="tablist">{"".join(buttons)}</div>'
    panes_html = '<div class="container">' + "\n".join(panes) + "</div>"
    return tab_bar, panes_html, "\n".join(chart_scripts)


def main():
    p = argparse.ArgumentParser(description="Assemble the CE-RCA composite report.")
    p.add_argument("--run-dir", required=True, help="Run directory with sub-skill artifacts")
    p.add_argument("--output", default=None, help="Output path (default <run_dir>/report.html)")
    p.add_argument("--template", default=None, help="Composite template (default templates/report.html)")
    args = p.parse_args()

    run_dir = Path(args.run_dir)
    output = Path(args.output) if args.output else run_dir / "report.html"
    template_path = (
        Path(args.template)
        if args.template
        else Path(__file__).parent.parent / "templates" / "report.html"
    )

    meta = {}
    meta_path = run_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())

    header = build_header(meta)
    tab_bar, panes, chart_scripts = build_tabs(run_dir)

    ce_id = meta.get("ce_id", "")
    ce_name = meta.get("combined_entity_name", "")
    title = f"CE-RCA · {ce_name} (CE {ce_id})" if ce_name else f"CE-RCA · CE {ce_id}"
    gen_date = meta.get("generated_date", "")
    footer = f"Generated {gen_date} · CE-RCA · CE {ce_id} {ce_name}".strip(" ·")

    visual_kit_path = Path(__file__).parent.parent / "references" / "visual_kit.md"
    style_block = extract_style_block(visual_kit_path)

    template = template_path.read_text(encoding="utf-8")
    html = (
        template
        .replace("{{TITLE}}", title)
        .replace("{{STYLE}}", style_block)
        .replace("{{HEADER}}", header)
        .replace("{{TAB_BAR}}", tab_bar)
        .replace("{{PANES}}", panes)
        .replace("{{CHART_SCRIPTS}}", chart_scripts)
        .replace("{{FOOTER}}", footer)
    )

    output.write_text(html, encoding="utf-8")
    print(f"Composite report written → {output}")


if __name__ == "__main__":
    main()
