"""
render.py — Component library. Assembles HTML from report_spec.json + summary.json.

Claude writes report_spec.json describing which components to show and in what order.
This script renders each component from summary data and injects them into report.html.

Usage:
  python render.py
    --summary  /tmp/cvr_rca_167/summary.json
    --spec     /tmp/cvr_rca_167/report_spec.json
    --output   /tmp/cvr_rca_167/report.html

Spec format — all fields are FLAT at the top level (no nested "params" key):
  {"component": "dimension_table", "step": "S2C", "dim": "device"}
  {"component": "callout", "variant": "finding", "text": "..."}
  {"component": "trend_chart", "step": "S2C"}

Component types:
  executive_summary    — findings: ["bullet 1", "bullet 2", ...] — leadership summary card
  metric_cards         — CVR/LP2S/S2C/C2O headline cards
  shapley_waterfall    — Horizontal bar chart of step contributions
  mbho_channel_table   — MB vs HO and Paid vs Organic mix + conversion effect tables
  dimension_table      — step: "LP2S"|"S2C"|"C2O", dim: "language"|"page_type"|"device"
  dimension_table_pair — step: "LP2S"|"S2C"|"C2O", dims: ["device","page_type"] — two tables side by side
  experience_table     — step: "S2C"|"C2O" — top experiences by |Δrate| for that step
  trend_chart          — step: "LP2S"|"S2C"|"C2O" — daily rate pre vs post
  c2o_sub_cards        — C2A and A2O metric cards
  section_header       — title: "...", subtitle: "..." — visual section divider (no wrapper)
  callout              — variant: "insight"|"warning"|"finding"|"mix_note", text: "..."
                         optional: heading: "..." (bold hero line), label: "..." (small-caps context tag)
  action_cards         — actions: [{finding, cause, action, dri}, ...]

Escape-hatch components (v1.15) — for novel investigation findings the
built-ins can't express. Use sparingly; standard components remain the default.
  analysis_block       — title, verdict?, verdict_class?, body_html, anchor_id?
                         wraps arbitrary HTML in the standard Section-3 chrome
  raw_html             — html, chart_id?, fig_json?
                         pure passthrough, no wrapper; for full-bleed callouts
                         or custom Plotly containers that need their own layout
"""

from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Design tokens
# ─────────────────────────────────────────────────────────────────────────────

C = {
    "red":     "#E53935",
    "green":   "#43A047",
    "blue":    "#1976D2",
    "amber":   "#F9A825",
    "grey":    "#757575",
    "light":   "#F5F5F5",
    "white":   "#FFFFFF",
    "border":  "#E0E0E0",
    "text":    "#212121",
    "subtext": "#616161",
}

CALLOUT_STYLES = {
    "insight":       {"border": C["blue"],  "bg": "#E3F2FD", "icon": "💡"},
    "warning":       {"border": C["amber"], "bg": "#FFF8E1", "icon": "⚠️"},
    "finding":       {"border": C["red"],   "bg": "#FFEBEE", "icon": "🔍"},
    "info":          {"border": C["grey"],  "bg": C["light"], "icon": "ℹ️"},
    "mix_note":      {"border": C["grey"],  "bg": C["light"], "icon": "ℹ️"},
    "interpretation":{"border": C["green"], "bg": "#F1F8E9", "icon": "✅"},
}


# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def pct(v, d=1):
    if v is None: return "—"
    return f"{v * 100:.{d}f}%"

def compact_num(v):
    """Format integer counts as 1.2K / 3.4M for readability."""
    if v is None: return "—"
    v = int(v)
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v / 1_000:.1f}K"
    return str(v)

def pp(v, d=2):
    """Format as percentage-point delta with sign."""
    if v is None: return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v * 100:.{d}f}pp"

def contrib_pct(effect, total_delta, d=0):
    """Format an effect as % of total |ΔCVR|. Shows share of the total change magnitude."""
    if effect is None or total_delta is None or total_delta == 0:
        return "—"
    val = effect / abs(total_delta) * 100
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.{d}f}%"

def delta_badge(v):
    if v is None: return ""
    colour = C["green"] if v >= 0 else C["red"]
    return (
        f'<span style="background:{colour};color:#fff;padding:2px 7px;'
        f'border-radius:10px;font-size:11px;font-weight:600;white-space:nowrap;">'
        f'{pp(v)}</span>'
    )

def inline_bar(delta, max_abs, width_px=60):
    """Small coloured bar proportional to |delta| relative to max_abs."""
    if delta is None or max_abs == 0:
        return ""
    w = max(2, int(abs(delta) / max_abs * width_px))
    colour = C["red"] if delta < 0 else C["green"]
    return (
        f'<div style="display:inline-block;width:{w}px;height:6px;'
        f'background:{colour};border-radius:3px;vertical-align:middle;margin-left:4px;"></div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Spec normalizer — accept both flat and params-nested formats
# ─────────────────────────────────────────────────────────────────────────────

def normalize_spec_item(item: dict) -> dict:
    """
    Claude sometimes writes {component, params: {step, dim, ...}} and sometimes
    writes {component, step, dim, ...} directly. Merge params into the top level
    so all downstream code sees a flat dict regardless of how it was written.
    """
    flat = dict(item)
    params = flat.pop("params", None)
    if isinstance(params, dict):
        flat.update(params)
    # Normalise "type" → "component" alias
    if "type" in flat and "component" not in flat:
        flat["component"] = flat.pop("type")
    return flat


# ─────────────────────────────────────────────────────────────────────────────
# Component renderers
# ─────────────────────────────────────────────────────────────────────────────

def render_metric_cards(summary: dict) -> tuple[str, list]:
    headline = summary.get("headline", {})
    pre  = headline.get("pre",  {})
    post = headline.get("post", {})
    d    = headline.get("delta", {})

    def card(label, pre_val, post_val, delta_val, fmt=pct):
        return f"""
<div style="background:{C['white']};border:1px solid {C['border']};border-radius:10px;
            padding:18px 22px;min-width:150px;flex:1;">
  <div style="font-size:11px;color:{C['subtext']};text-transform:uppercase;
              letter-spacing:.06em;margin-bottom:8px;">{label}</div>
  <div style="font-size:28px;font-weight:800;color:{C['text']};line-height:1;">
    {fmt(post_val)}
  </div>
  <div style="font-size:12px;color:{C['subtext']};margin-top:6px;display:flex;
              align-items:center;gap:6px;">
    <span>Pre: {fmt(pre_val)}</span>
    {delta_badge(delta_val)}
  </div>
</div>"""

    def traffic_card():
        pre_u   = pre.get("users_lp", 0)
        post_u  = post.get("users_lp", 0)
        delta_u = (post_u or 0) - (pre_u or 0)
        colour  = C["green"] if delta_u >= 0 else C["red"]
        sign    = "+" if delta_u >= 0 else ""
        badge   = (f'<span style="background:{colour};color:#fff;padding:2px 7px;'
                   f'border-radius:10px;font-size:11px;font-weight:600;">'
                   f'{sign}{compact_num(delta_u)}</span>')
        return f"""
<div style="background:{C['white']};border:1px solid {C['border']};border-radius:10px;
            padding:18px 22px;min-width:150px;flex:1;">
  <div style="font-size:11px;color:{C['subtext']};text-transform:uppercase;
              letter-spacing:.06em;margin-bottom:8px;">LP Traffic</div>
  <div style="font-size:28px;font-weight:800;color:{C['text']};line-height:1;">
    {compact_num(post_u)}
  </div>
  <div style="font-size:12px;color:{C['subtext']};margin-top:6px;display:flex;
              align-items:center;gap:6px;">
    <span>Pre: {compact_num(pre_u)}</span>
    {badge}
  </div>
</div>"""

    cards = (
        card("CVR (LP→Order)",       pre.get("cvr"),  post.get("cvr"),  d.get("cvr"),  lambda v: pct(v, 2))
        + card("LP → Select",        pre.get("lp2s"), post.get("lp2s"), d.get("lp2s"))
        + card("Select → Checkout",  pre.get("s2c"),  post.get("s2c"),  d.get("s2c"))
        + card("Checkout → Order",   pre.get("c2o"),  post.get("c2o"),  d.get("c2o"))
        + traffic_card()
    )
    html = f'<div style="display:flex;flex-wrap:wrap;gap:12px;">{cards}</div>'
    return html, []


def render_shapley_waterfall(summary: dict) -> tuple[str, list]:
    shapley = summary.get("shapley")
    if not shapley:
        return "<p>Shapley data not available.</p>", []

    steps  = ["LP2S", "S2C", "C2O"]
    sv     = shapley.get("shapley", {})
    pct_c  = shapley.get("pct_contribution", {})
    sig    = set(shapley.get("significant_steps", []))
    total  = shapley.get("total_delta", 0)

    # Significance pills
    pills = ""
    for step in steps:
        v      = sv.get(step, 0)
        share  = abs(pct_c.get(step, 0))
        is_sig = step in sig
        bg     = (C["red"] if v < 0 else C["green"]) if is_sig else C["light"]
        fg     = C["white"] if is_sig else C["subtext"]
        tag    = '<div style="font-size:10px;margin-top:3px;opacity:.85;">▲ Significant</div>' if is_sig else ""
        pills += f"""
<div style="background:{bg};color:{fg};border-radius:8px;padding:12px 16px;
            flex:1;min-width:120px;text-align:center;">
  <div style="font-size:11px;text-transform:uppercase;letter-spacing:.06em;">{step}</div>
  <div style="font-size:22px;font-weight:800;margin:4px 0;">{pp(v, 3)}</div>
  <div style="font-size:12px;">{share:.0%} of Δ</div>
  {tag}
</div>"""

    chart_id = "shapley-waterfall"
    fig = {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "y": [f"{s}  ({pct_c.get(s, 0):.0%})" for s in steps],
            "x": [sv.get(s, 0) for s in steps],
            "marker": {
                "color": [C["red"] if sv.get(s, 0) < 0 else C["green"] for s in steps]
            },
            "text": [pp(sv.get(s, 0), 3) for s in steps],
            "textposition": "outside",
        }],
        "layout": {
            "title": {"text": f"Shapley Attribution — Total ΔCVR = {pp(total, 3)}", "font": {"size": 13}},
            "xaxis": {"title": "CVR contribution", "zeroline": True, "zerolinewidth": 2,
                      "zerolinecolor": C["border"]},
            "yaxis": {"autorange": "reversed"},
            "plot_bgcolor": C["white"], "paper_bgcolor": C["white"],
            "font": {"color": C["text"], "family": "Inter, system-ui, sans-serif"},
            "height": 220, "margin": {"l": 120, "r": 80, "t": 45, "b": 40},
            "showlegend": False,
        }
    }

    html = (
        f'<div style="display:flex;gap:10px;margin-bottom:14px;">{pills}</div>'
        f'<div id="{chart_id}" style="height:220px;"></div>'
    )
    return html, [(chart_id, fig)]


