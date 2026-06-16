#!/usr/bin/env python3
"""
render_ce_context.py — render the "CE Context" tab fragment for the CE-RCA composite.

CE Context is the orientation layer — what we know about a CE before the metrics.
This renderer turns the captured streams into a visual-kit body fragment
`<run_dir>/ce_context_report.html` that `compose.py` embeds verbatim as the CE
Context tab (`html-fragment`, anchors `cecontext-*`), positioned right after Summary.

Section order (stakeholder template):
  1. About this CE          (cecontext-about)        — user-context "About this CE" slot
  2. Timeline of changes    (cecontext-timeline)     — Plotly, pre/post window shaded
  3. Recent past RCAs       (cecontext-pastrca)      — per-RCA table from ce_history.json
  4. Known constraints      (cecontext-constraints)  — bucketed Q&A from ce_context_constraints.json
  5. Known failure modes    (cecontext-failuremodes) — user-context slot
  6. Important links         (cecontext-links)        — user-context slot
  7. Slack standing context (cecontext-slack)        — raw provenance, collapsed

Design: the CE Context sub-agent emits structured JSON (`ce_context_timeline.json`,
`ce_history.json`, `ce_context_constraints.json`); this renderer plots them
deterministically and gracefully (missing JSON → fallback or omit, never crash).
The deterministic context primitives (slot splitter, link table, prior-run index,
collapsible block) are imported from render_ce_health.py — no duplication.

Timing note: CE Context renders at the umbrella's Step 2 (parallel with the deep
dives), BEFORE `meta.json` is built (Step 4a). So ce_id / windows come from CE
Health's sidecar (`ce_health_report.json`) and the timeline JSON — never `meta.json`.

The collapse + table styling is reused from render_ce_health and RE-SCOPED from
`#tab-cehealth` → `#tab-cecontext` so it applies to this tab and nowhere else.

Usage:
    python3 scripts/render_ce_context.py --run-dir <run_dir>
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html as _html
import json
from pathlib import Path

from helpers import render_markdown_to_html
from render_ce_health import (
    block,
    _subhead,
    _split_user_context_slots,
    _uctx_links_block,
    prior_runs_block,
    CEH_TABLE_STYLE,
    CEH_COLLAPSE_STYLE,
    CEH_COLLAPSE_SCRIPT,
)

# Re-scope the CE Health chrome to this tab so it applies here and can't leak.
CTX_TABLE_STYLE = CEH_TABLE_STYLE.replace("#tab-cehealth", "#tab-cecontext")
CTX_COLLAPSE_STYLE = CEH_COLLAPSE_STYLE.replace("#tab-cehealth", "#tab-cecontext")
CTX_COLLAPSE_SCRIPT = (
    CEH_COLLAPSE_SCRIPT.replace("tab-cehealth", "tab-cecontext").replace("#cehealth-", "#cecontext-")
)

# Open by default; failure-modes / links / Slack start collapsed.
CTX_DEFAULT_OPEN = {"cecontext-about", "cecontext-timeline", "cecontext-pastrca", "cecontext-constraints"}

# Timeline lane order (top → bottom) + display label + colour.
_LANES = [
    ("prior_rca", "Prior RCAs", "#9c27b0"),
    ("known_event", "Known events", "#c62828"),
    ("mmp", "MMP doc", "#1565c0"),
    ("slack", "Slack", "#2e7d32"),
]

# Status-chip palettes (icon, fg, bg, border).
_CONSTRAINT_STATUS = {
    "issue": ("⚠️", "#8a5200", "#fff4e5", "#f0c890", "Issue"),
    "none_known": ("✓", "#1b6b3a", "#e7f6ec", "#a9d8ba", "None known"),
    "unknown": ("❓", "#5a6478", "#eef0f4", "#d6dbe8", "Unknown"),
}
_MOVED_STATUS = {
    "moved": ("✓", "#1b6b3a", "#e7f6ec", "#a9d8ba", "Moved"),
    "didnt": ("✗", "#a3262b", "#fdecea", "#e7b0b0", "Didn't move"),
    "partial": ("◑", "#8a5200", "#fff4e5", "#f0c890", "Partial"),
    "unknown": ("❓", "#5a6478", "#eef0f4", "#d6dbe8", "Unknown"),
}


def _chip(palette: dict, key: str) -> str:
    icon, fg, bg, br, label = palette.get(key, palette["unknown"])
    return (f'<span style="display:inline-block;background:{bg};color:{fg};border:1px solid {br};'
            f'border-radius:12px;padding:2px 10px;font-size:12px;font-weight:700;white-space:nowrap;">'
            f'{icon} {label}</span>')


def _first_existing(run_dir: Path, name: str):
    """Subfolder-aware lookup (root first, then organized subfolders for re-renders)."""
    for sub in ("", "data", "reports"):
        p = (run_dir / sub / name) if sub else (run_dir / name)
        if p.exists():
            return p
    return None


def _load_json(run_dir: Path, name: str):
    f = _first_existing(run_dir, name)
    if not f:
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _load_uctx_slots(run_dir: Path) -> dict:
    """Split user_context.md into its `## ` slots (reuses render_ce_health's splitter)."""
    f = _first_existing(run_dir, "user_context.md")
    if not f:
        return {}
    try:
        return _split_user_context_slots(f.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def _read_ce_meta(run_dir: Path):
    """ce_id (for the past-RCA fallback index) + pre/post window (for the timeline band).
    Prefer CE Health's sidecar for ce_id; the timeline JSON owns the window shape."""
    ce_id = None
    window = {}
    sidecar = _load_json(run_dir, "ce_health_report.json")
    if sidecar:
        ce_id = sidecar.get("ce_id") or sidecar.get("metadata", {}).get("combined_entity_id")
    tl = _load_json(run_dir, "ce_context_timeline.json")
    if tl:
        ce_id = ce_id or tl.get("ce_id")
        window = tl.get("window") or {}
    return ce_id, window


# ── §1 About ─────────────────────────────────────────────────────────────────
def _md_block(body: str) -> str:
    body = (body or "").strip()
    return f'<div class="md-content">{render_markdown_to_html(body)}</div>' if body else ""


# ── §3 Recent past RCAs ──────────────────────────────────────────────────────
def build_pastrca_block(run_dir: Path, ce_id) -> str:
    """Per-RCA table from ce_history.json (Window · Pareto finding · Metric impact ·
    Moved? · Why). Falls back to the deterministic prior-run index when the JSON is
    absent, so the section is never empty when prior runs exist."""
    data = _load_json(run_dir, "ce_history.json")
    rcas = (data or {}).get("rcas") or []
    if not rcas:
        return prior_runs_block(run_dir, ce_id) if ce_id is not None else ""
    rows = []
    for r in rcas:
        if not isinstance(r, dict):
            continue
        win = _html.escape(str(r.get("window", "")))
        pareto = _html.escape(str(r.get("pareto_finding", ""))) or "—"
        impact = _html.escape(str(r.get("metric_impact", ""))) or "—"
        why = _html.escape(str(r.get("why", ""))) or "—"
        moved = _chip(_MOVED_STATUS, str(r.get("moved", "unknown")))
        lk_raw = r.get("report_link")
        lk = (f'<a class="ref-link" href="{_html.escape(str(lk_raw))}">open ↗</a>'
              if lk_raw else "")
        rows.append(f"<tr><td>{win}</td><td>{pareto}</td><td>{impact}</td>"
                    f"<td>{moved}</td><td>{why}</td><td>{lk}</td></tr>")
    if not rows:
        return prior_runs_block(run_dir, ce_id) if ce_id is not None else ""
    return ('<div class="md-content"><table><thead><tr>'
            '<th>Window</th><th>Pareto finding</th><th>Metric impact</th>'
            '<th>Moved?</th><th>Why</th><th></th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


# ── §4 Known constraints ─────────────────────────────────────────────────────
def build_constraints_block(run_dir: Path) -> str:
    """Bucketed Q&A from ce_context_constraints.json (Area · Status · Detail · source).
    Absent JSON → an honest 'not captured' line (the section still renders)."""
    data = _load_json(run_dir, "ce_context_constraints.json")
    buckets = (data or {}).get("buckets") or []
    if not buckets:
        return ('<div class="md-content"><p style="color:#8a8a8a;">'
                'No constraints captured for this CE yet.</p></div>')
    rows = []
    for b in buckets:
        if not isinstance(b, dict):
            continue
        area = _html.escape(str(b.get("area", "")))
        chip = _chip(_CONSTRAINT_STATUS, str(b.get("status", "unknown")))
        detail = _html.escape(str(b.get("detail", ""))).strip() or "—"
        srcs = " ".join(
            f'<a class="ref-link" href="{_html.escape(str(s.get("href", "")))}">'
            f'{_html.escape(str(s.get("label", "↗")))}</a>'
            for s in (b.get("sources") or [])
            if isinstance(s, dict) and s.get("href")
        )
        detail_cell = detail + (f' <span style="color:#8a8a8a;">{srcs}</span>' if srcs else "")
        rows.append(f"<tr><td>{area}</td><td>{chip}</td><td>{detail_cell}</td></tr>")
    return ('<div class="md-content"><table><thead><tr>'
            '<th>Constraint area</th><th>Status</th><th>Detail · source</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


# ── §7 Slack (raw provenance) ────────────────────────────────────────────────
def slack_block(run_dir: Path) -> str:
    """Raw Slack standing-context. Honesty rule: absent file → 'unavailable', never faked."""
    f = _first_existing(run_dir, "slack_context.md")
    if not f:
        return ('<div class="md-content"><p style="color:#8a8a8a;">'
                'Slack context unavailable (Slack MCP not connected for this run).</p></div>')
    try:
        t = f.read_text(encoding="utf-8").strip()
    except Exception:  # noqa: BLE001
        return ""
    if not t:
        return ""
    return f'<div class="md-content">{render_markdown_to_html(t)}</div>'


# ── §2 Timeline ──────────────────────────────────────────────────────────────
def _event_date(e: dict):
    """The point date for an event — its `date`, or the start of its `date_range`."""
    if e.get("date"):
        return e["date"]
    rng = e.get("date_range")
    if isinstance(rng, list) and rng:
        return rng[0]
    return None


def _week_key(dstr: str) -> str:
    """Monday of the ISO week containing `dstr` (YYYY-MM-DD) — the weekly bucket."""
    x = _dt.date.fromisoformat(dstr)
    return (x - _dt.timedelta(days=x.weekday())).isoformat()


def _trunc(s: str, n: int = 46) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _timeline_table(events, latest_n: int = 12) -> str:
    """A chronological (latest-first) list of EVERY dated context signal across all
    lanes — so the reader can scan all messages at once without clicking individual
    bubbles (the complaint the swimlane couldn't solve when bubbles overlap). One row
    per event: Date · What we found · Source (lane-coloured dot + label + ↗ link).
    Shows the latest `latest_n`; older rows collapse behind a 'Show older' toggle so
    the section stays compact. Undated events sort to the end with a '—' date."""
    lane_meta = {k: (label, color) for k, label, color in _LANES}
    rows = [(_event_date(e), e) for e in events if isinstance(e, dict)]
    dated = sorted((r for r in rows if r[0]), key=lambda r: r[0], reverse=True)
    undated = [r for r in rows if not r[0]]
    ordered = dated + undated
    if not ordered:
        return ""

    def _row_html(d, e, hidden):
        label, color = lane_meta.get(e.get("lane"), (str(e.get("lane") or "—"), "#888"))
        src = ('<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
               'background:{c};margin-right:6px;vertical-align:middle;"></span>{l}').format(
                   c=color, l=_html.escape(label))
        link = e.get("link")
        if link:
            src += ' <a class="ref-link" href="{h}" target="_blank">↗</a>'.format(
                h=_html.escape(str(link)))
        cls = ' class="cecontext-tl-more" style="display:none;"' if hidden else ''
        return ('<tr{cls}><td style="white-space:nowrap;color:#5a6478;vertical-align:top;">{d}</td>'
                '<td style="vertical-align:top;">{t}</td>'
                '<td style="white-space:nowrap;vertical-align:top;">{s}</td></tr>').format(
                    cls=cls, d=_html.escape(str(d or "—")),
                    t=_html.escape(str(e.get("label", ""))), s=src)

    visible, hidden = ordered[:latest_n], ordered[latest_n:]
    body = "".join(_row_html(d, e, False) for d, e in visible)
    body += "".join(_row_html(d, e, True) for d, e in hidden)
    more_btn = ""
    if hidden:
        more_btn = (
            '<button onclick="var t=document.querySelectorAll(\'.cecontext-tl-more\');'
            'for(var i=0;i<t.length;i++){t[i].style.display=\'\';}this.style.display=\'none\';" '
            'style="margin-top:8px;padding:5px 12px;font-size:12px;border:1px solid #cbd2e0;'
            'border-radius:6px;background:#f7f8fb;color:#3a4a6a;cursor:pointer;">'
            'Show ' + str(len(hidden)) + ' older ▾</button>')
    return (
        '<div style="margin-top:16px;">'
        '<div style="font-size:13px;font-weight:600;color:#1a1a2e;margin-bottom:6px;">'
        'All changes — chronological (latest first)</div>'
        '<table><thead><tr><th>Date</th><th>What we found</th><th>Source</th></tr></thead>'
        '<tbody>' + body + '</tbody></table>' + more_btn + '</div>')


def build_timeline_block(run_dir: Path, window: dict) -> str:
    """Weekly **bubble-density** swimlane of dated context events: one row per source
    bucket, bubble size = how many signals fell in that week (so dense clusters — e.g.
    a burst of Slack threads — read as one big bubble instead of an unreadable pile of
    overlapping dots). The pre/post analysis window is shaded behind. Hover previews the
    week's events; **clicking a bubble lists them in the panel below, with working ↗
    links** (a hover tooltip can't hold a clickable link and gets clipped at the edge).
    Returns '' when there is nothing dated to plot (graceful — the tables still render)."""
    data = _load_json(run_dir, "ce_context_timeline.json")
    if not data:
        return ""
    events = [e for e in (data.get("events") or []) if isinstance(e, dict)]
    if not events:
        return ""  # nothing dated → no chart; tables still render

    win = window or data.get("window") or {}

    lanes_present = []
    traces = []
    detail = []  # detail[curveNumber][pointNumber] = [{d,t,l}, ...] — robust click lookup
    for key, label, color in _LANES:
        # bin this lane's events by week
        agg = {}
        for e in events:
            if e.get("lane") != key:
                continue
            d = _event_date(e)
            if not d:
                continue  # undated → skip (stays in the tables)
            agg.setdefault(_week_key(d), []).append(e)
        if not agg:
            continue
        weeks = sorted(agg)
        counts = [len(agg[w]) for w in weeks]
        hover = ["<br>".join("• " + _html.escape(_trunc(str(ev.get("label", "")))) for ev in agg[w])
                 for w in weeks]
        detail.append([[{"d": _html.escape(str(_event_date(ev) or "")),
                         "t": _html.escape(str(ev.get("label", ""))),
                         "l": _html.escape(str(ev.get("link") or ""))}
                        for ev in agg[w]] for w in weeks])
        lanes_present.append(label)
        traces.append({
            "type": "scatter", "mode": "markers", "name": label,
            "x": weeks, "y": [label] * len(weeks),
            "text": hover, "hovertemplate": "%{text}<extra>" + label + "</extra>",
            "marker": {"size": [13 + 8 * (m - 1) for m in counts], "color": color,
                       "line": {"width": 1.5, "color": "#fff"}, "opacity": 0.9},
        })
    if not traces:
        return ""

    shapes, annos = [], []

    def _band(x0, x1, fill, name):
        if x0 and x1:
            shapes.append({"type": "rect", "xref": "x", "yref": "paper",
                           "x0": x0, "x1": x1, "y0": 0, "y1": 1,
                           "fillcolor": fill, "opacity": 0.5, "line": {"width": 0}, "layer": "below"})
            annos.append({"x": x0, "xref": "x", "y": 1.04, "yref": "paper",
                          "text": name, "showarrow": False, "xanchor": "left",
                          "font": {"size": 10, "color": "#6a7690"}})
    _band(win.get("pre_start"), win.get("pre_end"), "#eceff1", "Pre")
    _band(win.get("post_start"), win.get("post_end"), "#e3f2fd", "Post")

    height = 110 + 46 * max(1, len(lanes_present))
    layout = {
        "height": height, "autosize": True,
        "margin": {"l": 110, "r": 40, "t": 26, "b": 40},
        "plot_bgcolor": "#fff", "paper_bgcolor": "#fff",
        "font": {"family": "-apple-system,sans-serif", "size": 11, "color": "#1a1a2e"},
        "showlegend": False, "hovermode": "closest",
        # left-aligned, never-truncated hover preview (the full detail is the click panel)
        "hoverlabel": {"align": "left", "bgcolor": "#fff", "bordercolor": "#ccc",
                       "font": {"size": 12, "color": "#1a1a2e"}, "namelength": -1},
        "xaxis": {"type": "date", "gridcolor": "#eef"},
        "yaxis": {"type": "category", "categoryorder": "array",
                  "categoryarray": list(reversed(lanes_present)), "automargin": True},
        "shapes": shapes, "annotations": annos,
    }

    # Click a bubble → list that week's events (with ↗ links) in the panel below. The
    # detail lookup is keyed by [curveNumber][pointNumber] (NOT Plotly customdata, which
    # mangles the ragged per-bubble event lists). Scoped to this tab's element ids.
    return (
        '<div id="chart-cecontext-timeline" class="chart-container" style="width:100%"></div>'
        '<div id="cecontext-timeline-detail" style="margin-top:10px;padding:12px 16px;'
        'background:#f7f8fb;border:1px solid #e6e9f0;border-radius:8px;font-size:13px;'
        'color:#5a6478;min-height:42px;">👆 Click any bubble to read that week\'s events here '
        '(with links).</div>'
        + _timeline_table(events) +
        '<script>(function(){var el=document.getElementById("chart-cecontext-timeline");'
        f'var DETAIL={json.dumps(detail)};'
        f'Plotly.newPlot(el,{json.dumps(traces)},{json.dumps(layout)},'
        '{responsive:true,displayModeBar:false});'
        'el.on("plotly_click",function(d){var p=d.points[0];'
        'var evs=(DETAIL[p.curveNumber]||[])[p.pointNumber]||[];var lane=p.data.name||"";'
        'var h="<div style=\\"font-weight:700;color:#1a1a2e;margin-bottom:6px;\\">"+lane+'
        '" \\u00b7 week of "+p.x+"</div>";'
        'h+=evs.map(function(e){var lk=e.l?" <a href=\\""+e.l+"\\" target=\\"_blank\\" '
        'style=\\"color:#2e7d32;text-decoration:none;\\">\\u2197</a>":"";'
        'return "<div style=\\"margin:4px 0;color:#1a1a2e;\\">\\u2022 <b>"+e.d+"</b> \\u2014 "'
        '+e.t+lk+"</div>";}).join("");'
        'document.getElementById("cecontext-timeline-detail").innerHTML=h;});})();</script>'
    )


def build_fragment(run_dir: Path) -> str:
    ce_id, window = _read_ce_meta(run_dir)
    slots = _load_uctx_slots(run_dir)

    about = _md_block(slots.get("About this CE"))
    timeline = build_timeline_block(run_dir, window)
    pastrca = build_pastrca_block(run_dir, ce_id)
    constraints = build_constraints_block(run_dir)   # always renders (table or honest note)
    failuremodes = _md_block(slots.get("Known failure modes"))
    links = _uctx_links_block(slots.get("Important links", "")) if slots.get("Important links") else ""
    slack = slack_block(run_dir)

    # (anchor, title, inner, always-render?) — order = stakeholder template.
    candidates = [
        ("cecontext-about", "About this CE", about, False),
        ("cecontext-timeline", "Timeline of changes", timeline, False),
        ("cecontext-pastrca", "Recent past RCAs", pastrca, False),
        ("cecontext-constraints", "Known constraints", constraints, True),
        ("cecontext-failuremodes", "Known failure modes", failuremodes, False),
        ("cecontext-links", "Important links", links, False),
        ("cecontext-slack", "Slack standing context", slack, False),
    ]
    blocks = [(bid, block(title, bid, inner))
              for bid, title, inner, always in candidates
              if always or (inner and inner.strip())]

    if not blocks:
        body = ('<div class="analysis-block" id="cecontext-empty"><div class="ceh-body">'
                '<div class="md-content"><p style="color:#8a8a8a;">No context captured for this '
                'CE yet — no analyst notes, prior RCAs, or Slack signals.</p></div></div></div>')
    else:
        def _collapse(bid, frag):
            if bid in CTX_DEFAULT_OPEN:
                return frag
            frag = frag.replace(f'<div class="analysis-block" id="{bid}">',
                                f'<div class="analysis-block ceh-collapsed" id="{bid}">', 1)
            frag = frag.replace('class="ceh-toggle" aria-expanded="true"',
                                'class="ceh-toggle" aria-expanded="false"', 1)
            return frag
        body = "".join(_collapse(bid, frag) for bid, frag in blocks)

    resize = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "if(window.Plotly)document.querySelectorAll('#tab-cecontext .js-plotly-plot')"
              ".forEach(function(el){try{window.Plotly.Plots.resize(el);}catch(e){}});},200);});</script>")
    return (CTX_TABLE_STYLE + CTX_COLLAPSE_STYLE + body + CTX_COLLAPSE_SCRIPT + resize)


def _write_standalone(run_dir: Path, frag: str):
    """Wrap the body fragment into a full openable `report.html` (standalone runs).
    Reuses the shared `standalone_report.wrap_fragment`; graceful if it's unreachable."""
    try:
        from standalone_report import wrap_fragment, build_header_meta, build_rich_header
    except Exception as e:  # noqa: BLE001
        print(f"standalone wrap unavailable ({e}) — fragment written, no report.html")
        return
    ce_id, window = _read_ce_meta(run_dir)  # window = timeline {pre_start,pre_end,post_start,post_end}
    sc = _load_json(run_dir, "ce_health_report.json") or {}
    cm = _load_json(run_dir, "ce_context_meta.json") or {}   # standalone CE-metadata (the 5 pills)
    tl = _load_json(run_dir, "ce_context_timeline.json") or {}
    # Metadata source for the 5 CE pills: prefer CE Health's sidecar; else the
    # ce_context_meta.json the standalone /ce-context flow writes from its dim lookup.
    md = (sc.get("metadata") if sc else None) or cm or {}
    ce_id = ce_id or sc.get("ce_id") or cm.get("ce_id") or md.get("combined_entity_id")
    ce_name = (sc.get("ce_name") or cm.get("combined_entity_name") or cm.get("ce_name")
               or tl.get("ce_name") or "")
    # Normalize windows to {current,prior} (the build_header_meta shape): prefer the
    # sidecar's; else derive from the timeline JSON's pre/post window.
    windows = sc.get("windows")
    if not windows and window.get("post_start") and window.get("post_end"):
        windows = {"current": [window["post_start"], window["post_end"]]}
        if window.get("pre_start") and window.get("pre_end"):
            windows["prior"] = [window["pre_start"], window["pre_end"]]
    meta = build_header_meta(md, ce_id=ce_id, ce_name=ce_name, windows=windows)
    title = f"CE Context — {meta.get('combined_entity_name') or ('CE ' + str(ce_id) if ce_id else 'CE')}"
    banner = build_rich_header(meta, eyebrow="CE Context")
    doc = wrap_fragment(frag, scope_id="tab-cecontext", title=title, banner_html=banner)
    out = run_dir / "report.html"
    out.write_text(doc, encoding="utf-8")
    print(f"wrote {out} ({len(doc)} bytes) [standalone]")


def main():
    ap = argparse.ArgumentParser(description="Render the CE Context tab fragment.")
    ap.add_argument("--run-dir", required=True, help="Run directory with the context artifacts.")
    ap.add_argument("--standalone", action="store_true",
                    help="Also wrap the fragment into an openable standalone report.html.")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).expanduser()
    frag = build_fragment(run_dir)
    out = run_dir / "ce_context_report.html"
    out.write_text(frag, encoding="utf-8")
    print(f"wrote {out} ({len(frag)} bytes)")
    if args.standalone:
        _write_standalone(run_dir, frag)


if __name__ == "__main__":
    main()