def render_mbho_channel_table(summary: dict) -> tuple[str, list]:
    total_delta = (summary.get("headline") or {}).get("delta", {}).get("cvr") or 0

    def _mix_cell(effect):
        """Coloured % contribution badge. Green = pushed CVR up, red = pushed CVR down."""
        if effect is None:
            return "—"
        colour = C["green"] if effect >= 0 else C["red"]
        val    = contrib_pct(effect, total_delta)
        return (f'<span style="color:{colour};font-weight:600;">{val}</span>')

    def _table(rows, title):
        if not rows:
            return ""
        max_abs_cvr = max((abs(rr.get("post_cvr", 0) - rr.get("pre_cvr", 0)) for rr in rows), default=1) or 1

        header = f"""
<div style="font-size:12px;font-weight:700;color:{C['subtext']};
            text-transform:uppercase;margin:14px 0 6px;">{title}</div>"""
        th = lambda t, tip="": (
            f'<th style="padding:7px 12px;text-align:left;font-size:11px;'
            f'color:{C["subtext"]};font-weight:600;border-bottom:2px solid {C["border"]};'
            f'white-space:nowrap;" title="{tip}">{t}</th>'
        )
        thead = (
            "<thead><tr>"
            + th("Segment")
            + th("Pre Traffic%")
            + th("Post Traffic%")
            + th("Δ Traffic%")
            + th("Pre CVR")
            + th("Post CVR")
            + th("Δ CVR")
            + th("Mix % of ΔCVR",  "How much of total CVR change is explained by traffic share shifting to/from this segment")
            + th("Conv. % of ΔCVR","How much of total CVR change is explained by conversion rate changing within this segment")
            + "</tr></thead>"
        )

        tbody = ""
        for i, rr in enumerate(rows):
            bg        = C["light"] if i % 2 else C["white"]
            mix       = rr.get("mix") or {}
            delta_cvr = (rr.get("post_cvr") or 0) - (rr.get("pre_cvr") or 0)
            tbody += f"""
<tr style="background:{bg};">
  <td style="padding:7px 12px;font-weight:600;">{rr.get('segment','')}</td>
  <td style="padding:7px 12px;">{pct(rr.get('pre_share'))}</td>
  <td style="padding:7px 12px;">{pct(rr.get('post_share'))}</td>
  <td style="padding:7px 12px;">{delta_badge(rr.get('post_share', 0) - rr.get('pre_share', 0))}</td>
  <td style="padding:7px 12px;">{pct(rr.get('pre_cvr'), 2)}</td>
  <td style="padding:7px 12px;font-weight:700;">{pct(rr.get('post_cvr'), 2)}</td>
  <td style="padding:7px 12px;">{delta_badge(delta_cvr)}{inline_bar(delta_cvr, max_abs_cvr)}</td>
  <td style="padding:7px 12px;">{_mix_cell(mix.get('mix_effect'))}</td>
  <td style="padding:7px 12px;">{_mix_cell(mix.get('conversion_effect'))}</td>
</tr>"""

        return (header + f'<div style="overflow-x:auto;"><table style="border-collapse:collapse;'
                f'width:100%;font-size:13px;color:{C["text"]};">{thead}<tbody>{tbody}</tbody>'
                f'</table></div>')

    html  = _table(summary.get("mbho_mix", []),    "Microbrand (MB) vs Headout (HO)")
    html += _table(summary.get("channel_mix", []), "Paid vs Organic")
    return html, []


def render_dimension_table(summary: dict, step: str, dim: str, title: str = "") -> tuple[str, list]:
    rows = (summary.get("dimensions") or {}).get(step, {}).get(dim, [])
    if not rows:
        return f'<p style="color:{C["subtext"]};font-style:italic;">No {dim} data for {step}.</p>', []

    title = title or f"{step} by {dim.replace('_', ' ').title()}"

    # Sort by pre_users descending so largest segments appear first.
    # aggregate.py already picked the top-5 by |delta|; we just reorder for readability.
    rows = sorted(rows, key=lambda rr: rr.get("pre_users") or 0, reverse=True)

    max_abs = max((abs(rr.get("delta") or 0) for rr in rows), default=1) or 1

    th = lambda t: (f'<th style="padding:7px 12px;text-align:left;font-size:11px;'
                    f'color:{C["subtext"]};font-weight:600;border-bottom:2px solid {C["border"]};'
                    f'white-space:nowrap;">{t}</th>')
    thead = ("<thead><tr>"
             + th("Value") + th("Pre Users") + th("Post Users")
             + th("Pre Rate") + th("Post Rate") + th("Δ Rate")
             + "</tr></thead>")

    tbody = ""
    for i, rr in enumerate(rows):
        bg    = C["light"] if i % 2 else C["white"]
        delta = rr.get("delta")
        tbody += f"""
<tr style="background:{bg};">
  <td style="padding:7px 12px;font-weight:600;">{rr.get('value','')}</td>
  <td style="padding:7px 12px;color:{C['subtext']}">{compact_num(rr.get('pre_users'))}</td>
  <td style="padding:7px 12px;color:{C['subtext']}">{compact_num(rr.get('post_users'))}</td>
  <td style="padding:7px 12px;">{pct(rr.get('pre_rate'))}</td>
  <td style="padding:7px 12px;font-weight:700;">{pct(rr.get('post_rate'))}</td>
  <td style="padding:7px 12px;white-space:nowrap;">
    {delta_badge(delta)}{inline_bar(delta, max_abs)}
  </td>
</tr>"""

    # Title comes from the section wrapper (SECTION_TITLES), not repeated here
    html = (
        f'<div style="overflow-x:auto;"><table style="border-collapse:collapse;width:100%;'
        f'font-size:13px;color:{C["text"]};">{thead}<tbody>{tbody}</tbody></table></div>'
    )
    return html, []


def render_trend_chart(summary: dict, step: str) -> tuple[str, list]:
    trend = summary.get("trend", {})
    rate_key = {"LP2S": "lp2s_rate", "S2C": "s2c_rate", "C2O": "c2o_rate"}[step]

    def series(rows):
        return (
            [rr["date"] for rr in rows if rr.get(rate_key) is not None],
            [rr[rate_key] for rr in rows if rr.get(rate_key) is not None],
        )

    pre_x,  pre_y  = series(trend.get("pre",  []))
    post_x, post_y = series(trend.get("post", []))

    chart_id = f"trend-{step.lower()}"
    fig = {
        "data": [
            {
                "type": "scatter", "mode": "lines+markers",
                "name": "Pre period",
                "x": pre_x, "y": pre_y,
                "line": {"color": C["grey"], "dash": "dash", "width": 2},
                "marker": {"size": 5, "color": C["grey"]},
            },
            {
                "type": "scatter", "mode": "lines+markers",
                "name": "Post period",
                "x": post_x, "y": post_y,
                "line": {"color": C["blue"], "width": 2},
                "marker": {"size": 5, "color": C["blue"]},
            },
        ],
        "layout": {
            "title": {"text": f"{step} Daily Rate — Pre (dashed) vs Post", "font": {"size": 13}},
            "yaxis": {"tickformat": ".1%", "title": f"{step} Rate"},
            "xaxis": {"title": "Date"},
            "plot_bgcolor": C["white"], "paper_bgcolor": C["white"],
            "font": {"color": C["text"], "family": "Inter, system-ui, sans-serif"},
            "height": 240, "margin": {"l": 60, "r": 20, "t": 45, "b": 50},
            "legend": {"orientation": "h", "y": -0.3},
        }
    }
    html = f'<div id="{chart_id}" style="height:240px;"></div>'
    return html, [(chart_id, fig)]


def render_c2o_sub_cards(summary: dict) -> tuple[str, list]:
    c2o = summary.get("c2o_sub")
    if not c2o:
        return "", []

    pre  = c2o.get("pre",  {})
    post = c2o.get("post", {})

    def card(label, pre_v, post_v, delta_v):
        return f"""
<div style="background:{C['white']};border:1px solid {C['border']};border-radius:10px;
            padding:18px 22px;flex:1;min-width:180px;">
  <div style="font-size:11px;color:{C['subtext']};text-transform:uppercase;
              letter-spacing:.06em;margin-bottom:8px;">{label}</div>
  <div style="font-size:28px;font-weight:800;color:{C['text']};line-height:1;">
    {pct(post_v)}
  </div>
  <div style="font-size:12px;color:{C['subtext']};margin-top:6px;
              display:flex;align-items:center;gap:6px;">
    <span>Pre: {pct(pre_v)}</span>
    {delta_badge(delta_v)}
  </div>
</div>"""

    cards_html = (
        f'<div style="display:flex;flex-wrap:wrap;gap:12px;">'
        + card("Checkout → Attempt (C2A)", pre.get("c2a"), post.get("c2a"), c2o.get("delta_c2a"))
        + card("Attempt → Order (A2O)",    pre.get("a2o"), post.get("a2o"), c2o.get("delta_a2o"))
        + "</div>"
    )
    # Append under-development banner: inventory level check at checkout
    cards_html += render_under_development_banner(
        "Inventory Level Check at Checkout",
        "We're building a sub-analysis that correlates C2A abandonment with "
        "real-time availability constraints at checkout — identifying whether users "
        "drop off because their selected slot/variant became unavailable during the "
        "booking flow. DRI: Supply / Inventory."
    )
    return cards_html, []


def render_executive_summary(findings: list) -> tuple[str, list]:
    """Leadership-facing summary card: 3–5 crisp bullets above everything else."""
    bullets = "".join(
        f'<li style="margin-bottom:10px;padding-left:8px;border-left:3px solid {C["blue"]};'
        f'line-height:1.65;font-size:14px;color:{C["text"]};">{f}</li>'
        for f in (findings or [])
    )
    html = (
        f'<div style="background:{C["white"]};border:1px solid {C["border"]};'
        f'border-radius:10px;padding:24px 28px;">'
        f'<div style="font-size:11px;font-weight:700;color:{C["subtext"]};'
        f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;">Executive Summary</div>'
        f'<ul style="list-style:none;padding:0;margin:0;">{bullets}</ul>'
        f'</div>'
    )
    return html, []


def render_section_header(title: str, subtitle: str = "") -> tuple[str, list]:
    """Bold section divider for grouping related deep-dive components."""
    sub = (f'<div style="font-size:13px;color:{C["subtext"]};margin-top:5px;">{subtitle}</div>'
           if subtitle else "")
    html = (
        f'<div style="margin:44px 0 20px;padding-bottom:12px;'
        f'border-bottom:2px solid {C["border"]};">'
        f'<div style="font-size:19px;font-weight:800;color:{C["text"]};">{title}</div>'
        f'{sub}</div>'
    )
    return html, []


def render_under_development_banner(label: str, description: str) -> str:
    """Small inline banner indicating a planned analysis not yet available."""
    return (
        f'<div style="display:flex;align-items:flex-start;gap:10px;'
        f'background:#F8F4FF;border:1px dashed #9C6FE0;border-radius:8px;'
        f'padding:11px 16px;margin-top:14px;">'
        f'<span style="font-size:14px;flex-shrink:0;">🔬</span>'
        f'<div>'
        f'<div style="font-size:11px;font-weight:700;color:#6800f4;'
        f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px;">'
        f'Sub-skill under development · {label}</div>'
        f'<div style="font-size:13px;color:#424242;line-height:1.5;">{description}</div>'
        f'</div>'
        f'</div>'
    )


def render_experience_table(summary: dict, step: str) -> tuple[str, list]:
    """Top experiences by |Δrate| for a given funnel step (S2C or C2O only)."""
    rows = (summary.get("experiences") or {}).get(step, [])
    if not rows:
        return (f'<p style="color:{C["subtext"]};font-style:italic;">'
                f'No experience-level data for {step}.</p>'), []

    # Sort by pre_users descending (largest experience first)
    rows = sorted(rows, key=lambda rr: rr.get("pre_users") or 0, reverse=True)
    max_abs = max((abs(rr.get("delta") or 0) for rr in rows), default=1) or 1

    step_label = {"S2C": "Select → Checkout", "C2O": "Checkout → Order"}.get(step, step)
    th = lambda t: (f'<th style="padding:7px 12px;text-align:left;font-size:11px;'
                    f'color:{C["subtext"]};font-weight:600;border-bottom:2px solid {C["border"]};'
                    f'white-space:nowrap;">{t}</th>')
    thead = ("<thead><tr>"
             + th("Experience") + th("Pre Users") + th("Post Users")
             + th(f"Pre {step_label}") + th(f"Post {step_label}") + th("Δ Rate")
             + "</tr></thead>")

    tbody = ""
    for i, rr in enumerate(rows):
        bg    = C["light"] if i % 2 else C["white"]
        delta = rr.get("delta")
        tbody += f"""
<tr style="background:{bg};">
  <td style="padding:7px 12px;font-weight:600;max-width:280px;
             overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
      title="{rr.get('experience_name','')}">
    {rr.get('experience_name','')}
  </td>
  <td style="padding:7px 12px;color:{C['subtext']}">{compact_num(rr.get('pre_users'))}</td>
  <td style="padding:7px 12px;color:{C['subtext']}">{compact_num(rr.get('post_users'))}</td>
  <td style="padding:7px 12px;">{pct(rr.get('pre_rate'))}</td>
  <td style="padding:7px 12px;font-weight:700;">{pct(rr.get('post_rate'))}</td>
  <td style="padding:7px 12px;white-space:nowrap;">
    {delta_badge(delta)}{inline_bar(delta, max_abs)}
  </td>
</tr>"""

    table_html = (
        f'<div style="overflow-x:auto;"><table style="border-collapse:collapse;width:100%;'
        f'font-size:13px;color:{C["text"]};">{thead}<tbody>{tbody}</tbody></table></div>'
    )

    # Append under-development banner for S2C: availability correlation is next
    if step == "S2C":
        table_html += render_under_development_banner(
            "Availability Correlation",
            "We're building a sub-analysis that correlates S2C drops with inventory "
            "slot availability in Hub for the same period — identifying whether users "
            "are bouncing from the date picker because no slots are visible."
        )

    return table_html, []


def render_price_cards(summary: dict) -> tuple[str, list]:
    """
    Pre vs Post traffic-weighted average price for LP2S analysis.
    A price increase (red) alongside an LP2S drop is the price-anchoring signal.
    A price decrease (green) rules out pricing as a cause.
    """
    pa = summary.get("price_analysis") or {}
    if not pa.get("available"):
        return (f'<p style="color:{C["subtext"]};font-style:italic;">'
                f'Price data not available for this CE.</p>'), []

    pre_p  = pa.get("pre_avg_price_usd")
    post_p = pa.get("post_avg_price_usd")
    dp     = pa.get("delta_pct")

    # For price cards: red = price went UP (bad for LP2S), green = price went down
    badge_colour = C["red"] if (dp or 0) > 0 else C["green"]
    sign         = "+" if (dp or 0) >= 0 else ""
    delta_str    = f"{sign}{(dp or 0) * 100:.1f}%" if dp is not None else "—"

    def fmt_price(v):
        return f"${v:.2f}" if v is not None else "—"

    cards = f"""
<div style="display:flex;flex-wrap:wrap;gap:12px;">
  <div style="background:{C['white']};border:1px solid {C['border']};border-radius:10px;
              padding:18px 22px;flex:1;min-width:150px;">
    <div style="font-size:11px;color:{C['subtext']};text-transform:uppercase;
                letter-spacing:.06em;margin-bottom:8px;">Pre-Period Avg Price</div>
    <div style="font-size:28px;font-weight:800;color:{C['text']};line-height:1;">
      {fmt_price(pre_p)}
    </div>
    <div style="font-size:12px;color:{C['subtext']};margin-top:6px;">
      Traffic-weighted across experiences
    </div>
  </div>
  <div style="background:{C['white']};border:1px solid {C['border']};border-radius:10px;
              padding:18px 22px;flex:1;min-width:150px;">
    <div style="font-size:11px;color:{C['subtext']};text-transform:uppercase;
                letter-spacing:.06em;margin-bottom:8px;">Post-Period Avg Price</div>
    <div style="font-size:28px;font-weight:800;color:{C['text']};line-height:1;">
      {fmt_price(post_p)}
    </div>
    <div style="font-size:12px;color:{C['subtext']};margin-top:6px;
                display:flex;align-items:center;gap:6px;">
      <span>vs Pre</span>
      <span style="background:{badge_colour};color:#fff;padding:2px 7px;
                   border-radius:10px;font-size:11px;font-weight:600;">
        {delta_str}
      </span>
    </div>
  </div>
</div>"""

    # Experience-level price table (top 8 by |delta_pct|)
    exp_rows = pa.get("experiences") or []
    if exp_rows:
        th = lambda t: (f'<th style="padding:7px 12px;text-align:left;font-size:11px;'
                        f'color:{C["subtext"]};font-weight:600;border-bottom:2px solid {C["border"]};'
                        f'white-space:nowrap;">{t}</th>')
        thead = ("<thead><tr>"
                 + th("Experience") + th("Pre Price") + th("Post Price")
                 + th("Δ Price") + th("LP Traffic (pre)")
                 + "</tr></thead>")

        max_abs = max((abs(ep.get("delta_pct") or 0) for ep in exp_rows), default=1) or 1
        tbody   = ""
        for i, ep in enumerate(exp_rows):
            bg    = C["light"] if i % 2 else C["white"]
            dp_v  = ep.get("delta_pct")
            sign  = "+" if (dp_v or 0) >= 0 else ""
            dp_str = f"{sign}{(dp_v or 0) * 100:.1f}%" if dp_v is not None else "—"
            colour = C["red"] if (dp_v or 0) > 0.01 else (C["green"] if (dp_v or 0) < -0.01 else C["grey"])
            tbody += f"""
<tr style="background:{bg};">
  <td style="padding:7px 12px;font-weight:600;max-width:280px;
             overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
      title="{ep.get('experience_name','')}">
    {ep.get('experience_name','')}
  </td>
  <td style="padding:7px 12px;">{fmt_price(ep.get('pre_final_price_usd'))}</td>
  <td style="padding:7px 12px;font-weight:700;">{fmt_price(ep.get('post_final_price_usd'))}</td>
  <td style="padding:7px 12px;">
    <span style="color:{colour};font-weight:600;">{dp_str}</span>
    {inline_bar(dp_v, max_abs)}
  </td>
  <td style="padding:7px 12px;color:{C['subtext']}">{compact_num(ep.get('select_users'))}</td>
</tr>"""

        cards += (
            f'<div style="font-size:12px;font-weight:700;color:{C["subtext"]};'
            f'text-transform:uppercase;letter-spacing:.06em;margin:18px 0 6px;">By Experience</div>'
            f'<div style="overflow-x:auto;"><table style="border-collapse:collapse;width:100%;'
            f'font-size:13px;color:{C["text"]};">{thead}<tbody>{tbody}</tbody></table></div>'
        )

    return cards, []


def render_price_trend_chart(summary: dict) -> tuple[str, list]:
    """
    Daily traffic-weighted average final_price_usd — pre (grey dashed) vs post (purple).
    Reveals whether a price change was a gradual drift or a sudden step on a specific date.
    """
    pa = summary.get("price_analysis") or {}
    if not pa.get("available"):
        return "", []

    trend = pa.get("daily_trend") or []
    pre_x  = [d["date"]                  for d in trend if d.get("period") == "pre"  and d.get("avg_final_price_usd") is not None]
    pre_y  = [d["avg_final_price_usd"]   for d in trend if d.get("period") == "pre"  and d.get("avg_final_price_usd") is not None]
    post_x = [d["date"]                  for d in trend if d.get("period") == "post" and d.get("avg_final_price_usd") is not None]
    post_y = [d["avg_final_price_usd"]   for d in trend if d.get("period") == "post" and d.get("avg_final_price_usd") is not None]

    chart_id = "price-trend"
    fig = {
        "data": [
            {
                "type": "scatter", "mode": "lines+markers",
                "name": "Pre period",
                "x": pre_x, "y": pre_y,
                "line":   {"color": C["grey"], "dash": "dash", "width": 2},
                "marker": {"size": 5, "color": C["grey"]},
            },
            {
                "type": "scatter", "mode": "lines+markers",
                "name": "Post period",
                "x": post_x, "y": post_y,
                "line":   {"color": "#6800f4", "width": 2},
                "marker": {"size": 5, "color": "#6800f4"},
            },
        ],
        "layout": {
            "title": {"text": "Avg Listed Price (traffic-weighted) — Pre (dashed) vs Post", "font": {"size": 13}},
            "yaxis": {"title": "Avg Final Price (USD)", "tickprefix": "$"},
            "xaxis": {"title": "Date"},
            "plot_bgcolor":  C["white"],
            "paper_bgcolor": C["white"],
            "font": {"color": C["text"], "family": "Inter, system-ui, sans-serif"},
            "height": 240,
            "margin": {"l": 70, "r": 20, "t": 45, "b": 50},
            "legend": {"orientation": "h", "y": -0.3},
        }
    }
    html = f'<div id="{chart_id}" style="height:240px;"></div>'
    return html, [(chart_id, fig)]


def render_url_table(summary: dict) -> tuple[str, list]:
    """
    URL-level funnel breakdown — top 20 page URLs by pre-period LP traffic.

    Each row shows a URL's LP2S, S2C, and C2O rates for pre vs post, plus the
    delta. Cells with anomalously low rates (flagged by aggregate.py) are
    highlighted in red so the analyst's eye goes there immediately.

    The URL is truncated to ~50 chars and links to the actual page. If the CE
    has a top_page_url from Q0, that's already surfaced in the header; this
    table gives the full per-URL breakdown.
    """
    ub = summary.get("url_breakdown") or {}
    if not ub.get("available"):
        return (
            f'<p style="color:{C["subtext"]};font-style:italic;">'
            f'URL-level breakdown not available for this CE '
            f'(requires PRIMARY_MBHO to be MB or HO, not ALL).</p>'
        ), []

    urls = ub.get("urls") or []
    if not urls:
        return f'<p style="color:{C["subtext"]};font-style:italic;">No URL data.</p>', []

    def rate_cell(step_data: dict, step_key: str, anomalies: list) -> str:
        """Render a compact pre→post rate cell, red-tinted if anomalous."""
        pre   = step_data.get("pre_rate")
        post  = step_data.get("post_rate")
        delta = step_data.get("delta_abs")

        pre_str  = pct(pre)  if pre  is not None else "—"
        post_str = pct(post) if post is not None else "—"

        if delta is not None:
            colour = C["red"] if delta < -0.005 else (C["green"] if delta > 0.005 else C["grey"])
            sign   = "+" if delta >= 0 else ""
            delta_str = f'{sign}{delta * 100:.1f}pp'
        else:
            colour    = C["grey"]
            delta_str = "—"

        is_anomaly = step_key in anomalies
        bg = "rgba(229,57,53,0.06)" if is_anomaly else "transparent"
        warn = ' <span title="Anomalously low vs pre" style="color:#E53935;">⚠</span>' if is_anomaly else ""

        return (
            f'<td style="padding:6px 10px;background:{bg};white-space:nowrap;">'
            f'<span style="font-size:12px;color:{C["subtext"]}">{pre_str}</span>'
            f' → <span style="font-weight:700;">{post_str}</span>'
            f'<br><span style="font-size:11px;color:{colour};font-weight:600;">'
            f'{delta_str}</span>{warn}'
            f'</td>'
        )

    th = lambda t, tip="": (
        f'<th style="padding:7px 10px;text-align:left;font-size:11px;'
        f'color:{C["subtext"]};font-weight:600;border-bottom:2px solid {C["border"]};'
        f'white-space:nowrap;" title="{tip}">{t}</th>'
    )
    thead = (
        "<thead><tr>"
        + th("Page URL")
        + th("Type")
        + th("Pre LP", "Pre-period LP users on this URL")
        + th("Post LP", "Post-period LP users on this URL")
        + th("LP2S (pre→post, Δ)", "Landing Page → Select rate")
        + th("S2C (pre→post, Δ)",  "Select → Checkout rate")
        + th("C2O (pre→post, Δ)",  "Checkout → Order rate")
        + "</tr></thead>"
    )

    tbody = ""
    for i, row in enumerate(urls):
        bg    = C["light"] if i % 2 else C["white"]
        url   = row.get("page_url") or ""
        ptype = row.get("page_type") or ""
        psub  = row.get("page_sub_type") or ""
        ptype_label = f"{ptype}" + (f" / {psub}" if psub else "")

        # Truncate URL display at 55 chars, show full in title attr for hover
        url_display = url[:55] + "…" if len(url) > 55 else url
        url_link = (f'<a href="{url}" target="_blank" rel="noopener" '
                    f'style="color:{C["blue"]};text-decoration:none;font-size:12px;" '
                    f'title="{url}">{url_display}</a>')

        anomalies   = row.get("anomalies") or []
        steps_data  = row.get("steps") or {}
        pre_users   = row.get("pre_users_lp")
        post_users  = row.get("post_users_lp")

        # Row-level warning dot if any anomalies
        row_warn = (
            f'<span style="color:#E53935;font-size:10px;margin-right:4px;"'
            f' title="Anomalous drop in: {", ".join(anomalies)}">●</span>'
            if anomalies else ""
        )

        tbody += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:6px 10px;max-width:260px;">'
            f'{row_warn}{url_link}</td>'
            f'<td style="padding:6px 10px;font-size:12px;color:{C["subtext"]};'
            f'white-space:nowrap;">{ptype_label}</td>'
            f'<td style="padding:6px 10px;font-size:12px;color:{C["subtext"]}">'
            f'{compact_num(pre_users)}</td>'
            f'<td style="padding:6px 10px;font-size:12px;color:{C["subtext"]}">'
            f'{compact_num(post_users)}</td>'
            + rate_cell(steps_data.get("LP2S", {}), "LP2S", anomalies)
            + rate_cell(steps_data.get("S2C",  {}), "S2C",  anomalies)
            + rate_cell(steps_data.get("C2O",  {}), "C2O",  anomalies)
            + '</tr>'
        )

    html = (
        f'<p style="font-size:12px;color:{C["subtext"]};margin-bottom:10px;">'
        f'Top {len(urls)} URLs by pre-period LP traffic within the primary segment '
        f'(filtered to URLs with ≥ 50 users). '
        f'<span style="color:#E53935;">⚠</span> = ≥15% relative + ≥3pp absolute '
        f'drop vs pre in a significant step.</p>'
        f'<div style="overflow-x:auto;">'
        f'<table style="border-collapse:collapse;width:100%;font-size:13px;'
        f'color:{C["text"]};">{thead}<tbody>{tbody}</tbody></table></div>'
    )
    return html, []


def render_callout(variant: str, text: str, heading: str = "", label: str = "") -> tuple[str, list]:
    style = CALLOUT_STYLES.get(variant, CALLOUT_STYLES["insight"])

    header_html = ""
    if heading:
        label_html = ""
        if label:
            label_html = (
                f'<div style="font-size:10px;font-weight:700;color:{style["border"]};'
                f'text-transform:uppercase;letter-spacing:.1em;margin-bottom:5px;">{label}</div>'
            )
        header_html = (
            label_html
            + f'<div style="font-size:15px;font-weight:800;color:{C["text"]};'
            f'line-height:1.35;margin-bottom:8px;">{heading}</div>'
        )

    html = (
        f'<div style="border-left:4px solid {style["border"]};background:{style["bg"]};'
        f'padding:14px 18px;border-radius:0 8px 8px 0;margin:12px 0;">'
        f'{header_html}'
        f'<span style="font-size:14px;margin-right:6px;">{style["icon"]}</span>'
        f'<span style="font-size:14px;color:{C["text"]};line-height:1.6;">{text}</span>'
        f'</div>'
    )
    return html, []


def render_verdict_banner(item: dict, summary: dict) -> tuple[str, list]:
    """
    Action-first hero banner — the very first thing leadership sees.
    Renders: CVR change | root cause | action + DRI | recovery ceiling.
    All text fields are Claude-authored in the spec; numbers come from summary.
    """
    headline = summary.get("headline", {})
    delta    = headline.get("delta", {})
    pre_cvr  = (headline.get("pre") or {}).get("cvr")
    post_cvr = (headline.get("post") or {}).get("cvr")
    d_cvr    = delta.get("cvr")

    # Format CVR change line
    if d_cvr is not None:
        d_pp  = f"{d_cvr * 100:+.2f}pp"
        d_pct = f"({post_cvr / pre_cvr - 1:+.0%})" if pre_cvr else ""
        cvr_colour = C["red"] if d_cvr < 0 else C["green"]
        cvr_line = f'<span style="color:{cvr_colour};">{d_pp} {d_pct}</span>'
    else:
        cvr_line = "—"

    root_cause  = item.get("root_cause", "")
    action_text = item.get("action", "")
    dri         = item.get("dri", "")
    recovery_pp_val = item.get("recovery_pp")

    recovery_html = ""
    if recovery_pp_val is not None:
        sign = "+" if recovery_pp_val >= 0 else ""
        recovery_html = (
            f'<div style="margin-top:16px;font-size:12px;color:#94A3B8;">'
            f'⚡ If the primary driver step recovers to pre-period levels, '
            f'CVR recovers ~<b style="color:#E2E8F0;">{sign}{recovery_pp_val * 100:.2f}pp</b> '
            f'(Shapley ceiling — full recovery scenario)'
            f'</div>'
        )

    html = (
        f'<div style="background:#1A1A2E;color:#fff;border-radius:12px;padding:28px 32px;margin-bottom:20px;">'

        # CVR change row
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;flex-wrap:wrap;gap:8px;">'
        f'<div>'
        f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:#94A3B8;margin-bottom:4px;">CVR CHANGE · POST VS PRE</div>'
        f'<div style="font-size:36px;font-weight:900;line-height:1;">{cvr_line}</div>'
        f'</div>'
        f'</div>'

        # Root cause block
        f'<div style="background:rgba(255,255,255,0.07);border-radius:8px;padding:16px 20px;margin-bottom:12px;">'
        f'<div style="font-size:10px;font-weight:700;color:#60A5FA;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px;">ROOT CAUSE</div>'
        f'<div style="font-size:15px;font-weight:600;color:#fff;line-height:1.5;">{root_cause}</div>'
        f'</div>'

        # Action block
        f'<div style="background:rgba(67,160,71,0.18);border:1px solid rgba(67,160,71,0.35);border-radius:8px;padding:16px 20px;">'
        f'<div style="font-size:10px;font-weight:700;color:#81C784;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px;">'
        f'ACTION{f" · DRI: {dri.upper()}" if dri else ""}'
        f'</div>'
        f'<div style="font-size:15px;font-weight:600;color:#fff;line-height:1.5;">{action_text}</div>'
        f'</div>'

        + recovery_html
        + f'</div>'
    )
    return html, []


def render_brief_bullets(bullets: list) -> tuple[str, list]:
    """
    3 confidence bullets (what/where/when) shown immediately after the verdict.
    Each bullet has a label and a text sentence. Claude authors both.
    """
    if not bullets:
        return "", []

    cards = ""
    for b in bullets[:3]:
        label = b.get("label", "")
        text  = b.get("text", "")
        cards += (
            f'<div style="flex:1;min-width:200px;background:{C["white"]};'
            f'border:1px solid {C["border"]};border-radius:10px;padding:14px 18px;">'
            f'<div style="font-size:10px;font-weight:700;color:{C["blue"]};'
            f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">{label}</div>'
            f'<div style="font-size:13px;color:{C["text"]};line-height:1.55;">{text}</div>'
            f'</div>'
        )

    html = f'<div style="display:flex;gap:12px;flex-wrap:wrap;">{cards}</div>'
    return html, []


def render_evidence_divider() -> tuple[str, list]:
    """Visual break between the verdict section and the supporting evidence."""
    html = (
        f'<div style="display:flex;align-items:center;gap:14px;margin:36px 0 24px;">'
        f'<div style="flex:1;height:1px;background:{C["border"]};"></div>'
        f'<div style="font-size:11px;font-weight:700;color:{C["subtext"]};'
        f'text-transform:uppercase;letter-spacing:.1em;white-space:nowrap;">Supporting Analysis</div>'
        f'<div style="flex:1;height:1px;background:{C["border"]};"></div>'
        f'</div>'
    )
    return html, []


def render_dimension_table_pair(summary: dict, step: str, dims: list) -> tuple[str, list]:
    """Render two dimension tables side by side in a 50/50 flex row."""
    tables = []
    all_charts: list[tuple[str, dict]] = []
    for dim in dims[:2]:
        html, charts = render_dimension_table(summary, step, dim)
        label = dim.replace("_", " ").title()
        table_with_label = (
            f'<div style="font-size:12px;font-weight:700;color:{C["subtext"]};'
            f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">By {label}</div>'
            + html
        )
        tables.append(table_with_label)
        all_charts.extend(charts)

    if len(tables) == 2:
        out = (
            f'<div style="display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap;">'
            f'<div style="flex:1;min-width:280px;">{tables[0]}</div>'
            f'<div style="flex:1;min-width:280px;">{tables[1]}</div>'
            f'</div>'
        )
    elif tables:
        out = tables[0]
    else:
        out = ""
    return out, all_charts


def render_action_cards(actions: list[dict]) -> tuple[str, list]:
    if not actions:
        return "", []

    priority_classes = ["p1", "p2", "p3"]
    priority_labels  = ["P1", "P2", "P3"]
    priority_borders = ["#e53935", "#f57c00", "#43a047"]

    cards = ""
    for i, action in enumerate(actions):
        pc     = priority_classes[min(i, 2)]
        pl     = priority_labels[min(i, 2)]
        border = priority_borders[min(i, 2)]
        cards += f"""
<div style="background:#fff;border:1px solid #e8ebf4;border-radius:10px;
            padding:20px 24px;margin-bottom:14px;
            border-left:4px solid {border};">
  <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;">
    <span class="priority-badge {pc}">{pl}</span>
    <span style="font-size:14px;font-weight:700;color:#1a1a2e;line-height:1.4;">
      {action.get('finding','')}
    </span>
  </div>
  <div style="font-size:13px;color:#5c6a7a;margin-bottom:8px;">
    <b>Cause:</b> {action.get('cause','')}
  </div>
  <div style="font-size:13px;color:#1a1a2e;margin-bottom:10px;">
    <b>Action:</b> {action.get('action','')}
  </div>
  <div style="font-size:12px;color:#8892a4;border-top:1px solid #e8ebf4;padding-top:8px;">
    <b>DRI:</b> {action.get('dri','')}
  </div>
</div>"""

    return cards, []


def render_session_recordings_table(item: dict) -> tuple[str, list]:
    """
    Renders session recordings as structured per-recording tables.

    Spec fields:
      locus   — one-sentence description of the user segment and page filtered on
      replays — list of {label, steps: [str, ...], inference}

    Each recording renders as a table:
      Step | What the user did
      ...
      [Inference row spanning full width]
    """
    locus   = item.get("locus", "")
    replays = item.get("replays", [])
    if not replays:
        return "", []

    locus_html = ""
    if locus:
        locus_html = (
            f'<div style="font-size:12px;color:#5c6a7a;margin-bottom:18px;">'
            f'<b style="color:#1a1a2e;">Locus:</b> {locus}</div>'
        )

    blocks = ""
    for replay in replays:
        label     = replay.get("label", "")
        steps     = replay.get("steps", [])
        inference = replay.get("inference", "")

        rows = ""
        for i, step in enumerate(steps):
            rows += (
                f'<tr>'
                f'<td style="padding:8px 10px;text-align:center;color:#8892a4;font-size:12px;'
                f'font-weight:700;border-bottom:1px solid #f0f1f5;white-space:nowrap;width:44px;">'
                f'{i + 1}</td>'
                f'<td style="padding:8px 14px;font-size:13px;color:#1a1a2e;line-height:1.5;'
                f'border-bottom:1px solid #f0f1f5;">{step}</td>'
                f'</tr>'
            )

        inference_row = ""
        if inference:
            inference_row = (
                f'<tr>'
                f'<td colspan="2" style="padding:10px 14px;font-size:13px;font-weight:600;'
                f'color:#c62828;background:#fdecea;border-top:2px solid #e53935;'
                f'border-radius:0 0 7px 7px;">'
                f'→ {inference}</td>'
                f'</tr>'
            )

        label_html = ""
        if label:
            label_html = (
                f'<div style="font-size:11px;font-weight:700;color:#3a4a8a;'
                f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">{label}</div>'
            )

        blocks += (
            f'<div style="margin-bottom:20px;">'
            f'{label_html}'
            f'<div style="border:1px solid #e8ebf4;border-radius:8px;overflow:hidden;">'
            f'<table style="border-collapse:collapse;width:100%;">'
            f'<thead><tr style="background:#f5f6fa;">'
            f'<th style="padding:8px 10px;font-size:10px;font-weight:700;color:#8892a4;'
            f'text-transform:uppercase;letter-spacing:.06em;text-align:center;'
            f'border-bottom:2px solid #e0e4ef;width:44px;">Step</th>'
            f'<th style="padding:8px 14px;font-size:10px;font-weight:700;color:#8892a4;'
            f'text-transform:uppercase;letter-spacing:.06em;text-align:left;'
            f'border-bottom:2px solid #e0e4ef;">What the user did</th>'
            f'</tr></thead>'
            f'<tbody>{rows}{inference_row}</tbody>'
            f'</table></div></div>'
        )

    return locus_html + blocks, []


# ─────────────────────────────────────────────────────────────────────────────
# Section wrapper
# ─────────────────────────────────────────────────────────────────────────────

def section(title: str, content: str, subtitle: str = "") -> str:
    sub = (f'<div class="section-subtitle">{subtitle}</div>'
           if subtitle else "")
    return f"""
<div class="analysis-block">
  <div class="section-label">{title}</div>
  {sub}
  <div style="margin-top:2px;">{content}</div>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Escape-hatch components (v1.15)
# ─────────────────────────────────────────────────────────────────────────────
#
# The 19 built-in component renderers above cover the common RCA shapes. When
# an investigation surfaces a finding the built-ins can't express — a custom
# cross-cut Claude designed mid-investigation, a novel chart for a metric not
# in summary.json, a structured table for an experience pivot that doesn't
# match `experience_table`'s shape — the spec-JSON path needs an escape hatch
# so the rendering layer never silences a real finding.
#
# Two components serve this need:
#   • analysis_block — wraps arbitrary HTML in the standard Section-3 chrome
#     (rounded card, border, title styling, verdict-line styling). Preferred
#     for novel findings that should look visually consistent with the rest
#     of Section 3.
#   • raw_html — pure passthrough, no wrapper. Use only when the standard
#     chrome is wrong for the finding (full-bleed callout, custom Plotly
#     container, section divider). Rare.
#
# Principle (also documented in SKILL.md Step 3): investigation drives the
# report, not the inverse. The escape hatches are for *novel evidence*, not
# for cosmetic deviation from existing components.

def render_analysis_block(item: dict) -> tuple[str, list]:
    """Wrap arbitrary HTML in the standard Section-3 .analysis-block chrome.

    Schema:
      title:          required — section heading shown at the top of the block
      verdict:        optional — colored inline finding line above body
      verdict_class:  optional — "" (red, default) | "neutral" (blue-grey)
      body_html:      required — arbitrary HTML; rendered verbatim inside the block
      anchor_id:      optional — DOM id for ↗ link-to-table anchors (e.g. "block-custom-X")
    """
    title       = item.get("title", "")
    verdict     = item.get("verdict", "")
    vclass      = item.get("verdict_class", "")
    body_html   = item.get("body_html", "")
    anchor_id   = item.get("anchor_id", "")

    anchor_attr = f' id="{anchor_id}"' if anchor_id else ""
    vclass_suffix = f" {vclass}" if vclass else ""
    verdict_html = (
        f'<div class="verdict-line{vclass_suffix}">{verdict}</div>' if verdict else ""
    )
    title_html = (
        f'<div class="block-title">{title}</div>' if title else ""
    )
    html = (
        f'<div class="analysis-block"{anchor_attr}>'
        f'{title_html}'
        f'{verdict_html}'
        f'{body_html}'
        f'</div>'
    )
    return html, []


def render_raw_html(item: dict) -> tuple[str, list]:
    """Pass HTML through verbatim. No wrapper, no chrome.

    Schema:
      html:      required — arbitrary HTML rendered verbatim
      chart_id:  optional — Plotly chart container id (if the HTML contains one)
      fig_json:  optional — JSON-serialised Plotly figure spec for the chart

    When both chart_id and fig_json are supplied, the figure is registered with
    the page-level Plotly init script (same path as built-in chart components).
    """
    html = item.get("html", "")
    charts = []
    chart_id = item.get("chart_id")
    fig_json = item.get("fig_json")
    if chart_id and fig_json:
        try:
            fig = json.loads(fig_json) if isinstance(fig_json, str) else fig_json
            charts.append((chart_id, fig))
        except (json.JSONDecodeError, TypeError):
            # Fail soft — render the HTML anyway, just skip the figure registration
            pass
    return html, charts


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch table
# ─────────────────────────────────────────────────────────────────────────────

def dispatch(spec_item: dict, summary: dict) -> tuple[str, list]:
    """Route a spec item to its renderer. Returns (html, [(chart_id, fig), ...])."""
    item = normalize_spec_item(spec_item)
    t    = item.get("component", "")

    if t == "hero_verdict":
        return render_verdict_banner(item, summary)
    elif t == "brief_bullets":
        return render_brief_bullets(item.get("bullets", []))
    elif t == "evidence_divider":
        return render_evidence_divider()
    elif t == "executive_summary":
        return render_executive_summary(item.get("findings", []))
    elif t == "metric_cards":
        return render_metric_cards(summary)
    elif t == "shapley_waterfall":
        return render_shapley_waterfall(summary)
    elif t == "mbho_channel_table":
        return render_mbho_channel_table(summary)
    elif t == "dimension_table":
        return render_dimension_table(
            summary,
            step=item.get("step", ""),
            dim=item.get("dim", ""),
            title=item.get("title", ""),
        )
    elif t == "experience_table":
        return render_experience_table(summary, step=item.get("step", ""))
    elif t == "trend_chart":
        return render_trend_chart(summary, step=item.get("step", ""))
    elif t == "c2o_sub_cards":
        return render_c2o_sub_cards(summary)
    elif t == "section_header":
        return render_section_header(
            title=item.get("title", ""),
            subtitle=item.get("subtitle", ""),
        )
    elif t == "callout":
        return render_callout(
            variant=item.get("variant", "insight"),
            text=item.get("text", ""),
            heading=item.get("heading", ""),
            label=item.get("label", ""),
        )
    elif t == "dimension_table_pair":
        return render_dimension_table_pair(
            summary,
            step=item.get("step", ""),
            dims=item.get("dims", []),
        )
    elif t == "action_cards":
        return render_action_cards(item.get("actions", []))
    elif t == "session_recordings_table":
        return render_session_recordings_table(item)
    elif t == "price_cards":
        return render_price_cards(summary)
    elif t == "price_trend_chart":
        return render_price_trend_chart(summary)
    elif t == "url_table":
        return render_url_table(summary)
    elif t == "analysis_block":
        # v1.15 escape hatch — see "Escape-hatch components" section above
        return render_analysis_block(item)
    elif t == "raw_html":
        # v1.15 escape hatch — true passthrough, no wrapper
        return render_raw_html(item)
    else:
        return f'<p style="color:red;">Unknown component: {t}</p>', []


# ─────────────────────────────────────────────────────────────────────────────
# Page assembly
# ─────────────────────────────────────────────────────────────────────────────

SECTION_TITLES = {
    "hero_verdict":         (None, ""),    # rendered directly — no extra wrapper
    "brief_bullets":        (None, ""),    # rendered directly — no extra wrapper
    "evidence_divider":     (None, ""),    # rendered directly — no extra wrapper
    "executive_summary":    (None, ""),    # rendered directly — no extra wrapper
    "metric_cards":         ("Overview", ""),
    "shapley_waterfall":    ("Funnel Attribution (Shapley)", "Contributions sum exactly to total ΔCVR"),
    "mbho_channel_table":   ("Traffic Mix Analysis", ""),
    "dimension_table":      ("{step} by {dim_label}", ""),
    "dimension_table_pair": ("{step} — {dims_label}", ""),
    "experience_table":     ("{step} — Experience Breakdown", "Top experiences by rate change · sorted by traffic volume"),
    "trend_chart":          ("Daily Trend — {step}", "Pre (grey dashed) vs Post (blue solid)"),
    "c2o_sub_cards":        ("Checkout → Order: C2A vs A2O", "Did users abandon before payment, or did payment fail?"),
    "price_cards":          ("LP2S — Price Analysis", "Traffic-weighted average listed price · pre vs post"),
    "price_trend_chart":    ("Price Trend — Daily", "Pre (grey dashed) vs Post (purple solid)"),
    "url_table":            ("Page URL Breakdown", "LP2S · S2C · C2O by URL — pre vs post · ⚠ = anomalous drop"),
    "section_header":              (None, ""),    # renders its own heading, no wrapper
    "callout":                     (None, ""),    # no section wrapper
    "action_cards":                ("Findings & Actions", ""),
    "session_recordings_table":    ("Session Recordings", "Directly observed user behaviour · post period"),
    # v1.15 escape hatches — these render their own chrome (analysis_block) or
    # no chrome (raw_html), so the outer _render_sections wrapper must NOT add
    # a section heading. None signals "renders directly, no wrapper."
    "analysis_block":              (None, ""),
    "raw_html":                    (None, ""),
}

# ─────────────────────────────────────────────────────────────────────────────
# Markdown → HTML (perf-audit tab, and any future markdown-sourced tab)
# ─────────────────────────────────────────────────────────────────────────────
#
# Perf-audit ships pure markdown (10 numbered sections, GFM-style tables, lists,
# bold/italic, links). We need to embed that markdown as a tab pane inside the
# CVR-RCA HTML without taking a hard dependency on the `markdown` PyPI package
# (the skill ships as files, not a Python project with a pinned requirements).
# This renderer handles exactly what perf-audit emits — not a general markdown
# implementation. Heading IDs are injected at render time with a configurable
# prefix so cross-tab anchors stay namespaced and stable.

def _slugify(text: str) -> str:
    """Turn a heading like '5. Coverage + Matchmaking' into 'coverage-matchmaking'."""
    text = re.sub(r"^\s*\d+\.\s*", "", text)            # drop leading "5. "
    text = re.sub(r"[`*_]", "", text)                    # strip md emphasis
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text or "section"

def _md_inline(text: str) -> str:
    """Inline conversions: links, code, bold, italic. Order matters."""
    # links: [label](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    # inline code: `code`
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # bold: **text**
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # italic: *text* (not part of bold)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    return text

def _md_parse_table(lines: list[str], start: int) -> tuple[str, int]:
    """Parse a GFM pipe table starting at `lines[start]`. Returns (html, consumed)."""
    def cells(row: str) -> list[str]:
        row = row.strip().strip("|")
        return [c.strip() for c in row.split("|")]

    header_cells = cells(lines[start])
    # alignment row is lines[start+1] — we don't honour alignment, just consume it
    i = start + 2
    rows: list[list[str]] = []
    while i < len(lines) and "|" in lines[i] and lines[i].strip():
        rows.append(cells(lines[i]))
        i += 1
    out = ['<table class="md-table"><thead><tr>']
    for cell in header_cells:
        out.append(f"<th>{_md_inline(cell)}</th>")
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{_md_inline(cell)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out), i - start

def _md_parse_list(lines: list[str], start: int, ordered: bool) -> tuple[str, int]:
    """Parse a contiguous list block. Returns (html, consumed)."""
    pat = re.compile(r"^\s*\d+\.\s+(.*)$" if ordered else r"^\s*[-*]\s+(.*)$")
    items: list[str] = []
    i = start
    while i < len(lines):
        m = pat.match(lines[i])
        if not m:
            break
        items.append(_md_inline(m.group(1)))
        i += 1
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{it}</li>" for it in items) + f"</{tag}>", i - start

def render_markdown_to_html(md: str, anchor_prefix: str = "") -> str:
    """Render perf-audit-style markdown to HTML.

    Supported:
      - ATX headings (#..######) with auto-injected `id="<anchor_prefix><slug>"`
      - GFM pipe tables → `<table class="md-table">`
      - Unordered (- *) and ordered (1.) lists
      - Bold (**), italic (*), inline code (`), links ([t](u))
      - Horizontal rules (---)
      - Paragraphs (blank-line separated)
      - HTML comments are passed through unchanged (perf-audit uses <!-- markers -->)

    Anything outside this surface is rendered as plain paragraph text.
    """
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # HTML comment passthrough — perf-audit uses these as section markers
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            out.append(stripped)
            i += 1
            continue

        # ATX heading
        m = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            slug = _slugify(text)
            anchor = f' id="{anchor_prefix}{slug}"' if anchor_prefix else f' id="{slug}"'
            out.append(f"<h{level}{anchor}>{_md_inline(text)}</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}\s*$", line) or re.match(r"^_{3,}\s*$", line):
            out.append("<hr>")
            i += 1
            continue

        # GFM pipe table — header row + separator row
        if (
            "|" in line
            and i + 1 < len(lines)
            and re.match(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", lines[i + 1])
        ):
            tbl, consumed = _md_parse_table(lines, i)
            out.append(tbl)
            i += consumed
            continue

        # Unordered list
        if re.match(r"^\s*[-*]\s+", line):
            lst, consumed = _md_parse_list(lines, i, ordered=False)
            out.append(lst)
            i += consumed
            continue

        # Ordered list
        if re.match(r"^\s*\d+\.\s+", line):
            lst, consumed = _md_parse_list(lines, i, ordered=True)
            out.append(lst)
            i += consumed
            continue

        # Blank line
        if not stripped:
            i += 1
            continue

        # Paragraph — gather contiguous non-empty non-block lines
        para = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip():
                break
            if re.match(r"^(#{1,6}\s|[-*]\s|\d+\.\s|-{3,}\s*$|_{3,}\s*$)", nxt):
                break
            if "|" in nxt and i + 1 < len(lines) and re.match(
                r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", lines[i + 1] if i + 1 < len(lines) else ""
            ):
                break
            para.append(nxt)
            i += 1
        out.append(f"<p>{_md_inline(' '.join(s.strip() for s in para))}</p>")

    return "\n".join(out)


def render_markdown_tab(path: Path, anchor_prefix: str) -> str:
    """Read a markdown file and return HTML for its tab pane.

    If the file is missing or empty, return a small "not available" placeholder
    so the tab still renders rather than producing a broken pane. The caller
    decides whether to emit the tab at all — we don't crash here.
    """
    if not path.exists():
        return (
            '<div class="md-content"><p style="color:#8892a4;font-style:italic;">'
            f"Source file <code>{path.name}</code> not found in run directory."
            "</p></div>"
        )
    md_text = path.read_text(encoding="utf-8")
    if not md_text.strip():
        return (
            '<div class="md-content"><p style="color:#8892a4;font-style:italic;">'
            f"Source file <code>{path.name}</code> is empty."
            "</p></div>"
        )
    body = render_markdown_to_html(md_text, anchor_prefix=anchor_prefix)
    return f'<div class="md-content">{body}</div>'


def render_tab_bar(tabs: list[dict]) -> str:
    """Emit the sticky tab bar above the panes. Only called when tabs >= 2."""
    buttons = []
    for idx, tab in enumerate(tabs):
        tab_id = tab["id"]
        label = tab.get("label", tab_id)
        active = " active" if idx == 0 else ""
        buttons.append(
            f'<button class="tab-button{active}" data-tab="{tab_id}" '
            f'role="tab" aria-selected="{str(idx == 0).lower()}">{label}</button>'
        )
    return f'<div class="tab-bar" role="tablist">{"".join(buttons)}</div>'


# ─────────────────────────────────────────────────────────────────────────────
# Spec assembly
# ─────────────────────────────────────────────────────────────────────────────

def _render_sections(sections: list, summary: dict, all_charts: list) -> str:
    """Loop through a sections[] array and render each component.

    Extracted from the original inline loop in `assemble()` so the same logic
    can run per-tab. `all_charts` is mutated in place — Plotly init scripts are
    emitted once at the end, after all tabs are assembled.
    """
    html_acc = ""
    for item in sections:
        item = normalize_spec_item(item)
        t = item.get("component", "")
        html, charts = dispatch(item, summary)
        all_charts.extend(charts)

        title_tmpl, subtitle_tmpl = SECTION_TITLES.get(t, (t, ""))

        if title_tmpl is None:
            html_acc += html
        else:
            fmt_kwargs = dict(item)
            fmt_kwargs.setdefault("dim_label", item.get("dim", "").replace("_", " ").title())
            raw_dims = item.get("dims", [])
            fmt_kwargs.setdefault(
                "dims_label",
                " & ".join(d.replace("_", " ").title() for d in raw_dims) if raw_dims else ""
            )
            title    = title_tmpl.format(**fmt_kwargs)
            subtitle = subtitle_tmpl.format(**fmt_kwargs)
            html_acc += section(title, html, subtitle)
    return html_acc


def assemble(spec: dict, summary: dict, template: str, spec_dir: Path | None = None) -> str:
    meta    = summary.get("meta", {})
    sections_html = ""
    all_charts: list[tuple[str, dict]] = []

    primary_mbho = meta.get('primary_mbho', '')
    mbho_label   = "Microbrand (MB)" if primary_mbho == "MB" else ("Headout (HO)" if primary_mbho == "HO" else primary_mbho)

    # ── Report header ─────────────────────────────────────────────────────────
    # CE name is the primary identifier; CE ID is a secondary label.
    # If a top_page_url is available (from Q0), the CE name becomes a clickable
    # link so the analyst can jump directly from the report to the live page.
    ce_name   = meta.get("combined_entity_name") or f"CE {meta.get('ce_id','')}"
    ce_type   = meta.get("combined_entity_type") or ""
    ce_market = meta.get("market") or ""
    ce_country= meta.get("country") or ""
    top_url   = meta.get("top_page_url")

    # Build the CE name element — linked if we have a URL
    if top_url:
        ce_name_html = (
            f'<a href="{top_url}" target="_blank" rel="noopener" '
            f'style="color:#fff;text-decoration:none;border-bottom:2px solid rgba(255,255,255,.4);">'
            f'{ce_name}</a>'
        )
    else:
        ce_name_html = ce_name

    # Build sub-labels row: CE ID · type · market · country
    sub_parts = [f'CE {meta.get("ce_id", "")}']
    if ce_type:
        sub_parts.append(ce_type)
    if ce_country:
        sub_parts.append(ce_country)
    if ce_market:
        sub_parts.append(ce_market)
    ce_sub_label = " · ".join(sub_parts)

    sections_html += f"""
<div style="background:#1a1a2e;color:#fff;padding:28px 32px;margin-bottom:28px;">
  <div style="font-size:10px;text-transform:uppercase;letter-spacing:.15em;
              color:#8892a4;margin-bottom:8px;">CVR Root Cause Analysis</div>
  <div style="font-size:28px;font-weight:900;line-height:1.2;letter-spacing:-.01em;">{ce_name_html}</div>
  <div style="font-size:12px;color:#8892a4;margin-top:6px;">{ce_sub_label}</div>
  <div style="display:flex;flex-wrap:wrap;gap:20px;margin-top:14px;font-size:13px;color:#c8cfe0;">
    <span><span style="color:#8892a4;font-size:10px;text-transform:uppercase;letter-spacing:.08em;margin-right:5px;">Pre</span>{meta.get('pre_period','')}</span>
    <span style="color:#3a4a6a;">·</span>
    <span><span style="color:#8892a4;font-size:10px;text-transform:uppercase;letter-spacing:.08em;margin-right:5px;">Post</span>{meta.get('post_period','')}</span>
    <span style="color:#3a4a6a;">·</span>
    <span><span style="color:#8892a4;font-size:10px;text-transform:uppercase;letter-spacing:.08em;margin-right:5px;">Segment</span>{mbho_label}</span>
  </div>
</div>"""

    # ── Tabs vs flat sections ─────────────────────────────────────────────────
    # The spec may use one of two shapes:
    #   • Flat (legacy):  {"sections": [...]}
    #   • Tabbed:         {"tabs": [{"id": "...", "label": "...", "sections": [...]}
    #                              | {"id": "...", "label": "...",
    #                                 "source": {"type": "markdown", "path": "..."}}]}
    # When the tab list has 2+ entries we emit a tab bar above panes; with one
    # entry (or no tabs key) we emit content flat — zero regression for older
    # specs and for runs where the perf-audit didn't fire.
    # v1.15: tab bar is emitted into its own template slot ({{TAB_BAR}}) so it
    # sits outside .container — full-viewport-width sticky band, left-anchored
    # buttons. See report_structure.md → "Tabbed report structure → Visual
    # differences from CVR-RCA content" for the rationale.
    tab_bar_html = ""
    tabs = spec.get("tabs")
    if tabs and len(tabs) >= 2:
        tab_bar_html = render_tab_bar(tabs)
        for idx, tab in enumerate(tabs):
            active_cls = " active" if idx == 0 else ""
            tab_id = tab["id"]
            if "sections" in tab:
                pane_body = _render_sections(tab["sections"], summary, all_charts)
            elif "source" in tab and tab["source"].get("type") == "markdown":
                src_path = tab["source"]["path"]
                # Resolve path relative to the spec file's directory (the run_dir)
                full_path = (spec_dir / src_path) if spec_dir else Path(src_path)
                anchor_prefix = tab.get("anchor_prefix", f"{tab_id}-")
                pane_body = render_markdown_tab(full_path, anchor_prefix)
            else:
                pane_body = (
                    '<div style="color:#8892a4;font-style:italic;padding:20px;">'
                    f'Tab "{tab_id}" has no sections or source.</div>'
                )
            sections_html += (
                f'<div class="tab-pane{active_cls}" id="tab-{tab_id}" role="tabpanel">'
                f'{pane_body}</div>'
            )
    elif tabs and len(tabs) == 1:
        # Single tab: render flat (no tab bar). Source could still be markdown.
        only = tabs[0]
        if "sections" in only:
            sections_html += _render_sections(only["sections"], summary, all_charts)
        elif "source" in only and only["source"].get("type") == "markdown":
            full_path = (spec_dir / only["source"]["path"]) if spec_dir else Path(only["source"]["path"])
            sections_html += render_markdown_tab(full_path, only.get("anchor_prefix", ""))
    else:
        # Legacy flat spec — backward compatible
        sections_html += _render_sections(spec.get("sections", []), summary, all_charts)

    # Plotly init JS
    js_lines = []
    for chart_id, fig in all_charts:
        safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", chart_id)
        js_lines.append(
            f"var fig_{safe_id} = {json.dumps(fig)};\n"
            f"Plotly.newPlot('{chart_id}', fig_{safe_id}.data, fig_{safe_id}.layout, {{responsive:true}});"
        )
    chart_js = "\n".join(js_lines)

    title_str = f"CVR RCA — CE {meta.get('ce_id', '')}"

    # Inject Headout logo as self-contained base64 data URI
    logo_path = Path(__file__).parent.parent / "assets" / "headout-logo.svg"
    if logo_path.exists():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
        logo_src = f"data:image/svg+xml;base64,{logo_b64}"
    else:
        # Fallback: plain purple square (logo asset missing)
        logo_src = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

    html_out = (template
                .replace("{{TITLE}}", title_str)
                .replace("{{TAB_BAR}}", tab_bar_html)
                .replace("{{BODY}}", sections_html)
                .replace("{{CHART_SCRIPTS}}", chart_js)
                .replace("{{HEADOUT_LOGO_SRC}}", logo_src))
    return html_out


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--summary",  required=True)
    p.add_argument("--spec",     required=True)
    p.add_argument("--output",   required=True)
    p.add_argument("--template", default=None)
    args = p.parse_args()

    summary  = json.loads(Path(args.summary).read_text())
    spec_path = Path(args.spec)
    spec     = json.loads(spec_path.read_text())

    # Find template relative to this script if not specified
    template_path = (Path(args.template) if args.template
                     else Path(__file__).parent.parent / "templates" / "report.html")
    template = template_path.read_text()

    # spec_dir lets `tabs[].source.path` resolve relative to the run directory,
    # so the spec can reference `perf_audit_report.md` without absolute paths.
    html = assemble(spec, summary, template, spec_dir=spec_path.parent)
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"Report written → {args.output}")


if __name__ == "__main__":
    main()
