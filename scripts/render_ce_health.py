#!/usr/bin/env python3
"""
render_ce_health.py — beautify the CE Health tab for the CE-RCA composite.

CE Health ships deterministic structured data: a `ce_health_report.json` sidecar
(vitals / windows / metadata) plus `ce_health_report.md` (11 sections as GFM
tables). This renderer re-renders that data into visual_kit chrome — the same
"presentation re-render" CVR-RCA does on its own `summary.json` — and writes a
body fragment `<run_dir>/ce_health_tab.html` that `compose.py` embeds verbatim
as the CE Health tab (`html-fragment` type).

Fidelity contract (see references/composition_rules.md):
  • CE Health's sections 1→11, exact headings, exact order, ALL rows, exact data.
  • No summarization, no row-trimming, no reordering. Beautification only:
      §1 Metadata  → header pills (rendered by compose.build_header, NOT here)
      §2 Vitals    → 6 metric cards + the full 4-window table below
      §5 L12M      → 2 Plotly charts replacing the monthly tables (same data)
      §6 TGIDs     → styled table with first 2 columns frozen on scroll
      §7 Shapley   → the ONE agreed exception: a corrected canonical 5-factor
                     booking-revenue waterfall (CE Health's own Shapley is
                     mis-specified — 5 factors, double-counts CR×TR). Computed
                     from raw revenue-component rows pulled via Query 1 (bq CLI).
  • If Query 1 fails, the §7 waterfall is skipped and CE Health's §7 table is
    rendered verbatim instead — a failed query never breaks the tab.

The renderer writes only the body fragment. The metadata header pills and the
composite header come from compose.build_header (fed by meta.json). Cross-tab ↗
anchors use the registered `cehealth-<slug>` scheme.

Usage:
    python3 scripts/render_ce_health.py --run-dir <run_dir>
"""
from __future__ import annotations

import argparse
import html as _html
import json
import re
import subprocess
import sys
from itertools import permutations as _perms
from math import factorial as _fact
from pathlib import Path

# Reuse the vendored markdown renderer for the prose section (§8).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import render_markdown_to_html  # noqa: E402

PROJECT_ID = "headout-analytics"
DATASET = "analytics_reporting"
BQ_LOCATION = "EU"

# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def money(v):
    a = abs(v); s = "-" if v < 0 else ""
    if a >= 1e6: return f"{s}${a / 1e6:.1f}M"
    if a >= 1e3: return f"{s}${a / 1e3:.1f}K"
    return f"{s}${a:.0f}"


def pct_delta(cur, pri):
    if not pri: return ("flat", "delta-flat")
    dp = (cur - pri) / pri * 100
    cls = "delta-pos" if dp > 0.5 else ("delta-neg" if dp < -0.5 else "delta-flat")
    return (f"{'+' if dp >= 0 else ''}{dp:.0f}%", cls)


def pp_delta(cur, pri):
    dpp = cur - pri
    cls = "delta-pos" if dpp > 0.05 else ("delta-neg" if dpp < -0.05 else "delta-flat")
    return (f"{'+' if dpp >= 0 else ''}{dpp:.1f}pp", cls)


def _arrow(cls):
    # Direction arrow for the vitals pill, by delta colour class. delta-flat → no
    # arrow (a near-flat move shouldn't read as a direction); pos/neg get ↑/↓ so the
    # arrow + colour are unambiguous (↓ + red = decrease).
    return "↑ " if cls == "delta-pos" else ("↓ " if cls == "delta-neg" else "")


def vitals_pill(abs_txt, rel_txt, cls):
    """Vitals-card pill text: arrow + absolute change + · + relative %, e.g.
    '↓ −$135K · −32%' or '↓ −0.63pp · −31%'. No 'Δ' (that stays in table headers).
    The arrow follows `cls` (delta-pos/neg/flat). `abs_txt` is the metric-formatted
    absolute change (money / comma-int / pp); `rel_txt` is the relative % string."""
    parts = [p for p in (abs_txt, rel_txt) if p]
    return _arrow(cls) + " · ".join(parts)


def _signed_money(delta):
    # Absolute money change with an explicit sign and a unicode minus, matching the
    # money() magnitude formatting ($NNN.NK / $N.NM): e.g. -135000 → "−$135K".
    return ("−" if delta < 0 else "+") + money(abs(delta))


def _signed_int(delta):
    # Absolute comma-integer change with an explicit sign + unicode minus.
    return ("−" if delta < 0 else "+") + f"{abs(int(round(delta))):,}"


def _signed_pp(cur, pri):
    # Absolute pp change with an explicit sign + unicode minus, 2 dp (e.g. "−0.63pp").
    d = cur - pri
    return ("−" if d < 0 else "+") + f"{abs(d):.2f}pp"


def rel_pct_of_pp(cur, pri):
    # Relative % for a rate metric: pp change / prior × 100, signed (e.g. "−31%").
    if not pri:
        return ""
    r = (cur - pri) / pri * 100
    return f"{'+' if r >= 0 else '−'}{abs(r):.0f}%"


def rel_pct(cur, pri):
    # Relative % change for a money/count metric, signed with a unicode minus
    # (e.g. "−32%") so the vitals pill reads consistently with the pp variant.
    if not pri:
        return ""
    r = (cur - pri) / pri * 100
    return f"{'+' if r >= 0 else '−'}{abs(r):.0f}%"


def numparse(s):
    s = s.replace(",", "").replace("$", "").replace("%", "").strip(); mult = 1
    if s.endswith("K"): mult = 1e3; s = s[:-1]
    if s.endswith("M"): mult = 1e6; s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Markdown-section / table parsing (the CE Health .md is regular GFM)
# ─────────────────────────────────────────────────────────────────────────────

def section(md, name):
    # Header match is single-line ([^\n]* — never crosses newlines, so e.g.
    # "Funnel" matches "## 4. Funnel" and NOT greedily through "## Funnel by
    # Language"); the body capture stays multi-line via re.S.
    m = re.search(rf'^##[^\n]*{re.escape(name)}[^\n]*$(.*?)(?=^## |\Z)', md, re.M | re.S)
    return m.group(1) if m else ""


def tables_in(text):
    """Return list of (headers, rows) for every GFM pipe table in `text`."""
    out = []; lines = text.split("\n"); i = 0
    while i < len(lines):
        if "|" in lines[i] and i + 1 < len(lines) and re.match(r'^\s*\|?\s*:?-+', lines[i + 1]):
            hdr = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            j = i + 2; rows = []
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")]); j += 1
            out.append((hdr, rows)); i = j
        else:
            i += 1
    return out


def _cell(c):
    """Escape, then convert markdown bold/italic so **TOTAL** renders bold."""
    s = _html.escape(c.strip())
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', s)
    return s


def _is_num(c):
    t = c.strip().strip('*')
    return bool(re.match(r'^[-+−]?[$]?[\d,]+(\.\d+)?\s*(%|pp|K|M|x)?', t)) and any(ch.isdigit() for ch in t)


# ── Delta-aware cell rendering (CE Health tables that carry pre/post deltas) ──
# Scoped <style> for the two-line value+delta cell and grouped header bands.
# Scoped to #tab-cehealth (the composite wraps this fragment in that pane id), so
# it can't leak into other tabs and we never touch the shared visual_kit style.
CEH_TABLE_STYLE = (
    "<style>"
    "#tab-cehealth .ceh-val{font-weight:600;color:#1a1a2e;}"
    "#tab-cehealth .ceh-chg{display:block;font-size:11px;font-weight:600;margin-top:2px;line-height:1.1;}"
    "#tab-cehealth .ceh-chg.up{color:#2e7d32;}"
    "#tab-cehealth .ceh-chg.down{color:#c62828;}"
    "#tab-cehealth .ceh-chg.flat{color:#b08900;}"
    "#tab-cehealth th.ceh-group{text-align:center;background:#f0f2f8;color:#5a6478;"
    "font-size:10px;letter-spacing:.6px;text-transform:uppercase;"
    "border-bottom:1px solid #e0e4ef;padding:6px 12px;}"
    # Blue vertical dividers at group boundaries (left-border on the first column of
    # each group, header + body).
    "#tab-cehealth table .ceh-gdiv{border-left:2px solid #6c8ebf;}"
    # Benchmark / step flag chips (amber=watch, red=off).
    "#tab-cehealth .ceh-flag{display:inline-block;margin-left:5px;padding:1px 6px;"
    "border-radius:9px;font-size:10px;font-weight:700;vertical-align:middle;}"
    "#tab-cehealth .ceh-flag.warn{background:#fff3e0;color:#b26a00;}"
    "#tab-cehealth .ceh-flag.bad{background:#fdecea;color:#c62828;}"
    # Concentration highlight (rows up to ~80% cumulative revenue) + classification pill.
    "#tab-cehealth tr.ceh-conc td{background:#eafaf0;}"
    "#tab-cehealth .ceh-class{display:inline-block;margin:0 0 8px;padding:3px 10px;"
    "border-radius:6px;font-size:11px;font-weight:700;background:#eef2fb;color:#3a4a8a;}"
    # Conditional-formatting backgrounds for table cells (completion rate < 80%).
    "#tab-cehealth td.ceh-cr-low{background:#fdecea;}"
    # Completion-rate < 80% on a metric card → red value (same threshold, card form).
    "#tab-cehealth .metric-card .post.ceh-cr-low-val{color:#c0392b;}"
    "#tab-cehealth .ceh-prime{display:inline-block;margin-left:6px;padding:1px 6px;"
    "border-radius:9px;font-size:10px;font-weight:700;background:#e8edf7;color:#3a4a8a;}"
    # Truncate long experience names (TGID sticky 2nd column) with ellipsis; the
    # full name is in the span's title attribute (hover to read).
    "#tab-cehealth .ceh-exp{display:block;max-width:200px;overflow:hidden;"
    "text-overflow:ellipsis;white-space:nowrap;}"
    # Landing-page URL cell: truncate with ellipsis, full URL in the title (hover).
    # Source landing URLs are NOT truncated (unlike experience names), so this works.
    "#tab-cehealth .ceh-lpurl{display:block;max-width:340px;overflow:hidden;"
    "text-overflow:ellipsis;white-space:nowrap;}"
    # New-CE / new-experience badge (replaces awkward trailing 'new' literal).
    "#tab-cehealth .ceh-new{display:inline-block;margin-left:6px;padding:1px 6px;"
    "border-radius:9px;font-size:10px;font-weight:700;background:#eef2fb;color:#5a6478;"
    "vertical-align:middle;}"
    "</style>"
)

_TRAIL_DELTA = re.compile(r'^(?P<main>.*\S)\s+(?P<delta>[+\-−][\d.,]+(?:pp|%))(?:\s*\([^)]*\))?$')
_PURE_DELTA = re.compile(r'^(?P<delta>[+\-−][\d.,]+(?:pp|%))(?:\s*\([^)]*\))?$')
# New-CE / "no prior" markers that trail a value in TGID cells (e.g. "$49.2K new",
# "97.3% —"). A lone em-dash means "no prior" → drop it; "new" → small muted badge.
_TRAIL_NEW = re.compile(r'^(?P<main>.*\S)\s+new$')
_TRAIL_NOPRIOR = re.compile(r'^(?P<main>.*\S)\s+[—–-]$')


# ─────────────────────────────────────────────────────────────────────────────
# Tunable presentation thresholds — heuristics for flags/labels, NOT category-
# specific truths. Centralised here so they can be retuned in one place.
# ─────────────────────────────────────────────────────────────────────────────
# Cumulative-Share % up to which TGIDs are counted "concentrated" (the green band
# in §8, and the Concentrated/Normal/Fragmented label). ~80% is a Pareto heuristic.
TGID_CONCENTRATION_PCT = 80.0
# Derived-S2O (S2C×C2O) % below which a high-traffic TGID is flagged "low S2O" in §8.
TGID_LOW_S2O_PCT = 8.0
# Near-flat delta band: a delta whose magnitude is below this is treated as "flat"
# (amber) rather than up/down. Separate thresholds for pp vs % deltas.
NEAR_FLAT_PP = 1.0   # |Δ| < 1pp → flat
NEAR_FLAT_PCT = 5.0  # |Δ| < 5%  → flat


def _delta_dir(delta):
    """Classify a delta token like '+3.7pp' / '-63%' → 'up' | 'down' | 'flat'.
    Near-flat band (amber): |Δ| < NEAR_FLAT_PP (pp) or < NEAR_FLAT_PCT (%). Tunable."""
    m = re.match(r'^([+\-−])([\d.,]+)(pp|%)$', delta.replace('−', '-').strip())
    if not m:
        return 'flat'
    sign, num, unit = m.groups()
    val = float(num.replace(',', '')) * (-1 if sign == '-' else 1)
    thr = NEAR_FLAT_PP if unit == 'pp' else NEAR_FLAT_PCT
    return 'flat' if abs(val) < thr else ('up' if val > 0 else 'down')


def _cell_split(c):
    """Render a cell that may carry a trailing delta as a two-line value+delta, a
    lone delta as a single coloured token, a new-CE/no-prior marker as a value +
    muted badge / bare value, else fall back to plain `_cell`."""
    s = c.strip()
    m = _TRAIL_DELTA.match(s)
    if m:
        d = _delta_dir(m.group('delta'))
        return (f'<span class="ceh-val">{_cell(m.group("main"))}</span>'
                f'<span class="ceh-chg {d}">{_html.escape(m.group("delta"))}</span>')
    m = _PURE_DELTA.match(s)
    if m:
        d = _delta_dir(m.group('delta'))
        # Colour the whole token (sign classified from the delta), preserving any
        # trailing parenthetical like "+31% (+$32.1K)" so no figure is dropped.
        return f'<span class="ceh-chg {d}">{_html.escape(s)}</span>'
    # New-CE marker (e.g. "$49.2K new") → value + small muted "new" badge, not inline.
    m = _TRAIL_NEW.match(s)
    if m:
        return f'<span class="ceh-val">{_cell(m.group("main"))}</span><span class="ceh-new">new</span>'
    # Lone trailing em-dash ("no prior", e.g. "97.3% —") → drop it, show the value.
    m = _TRAIL_NOPRIOR.match(s)
    if m:
        return f'<span class="ceh-val">{_cell(m.group("main"))}</span>'
    return _cell(c)


def _lead_num(s):
    """Numeric value of a cell that may carry a trailing delta / 'new' / no-prior
    token (e.g. '88.1% -1.8pp' → 88.1, '97.3% —' → 97.3). Plain `numparse` returns
    None on such combined cells because it tries to float the whole string — so any
    threshold/colour-scale formatting that reads raw value+delta cells stays dormant
    unless it first peels off the leading value. Falls back to numparse for clean
    cells (the value columns of split tables) and returns None for em-dashes."""
    s = (s or "").strip()
    for rx in (_TRAIL_DELTA, _TRAIL_NEW, _TRAIL_NOPRIOR):
        m = rx.match(s)
        if m:
            return numparse(m.group("main"))
    return numparse(s)


def styled_table(hdr, rows, highlight_first=False, maxrows=None, sticky_cols=0,
                 sticky_widths=None, split_deltas=False, groups=None,
                 div_cols=None, row_classes=None, cell_classes=None, cell_html=None):
    """Visual-kit styled table. `sticky_cols` freezes the first N columns on
    horizontal scroll (position:sticky), `sticky_widths` their px widths.
    `split_deltas` renders 'value + trailing delta' cells as a bold value with a
    coloured delta beneath (and lone-delta cells coloured). `groups` is an ordered
    list of (label, span) rendered as a grouped header band above the column row
    (only when the spans sum to the column count — else skipped, never broken).
    `div_cols` is a set of column indices to receive a blue left-border divider
    (header + body). `row_classes` is an optional list (aligned to rows) of extra
    <tr> classes. `cell_classes`/`cell_html` are optional {(row, col): str} maps for
    per-cell extra classes / raw HTML content overrides (presentation formatting)."""
    if maxrows: rows = rows[:maxrows]
    div_cols = div_cols or set()
    cell_classes = cell_classes or {}
    cell_html = cell_html or {}

    ncol = len(hdr)
    numcol = [False] * ncol
    for ci in range(ncol):
        vals = [r[ci] for r in rows if ci < len(r)]
        if vals and sum(_is_num(v) for v in vals) >= max(1, len(vals) * 0.6):
            numcol[ci] = True
    sticky_widths = sticky_widths or [70, 200]

    def _offset(i):
        return sum(sticky_widths[:i]) if i < len(sticky_widths) else sum(sticky_widths)

    def _stick(i, is_head):
        if i >= sticky_cols: return ""
        bg = "#f5f6fa" if is_head else "#fff"
        z = 5 if is_head else 2
        w = sticky_widths[i] if i < len(sticky_widths) else 120
        return f'position:sticky;left:{_offset(i)}px;background:{bg};z-index:{z};min-width:{w}px;box-shadow:1px 0 0 #e8ebf4;'

    def _classes(*parts):
        cl = [p for p in parts if p]
        return f' class="{" ".join(cl)}"' if cl else ''

    th = ""
    for i, h in enumerate(hdr):
        cls = _classes('num' if numcol[i] else '', 'ceh-gdiv' if i in div_cols else '')
        st = _stick(i, True)
        style_attr = ' style="' + st + '"' if st else ''
        th += "<th" + cls + style_attr + ">" + _cell(h) + "</th>"
    # Optional grouped header band — only when spans line up with the columns.
    grp = ""
    if groups and sum(int(s) for _, s in groups) == ncol:
        # Track which leading column each band starts at, to carry the blue divider
        # up into the band cell too.
        gcells = ""; col0 = 0
        for lbl, s in groups:
            span = int(s)
            gdiv = 'ceh-gdiv' if col0 in div_cols else ''
            colspan = f' colspan="{span}"' if span > 1 else ''
            gcells += f'<th{_classes("ceh-group", gdiv)}{colspan}>{_html.escape(str(lbl))}</th>'
            col0 += span
        grp = f"<tr>{gcells}</tr>"
    trs = ""
    for k, r in enumerate(rows):
        extra = (row_classes[k] if row_classes and k < len(row_classes) else '')
        rcls = _classes('highlight-row' if (highlight_first and k == 0) else '', extra)
        tds = ""
        for i, c in enumerate(r):
            cls = _classes('num' if (i < ncol and numcol[i]) else '',
                           'ceh-gdiv' if i in div_cols else '',
                           cell_classes.get((k, i), ''))
            st = _stick(i, False)
            style_attr = ' style="' + st + '"' if st else ''
            if (k, i) in cell_html:
                inner = cell_html[(k, i)]
            else:
                inner = _cell_split(c) if split_deltas else _cell(c)
            tds += "<td" + cls + style_attr + ">" + inner + "</td>"
        trs += f"<tr{rcls}>{tds}</tr>"
    return f'<div style="overflow-x:auto;"><table><thead>{grp}<tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def _sparkline(values, w=90, h=22):
    """Inline SVG polyline sparkline for a row's monthly trend. `values` is a list
    of floats/None; normalised to the row's own min/max so the shape (not the
    absolute level) reads. No JS, no Plotly. Returns a small inline <svg>."""
    pts = [v for v in values if v is not None]
    if len(pts) < 2:
        return ""
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1.0
    pad = 2
    n = len(values)
    step = (w - 2 * pad) / (n - 1) if n > 1 else 0
    coords = []
    for i, v in enumerate(values):
        x = pad + i * step
        vv = pts[0] if v is None else v
        y = (h - pad) - ((vv - lo) / span) * (h - 2 * pad)
        coords.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(coords)
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'style="vertical-align:middle;" preserveAspectRatio="none">'
            f'<polyline fill="none" stroke="#4a6fd4" stroke-width="1.5" '
            f'stroke-linejoin="round" stroke-linecap="round" points="{poly}"/></svg>')


def block(title, bid, inner, verdict=None, summary=None, collapsed=False):
    """Collapsible analysis block. The title is a <button class="ceh-toggle"> (not
    an <a>, so the template's anchor router never intercepts it); `inner` lives in a
    <div class="ceh-body"> that hides when collapsed. An optional `summary` renders a
    <div class="ceh-summary"> BETWEEN the header and body so it stays visible while
    collapsed (used for the Channel + Lead-time deterministic callouts). `collapsed`
    sets the initial state; the default-open set is centralised in build_fragment."""
    v = f'<div class="verdict-line neutral">{verdict}</div>' if verdict else ''
    summ = f'<div class="ceh-summary">{summary}</div>' if summary else ''
    state = ' ceh-collapsed' if collapsed else ''
    aria = 'false' if collapsed else 'true'
    return (
        f'<div class="analysis-block{state}" id="{bid}">'
        f'<button type="button" class="ceh-toggle" aria-expanded="{aria}">'
        f'<span class="ceh-chev" aria-hidden="true">▾</span>'
        f'<span class="block-title">{title}</span></button>'
        f'{summ}'
        f'<div class="ceh-body">{v}{inner}</div>'
        f'</div>'
    )


# Fragment-scoped collapse CSS + JS. Scoped to #tab-cehealth so it can't leak into
# other tabs. The <script> (a) toggles a section on its header-button click and (b)
# auto-expands a block when targeted — the template's anchor router preventDefault()s
# cross-tab links, so :target CSS alone won't fire; we handle it in JS for both the
# click path (doc-level listener on a[href^="#cehealth-"]) and initial load (hash).
CEH_COLLAPSE_STYLE = (
    "<style>"
    "#tab-cehealth .ceh-toggle{display:flex;align-items:center;gap:10px;width:100%;"
    "background:none;border:none;border-bottom:1px solid #e3e7f0;padding:8px 6px;"
    "margin:0 0 10px;cursor:pointer;text-align:left;font:inherit;"
    "border-radius:5px 5px 0 0;transition:background .15s ease;}"
    "#tab-cehealth .ceh-toggle:hover{background:#f4f6fb;}"
    "#tab-cehealth .ceh-toggle .block-title{margin-bottom:0;font-size:16px;font-weight:700;color:#1a1a2e;}"
    "#tab-cehealth .ceh-chev{font-size:16px;color:#6a7690;transition:transform .18s ease;flex:0 0 auto;}"
    "#tab-cehealth .analysis-block.ceh-collapsed .ceh-chev{transform:rotate(-90deg);}"
    "#tab-cehealth .analysis-block.ceh-collapsed .ceh-body{display:none;}"
    "#tab-cehealth .ceh-summary{font-size:12.5px;line-height:1.5;color:#3a4a6a;"
    "background:#f4f6fb;border-left:3px solid #6c8ebf;border-radius:4px;"
    "padding:8px 12px;margin:0 0 8px;}"
    "</style>"
)
CEH_COLLAPSE_SCRIPT = (
    "<script>(function(){"
    "var root=document.getElementById('tab-cehealth');if(!root)return;"
    "function setOpen(b,open){if(!b)return;b.classList.toggle('ceh-collapsed',!open);"
    "var t=b.querySelector('.ceh-toggle');if(t)t.setAttribute('aria-expanded',open?'true':'false');"
    # On expand, resize any Plotly chart inside — it was drawn at ~700px default while the
    # section was display:none; without this it stays stuck at that width on first open.
    "if(open&&window.Plotly){setTimeout(function(){"
    "b.querySelectorAll('.js-plotly-plot').forEach(function(el){"
    "try{window.Plotly.Plots.resize(el);}catch(e){}});},30);}}"
    "root.addEventListener('click',function(e){"
    "var t=e.target.closest('.ceh-toggle');if(!t||!root.contains(t))return;"
    "var b=t.closest('.analysis-block');setOpen(b,b.classList.contains('ceh-collapsed'));});"
    # Auto-expand when a cross-tab/in-tab anchor targets a CE Health block.
    "document.addEventListener('click',function(e){"
    "var a=e.target.closest('a[href^=\"#cehealth-\"]');if(!a)return;"
    "var b=document.getElementById(a.getAttribute('href').slice(1));"
    "if(b&&b.classList.contains('analysis-block'))setOpen(b,true);});"
    "function fromHash(){var h=location.hash;if(h&&h.indexOf('#cehealth-')===0){"
    "var b=document.getElementById(h.slice(1));"
    "if(b&&b.classList.contains('analysis-block'))setOpen(b,true);}}"
    "window.addEventListener('hashchange',fromHash);fromHash();"
    "})();</script>"
)

# Funnel-by-dimension dropdown: a <select> that shows one .ceh-fdim panel at a
# time. Delegated listener scoped to #tab-cehealth (matches the collapse pattern).
CEH_FDIM_STYLE = (
    "<style>"
    "#tab-cehealth .ceh-fdim-sel{font-size:13px;padding:4px 8px;border:1px solid #d6dbe8;"
    "border-radius:6px;background:#fff;color:#1a1a2e;margin:2px 0 10px;}"
    "</style>"
)
CEH_FDIM_SCRIPT = (
    "<script>(function(){var root=document.getElementById('tab-cehealth');if(!root)return;"
    "root.querySelectorAll('.ceh-fdim-sel').forEach(function(sel){"
    "sel.addEventListener('change',function(){var w=sel.closest('.ceh-fdim-wrap');if(!w)return;"
    "w.querySelectorAll('.ceh-fdim').forEach(function(d){"
    "d.style.display=(d.getAttribute('data-fdim')===sel.value)?'':'none';});});});"
    "})();</script>"
)


def build_fdim_dropdown(panels, label="Break funnel down by:"):
    """panels: list of (key, label, html). Returns a dropdown widget showing one
    panel at a time (first open by default). `label` is the prompt text (e.g.
    "Compare current vs:" for the TGID MoM/YoY toggle). Empty string if no panels.
    The shared CEH_FDIM_SCRIPT is a delegated listener over every .ceh-fdim-wrap on
    the page, so multiple independent dropdowns coexist with no extra JS."""
    if not panels:
        return ""
    opts = "".join('<option value="{}">{}</option>'.format(k, _html.escape(lbl))
                   for k, lbl, _ in panels)
    divs = "".join(
        '<div class="ceh-fdim" data-fdim="{}"{}>{}</div>'.format(
            k, "" if i == 0 else ' style="display:none"', h)
        for i, (k, lbl, h) in enumerate(panels))
    return ('<div class="ceh-fdim-wrap"><label style="font-size:12px;color:#777;'
            'margin-right:6px;">{}</label>'
            '<select class="ceh-fdim-sel">{}</select>{}</div>'.format(
                _html.escape(label), opts, divs))


def _subhead(t):
    return f'<div style="font-size:13px;font-weight:700;color:#2a2a44;margin:14px 0 6px;">{t}</div>'


# ─────────────────────────────────────────────────────────────────────────────
# Query 1 (via bq CLI) — raw revenue-component rows for the 5-factor Shapley
# ─────────────────────────────────────────────────────────────────────────────

# Funnel traffic + converters (CE-level ALL row), lifted from cvr-rca q1_base.sql.
_FUNNEL_SQL = """
WITH base AS (
  SELECT
    user_id,
    MAX(CASE WHEN has_order_completed THEN 1 ELSE 0 END) AS order_completed,
    CASE
      WHEN event_date BETWEEN '{pre_start}' AND '{pre_end}' THEN 'pre'
      WHEN event_date BETWEEN '{post_start}' AND '{post_end}' THEN 'post'
    END AS period
  FROM `{project}.{dataset}.mixpanel_user_page_funnel_progression`
  WHERE combined_entity_id = '{ce_id}'
    AND event_date BETWEEN '{pre_start}' AND '{post_end}'
    -- No page_type whitelist: all LP types.
    -- PMax INCLUDED here (no exclusion): the §7 Shapley decomposes the all-channels
    -- revenue numerator (combined_entity_stats), so its traffic + converter basis must
    -- be all-channels too for the 5-factor identity to reconcile. NOTE: this diverges
    -- from the Omni dashboard funnel + the §4 funnel cards, which stay PMax-excluded.
  GROUP BY 1, 3
)
SELECT
  period,
  COUNT(DISTINCT user_id) AS overall_traffic,
  COUNT(DISTINCT CASE WHEN order_completed = 1 THEN user_id END) AS users_order_completed
FROM base
WHERE period IS NOT NULL
GROUP BY period
"""

# Booking / revenue components (combined_entity_stats), lifted from
# ce_health.py:fetch_ce_health. `revenue` here is sum_revenue = booking revenue
# (revenue_actual) — the figure the 5-factor identity reconstructs.
_STATS_SQL = """
SELECT
  CASE WHEN report_date BETWEEN '{pre_start}' AND '{pre_end}' THEN 'pre' ELSE 'post' END AS period,
  SUM(count_orders) AS count_orders,
  SUM(sum_order_value) AS gross_bookings,
  SUM(sum_order_value_completed) AS gross_bookings_completed,
  SUM(sum_revenue) AS revenue
FROM `{project}.{dataset}.combined_entity_stats`
WHERE combined_entity_id = '{ce_id}'
  AND report_date BETWEEN '{pre_start}' AND '{post_end}'
GROUP BY period
"""


def _bq_json(sql):
    """Run a read-only query via the bq CLI and return parsed JSON rows.

    Uses the same project/location CE Health's BigQuery client uses. Raises on
    any failure so the caller can fall back to CE Health's §7 table verbatim.
    """
    proc = subprocess.run(
        ["bq", "query", "--use_legacy_sql=false", "--format=json",
         "--max_rows=10000", f"--project_id={PROJECT_ID}", f"--location={BQ_LOCATION}", sql],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"bq query failed: {proc.stderr.strip()[:500]}")
    return json.loads(proc.stdout or "[]")


def query_raw(ce_id, windows):
    """Build {'pre': {...}, 'post': {...}} of the raw Shapley inputs via Query 1.

    Returns the dict on success, or None on any failure (caller falls back)."""
    pre, post = windows["prior"], windows["current"]
    params = dict(project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
                  pre_start=pre[0], pre_end=pre[1], post_start=post[0], post_end=post[1])
    funnel = _bq_json(_FUNNEL_SQL.format(**params))
    stats = _bq_json(_STATS_SQL.format(**params))
    raw = {"pre": {}, "post": {}}
    for row in funnel:
        p = row["period"]
        raw[p]["overall_traffic"] = float(row["overall_traffic"])
        raw[p]["users_order_completed"] = float(row["users_order_completed"])
    for row in stats:
        p = row["period"]
        raw[p]["count_orders"] = float(row["count_orders"])
        raw[p]["gross_bookings"] = float(row["gross_bookings"])
        raw[p]["gross_bookings_completed"] = float(row["gross_bookings_completed"])
        raw[p]["revenue"] = float(row["revenue"])
    for p in ("pre", "post"):
        need = {"overall_traffic", "users_order_completed", "count_orders",
                "gross_bookings", "gross_bookings_completed", "revenue"}
        if not need.issubset(raw[p]):
            raise RuntimeError(f"Query 1 returned incomplete data for '{p}': {sorted(raw[p])}")
    return raw


# ─────────────────────────────────────────────────────────────────────────────
# Canonical 5-factor Shapley revenue bridge
#   revenue = traffic × cvr × aov × completion × take_rate
# CVR here = orders / users (ORDER-based) — it folds the old users→converters→orders
# steps into one factor, so there is NO orders-per-converter term (its leaky funnel
# converter denominator is gone). Matches ce_health.compute_shapley_for_ce exactly.
# All 120 permutations; unattributable = actual_delta − sum(contributions) ≈ $0.
# ─────────────────────────────────────────────────────────────────────────────

_FAC = ["traffic", "cvr", "aov", "completion_rate", "take_rate"]
_FLBL = {"traffic": "Traffic", "cvr": "CVR",
         "aov": "AOV", "completion_rate": "Completion Rate", "take_rate": "Take Rate"}


def _facs(r):
    return dict(
        traffic=r["overall_traffic"],
        # CVR = orders / users (folds in orders-per-converter); telescopes without
        # a converter count: traffic·(O/U)·(GB/O)·(GBC/GB)·(rev/GBC) = rev.
        cvr=r["count_orders"] / r["overall_traffic"],
        aov=r["gross_bookings"] / r["count_orders"],
        completion_rate=r["gross_bookings_completed"] / r["gross_bookings"],
        take_rate=r["revenue"] / r["gross_bookings_completed"],
    )


def _decompose(pre, post):
    sh = {f: 0.0 for f in _FAC}
    for perm in _perms(_FAC):
        for i, factor in enumerate(perm):
            term = 1.0
            for j, f in enumerate(perm):
                term *= post[f] if j < i else ((post[f] - pre[f]) if j == i else pre[f])
            sh[factor] += term
    n = _fact(len(_FAC))
    return {f: sh[f] / n for f in _FAC}


def build_shapley_block(raw, windows, insight=None):
    """The §7 corrected 5-factor booking-revenue waterfall (Plotly). When `insight`
    is given (the LLM section callout), it becomes the section-top `summary` and the
    deterministic `verdict` is dropped (the drag/lift detail is already in the chart);
    otherwise the deterministic verdict renders as before."""
    pf, qf = _facs(raw["pre"]), _facs(raw["post"])
    contrib = _decompose(pf, qf)
    pre_rev, post_rev = raw["pre"]["revenue"], raw["post"]["revenue"]
    delta = post_rev - pre_rev
    unattr = delta - sum(contrib.values())
    net_pct = delta / pre_rev * 100

    def _sm(v):
        return ("+" if v >= 0 else "−") + money(abs(v))

    pre_lbl = f"Pre ({windows['prior'][0]} – {windows['prior'][1]})"
    post_lbl = f"Post ({windows['current'][0]} – {windows['current'][1]})"
    x = ["Pre"] + [_FLBL[f] for f in _FAC] + ["Unattributable", "Post"]
    y = [round(pre_rev, 2)] + [round(contrib[f], 2) for f in _FAC] + [round(unattr, 2), round(post_rev, 2)]
    measure = ["absolute"] + ["relative"] * (len(_FAC) + 1) + ["total"]
    text = [money(pre_rev)] + [_sm(contrib[f]) for f in _FAC] + [_sm(unattr), money(post_rev)]
    drags = [f"{_FLBL[k]} ({_sm(v)})" for k, v in sorted(contrib.items(), key=lambda x: x[1]) if v < 0][:2]
    lifts = [f"{_FLBL[k]} ({_sm(v)})" for k, v in sorted(contrib.items(), key=lambda x: -x[1]) if v > 0][:2]

    verdict = (
        f"Booking revenue {'fell' if delta < 0 else 'rose'} {_sm(delta)} ({net_pct:.1f}%) "
        f"Pre → Post. Biggest {'drags' if drags else 'movers'}: {', '.join(drags) or '—'}; "
        f"offset by {', '.join(lifts) or '—'}. The 5-factor identity reconciles fully "
        f"({_sm(unattr)} unattributable). <em>Note: this decomposes <strong>Actual Revenue</strong>; "
        f"the §1 headline card shows <strong>Predicted Revenue</strong>.</em>"
    )
    inner = f'''<div id="chart-cehealth-shapley" class="chart-container" style="width:100%"></div>
  <script>Plotly.newPlot('chart-cehealth-shapley',[{{
    type:'waterfall',orientation:'v',
    measure:{json.dumps(measure)},
    x:{json.dumps(x)},
    y:{json.dumps(y)},
    text:{json.dumps(text)},textposition:'outside',textfont:{{size:11,color:'#444'}},
    connector:{{line:{{color:'#cbd2e0',dash:'dot',width:1}}}},
    increasing:{{marker:{{color:'#43A047',line:{{color:'#fff',width:1}}}}}},
    decreasing:{{marker:{{color:'#c62828',line:{{color:'#fff',width:1}}}}}},
    totals:{{marker:{{color:'#3d5a8a',line:{{color:'#fff',width:1}}}}}},
    hovertemplate:'%{{x}}<br>cumulative %{{y:$,.0f}}<extra></extra>'
  }}],{{title:{{text:'Revenue Waterfall<br><span style=\\"font-size:11px;color:#888\\">{pre_lbl} → {post_lbl} · {_sm(delta)} ({net_pct:.1f}%)</span>',font:{{size:14,color:'#1a1a2e'}},x:0.5,xanchor:'center'}},
    height:440,autosize:true,margin:{{l:75,r:80,t:64,b:104}},plot_bgcolor:'#fff',paper_bgcolor:'#fff',
    font:{{family:'-apple-system,sans-serif',size:11,color:'#1a1a2e'}},showlegend:false,
    yaxis:{{title:'Revenue (USD)',tickprefix:'$',gridcolor:'#eef',zerolinecolor:'#ccc'}},
    xaxis:{{tickangle:15}}}},
    {{responsive:true,displayModeBar:false}});</script>
  <p style="font-size:12px;color:#777;margin-top:8px;">Drivers reconcile to total revenue, calculated <strong>including PMax</strong> (all channels). <strong>CVR here = orders ÷ users</strong> (it absorbs orders-per-converter — no separate factor), so it differs from the §2 vitals CVR card (converters ÷ users, Omni / PMax-excluded); the funnel section also excludes PMax.</p>'''
    return block("3. Driver Diagnosis (Shapley)", "cehealth-shapley", inner,
                 verdict=(None if insight else verdict), summary=insight)


# ─────────────────────────────────────────────────────────────────────────────
# Build the fragment
# ─────────────────────────────────────────────────────────────────────────────

def card(label, post_val, delta_txt, delta_cls, pre_val=None, post_class=""):
    pre_html = f'<span class="pre">{pre_val}</span>' if pre_val else ''
    pc = f' {post_class}' if post_class else ''
    return (f'<div class="metric-card"><div class="label">{label}</div>'
            f'<div class="values">{pre_html}<span class="post{pc}">{post_val}</span></div>'
            f'<div class="delta {delta_cls}">{delta_txt}</div></div>')


# §8 user-context slot ordering + labels. Each tuple is
# (canonical-slot-name-as-written-in-user_context.md, display-label-in-report).
# Render order is the BGM reading order: orient (About) → bounds (Constraints,
# Failure modes) → analyst intent (priors/focus) → facts (events) → references.
_UCTX_SLOT_ORDER = [
    ("About this CE", "About this CE"),
    ("Constraints", "Constraints"),
    ("Known failure modes", "Known failure modes"),
    ("Hypothesis priors", "Analyst priors & focus"),
    ("Focus / direction", "Analyst priors & focus"),
    ("Known events", "Known events"),
    ("Important links", "Important links"),
]
# Slots we never surface as their own block (provenance / lens bookkeeping).
_UCTX_SLOT_SKIP = {"Sources"}


def _split_user_context_slots(md: str) -> dict:
    """Parse user_context.md into {slot-heading: body-markdown}. Slot headings are
    the `## ...` lines; the leading `# User Context ...` title is ignored. Returns
    {} if no `##` slots are found (caller then falls back to a verbatim embed)."""
    slots = {}
    cur = None
    buf = []
    for ln in md.splitlines():
        m = re.match(r'^##\s+(.*?)\s*$', ln)
        if m:
            if cur is not None:
                slots[cur] = "\n".join(buf).strip()
            cur = m.group(1).strip()
            buf = []
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        slots[cur] = "\n".join(buf).strip()
    return slots


def _uctx_constraints_block(body: str) -> str:
    """Render Constraints as warning chips/callout. Each bullet → a chip; non-bullet
    prose falls back to a single callout line."""
    items = [re.sub(r'^[-*]\s+', '', ln).strip()
             for ln in body.splitlines() if ln.strip()]
    items = [i for i in items if i]
    if not items:
        return ""
    chips = "".join(
        '<span style="display:inline-block;background:#fff4e5;color:#8a5200;'
        'border:1px solid #f0c890;border-radius:12px;padding:3px 11px;margin:3px 6px 3px 0;'
        f'font-size:12.5px;font-weight:600;">⚠ {c}</span>'
        for c in items
    )
    return ('<div style="background:#fffaf2;border-left:3px solid #e0a030;border-radius:4px;'
            f'padding:9px 12px;margin:2px 0 4px;">{chips}</div>')


def _uctx_links_block(body: str) -> str:
    """Render Important links as a small 2-col table (link · what it gives). Each
    bullet is parsed as 'link · description' or '[label](url) · description'."""
    rows = []
    for ln in body.splitlines():
        t = re.sub(r'^[-*]\s+', '', ln).strip()
        if not t:
            continue
        # Split on the first ' · ' (or ' - ' / ' — ') into link | description.
        parts = re.split(r'\s+[·\-—]\s+', t, maxsplit=1)
        link_raw = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ""
        # Bare URLs become anchors; existing markdown links pass through the renderer.
        if re.match(r'^https?://\S+$', link_raw):
            link_html = f'<a class="ref-link" href="{link_raw}">{link_raw}</a>'
        else:
            link_html = render_markdown_to_html(link_raw)
        desc_html = render_markdown_to_html(desc) if desc else ""
        rows.append(f"<tr><td>{link_html}</td><td>{desc_html}</td></tr>")
    if not rows:
        return ""
    return ('<div class="md-content"><table><thead><tr><th>Link</th>'
            f'<th>What it gives</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def user_context_subsection(run_dir: Path) -> str:
    """Fill §8 with user-provided + recent context if any was captured this run.

    Deterministic embed of already-distilled markdown (user_context.md +
    user_data_*.md + slack_context.md) — no synthesis, no new sub-agent. The
    user_context.md is SPLIT by its `## ...` slot headings and each slot rendered as
    its own labelled sub-block (Constraints as warning chips, Important links as a
    small table); a file with no recognizable slots falls back to the verbatim
    embed. 'What the RCA found against it' lives in the Summary; we just link there.
    Returns '' when nothing is present, so §8 renders exactly as before. Never fatal.
    """
    pieces = []
    has_provided = False  # true if the analyst actually supplied something (vs auto-Slack)
    try:
        uc = run_dir / "user_context.md"
        if uc.exists() and uc.read_text().strip():
            raw = uc.read_text().strip()
            slots = _split_user_context_slots(raw)
            rendered_any = False
            if slots:
                seen_labels = set()
                for slot_name, label in _UCTX_SLOT_ORDER:
                    body = slots.get(slot_name, "").strip()
                    if not body or slot_name in _UCTX_SLOT_SKIP:
                        continue
                    # Multiple source slots can map to one label (priors + focus);
                    # accumulate under the first occurrence, render once.
                    if slot_name == "Constraints":
                        block_html = _uctx_constraints_block(body)
                    elif slot_name == "Important links":
                        block_html = _uctx_links_block(body)
                    else:
                        block_html = f'<div class="md-content">{render_markdown_to_html(body)}</div>'
                    if not block_html:
                        continue
                    # If we've already emitted this label (priors then focus), append
                    # the body without repeating the subhead.
                    if label in seen_labels:
                        pieces.append((None, block_html))
                    else:
                        pieces.append((label, block_html))
                        seen_labels.add(label)
                    rendered_any = True
            if rendered_any:
                has_provided = True
            else:
                # No recognizable slots — fall back to the verbatim embed (as before).
                pieces.append(("Analyst context (focus · priors · known events)",
                               f'<div class="md-content">{render_markdown_to_html(raw)}</div>'))
                has_provided = True
        for p in sorted(run_dir.glob("user_data_*.md")):
            t = p.read_text().strip()
            if t:
                pieces.append((f"User data — {p.stem.replace('user_data_', '')}",
                               f'<div class="md-content">{render_markdown_to_html(t)}</div>'))
                has_provided = True
        sc = run_dir / "slack_context.md"
        if sc.exists():
            t = sc.read_text().strip()
            if t and "0 signals" not in t:
                pieces.append(("Recent Slack signals",
                               f'<div class="md-content">{render_markdown_to_html(t)}</div>'))
    except Exception:  # noqa: BLE001 — never let context embedding break the tab
        return ""
    if not pieces:
        return ""
    # Each piece carries its own subhead (or None to continue the prior label).
    inner = "".join(
        (f'{_subhead(title)}{body_html}' if title else body_html)
        for title, body_html in pieces
    )
    if has_provided:  # the Summary link only makes sense for analyst-supplied context
        inner += ('<p style="font-size:12px;color:#666;margin-top:10px;">What the RCA found '
                  'against this context → '
                  '<a class="ref-link" href="#summary-cross-reference">Summary ↗</a></p>')
    return inner


def _prior_headline(d: Path) -> str:
    """Best-effort one-line headline for a prior run — the root-cause sentence from
    findings.md, skipping the title/scaffold lines. '' if nothing usable."""
    f = d / "findings.md"
    try:
        if f.exists():
            for ln in f.read_text().splitlines():
                t = ln.strip().lstrip("#").strip().strip("*").strip()
                low = t.lower()
                if (t and not t.startswith(("---", "|", "<", "!", ">"))
                        and not low.startswith(("cvr-rca", "findings", "ce ", "run ",
                                                "root cause", "date", "window"))
                        and len(t) > 20):
                    return (t[:120] + "…") if len(t) > 120 else t
    except Exception:  # noqa: BLE001
        pass
    return ""


def prior_runs_block(run_dir: Path, ce_id) -> str:
    """'Past RCAs for this CE' — prior CE-RCA runs with the same ce_id (institutional
    memory). Scans sibling run folders, excludes the current run. '' if none/error."""
    if not ce_id:
        return ""
    try:
        rows = []
        for d in sorted(run_dir.parent.iterdir(), reverse=True):
            if not d.is_dir() or d.resolve() == run_dir.resolve():
                continue
            sc = d / "ce_health_report.json"
            if not sc.exists():
                continue
            try:
                j = json.loads(sc.read_text())
            except Exception:  # noqa: BLE001
                continue
            cid = j.get("ce_id") or j.get("metadata", {}).get("combined_entity_id")
            if str(cid) != str(ce_id):
                continue
            report = d / "report.html"
            link = (f'<a class="ref-link" href="file://{report}">open ↗</a>'
                    if report.exists() else "")
            rows.append((d.name, _prior_headline(d), link))
        if not rows:
            return ""
        body = "".join(f"<tr><td>{n}</td><td>{h}</td><td>{lk}</td></tr>"
                       for n, h, lk in rows[:5])
        return (f'{_subhead("Past RCAs for this CE")}'
                '<div class="md-content"><table><thead><tr><th>Run</th>'
                f'<th>Headline</th><th></th></tr></thead><tbody>{body}</tbody></table></div>')
    except Exception:  # noqa: BLE001 — never let history break the tab
        return ""


def _clean_history_md(md_section: str) -> str:
    """Drop CE Health's filesystem-search placeholders that never resolve in the
    bundle (no thoughts/shared dir), so §8 reads cleanly once we inject real content."""
    drop = ("Past perf audits:** None found", "Recent weekly reviews:** None found",
            "Slack context: searched by SKILL.md",
            "Add your context:")  # interactive CLI prompt — never belongs in the report
    return "\n".join(ln for ln in md_section.splitlines()
                     if not any(p in ln for p in drop))


def ce_history_block(run_dir: Path) -> str:
    """Synthesised historical trajectory written by the fire-and-forget CE-history
    sub-agent (`ce_history.md`). '' if absent or it found no prior runs."""
    f = run_dir / "ce_history.md"
    try:
        if not f.exists():
            return ""
        t = f.read_text().strip()
        if not t or "No prior RCAs found" in t or "no prior runs" in t.lower():
            return ""
        return (f'{_subhead("Historical trajectory")}'
                f'<div class="md-content">{render_markdown_to_html(t)}</div>')
    except Exception:  # noqa: BLE001
        return ""


def _tgid_groups(hdr):
    """Coalesce the Top-TGIDs columns into grouped header bands by column name.
    Returns an ordered [(label, span)] covering every column (blank label for the
    frozen identity cols / anything unmatched), so the band always lines up."""
    def label_of(h):
        n = h.strip().lower()
        if 'tgid' in n or 'experience' in n:
            return ''
        if 'rev' in n or n == 'share':
            return 'Revenue'
        # RPC (revenue-per-click) is a funnel-efficiency metric → Funnel group.
        if n in ('aov', 'cr', 'tr'):
            return 'Order Metrics'
        if 'sel users' in n or 'traffic' in n or n in ('s2c', 'c2o', 's2o', 'rpc'):
            return 'Funnel Metrics'
        if '0-2d' in n or '3-7d' in n or '7d+' in n:
            return 'Lead-time mix'
        return ''
    bands = []
    for h in hdr:
        lbl = label_of(h)
        if bands and bands[-1][0] == lbl:
            bands[-1][1] += 1
        else:
            bands.append([lbl, 1])
    # Only worth a band row if at least one real group was identified.
    return bands if any(lbl for lbl, _ in bands) else None


# ─────────────────────────────────────────────────────────────────────────────
# Wave A — rule-based (deterministic) presentation helpers
# ─────────────────────────────────────────────────────────────────────────────

# Default-open sections (every other block ships collapsed). One obvious place.
CEH_DEFAULT_OPEN = {"cehealth-vitals", "cehealth-l12m", "cehealth-shapley", "cehealth-funnel"}


def _col_idx(hdr, *names):
    """First header index whose lowercased text contains any of `names`. -1 if none."""
    low = [h.strip().lower() for h in hdr]
    for nm in names:
        for i, h in enumerate(low):
            if nm in h:
                return i
    return -1


def _flag_chip(kind, txt):
    return f'<span class="ceh-flag {kind}">{_html.escape(txt)}</span>'


# §3 Channel benchmark rules (Share, current period). Tunable in one place.
_CHAN_BENCH = {
    "Google PMax": (10.0, 5.0),   # (target %, tolerance pp)
    "Bing": (10.0, 5.0),
    "Organic": (5.0, 4.0),
}


def channel_flags_and_summary(hdr, rows):
    """Return ({row_idx: chip_html}, summary_html) for the channel table, from
    rule-based Share benchmarks. Deterministic; degrades to ({}, '') on odd shapes."""
    share_i = _col_idx(hdr, "share")
    name_i = _col_idx(hdr, "channel")
    if name_i < 0:
        name_i = 0  # fall back to the identity column if no "Channel" header
    if share_i < 0:
        return {}, ""
    shares = {}
    order = []
    for k, r in enumerate(rows):
        if share_i >= len(r):
            continue
        name = r[name_i].strip().strip("*")
        if name.upper() == "TOTAL":
            continue
        v = numparse(r[share_i])
        if v is None:
            # "<1%" → treat as ~0.5
            v = 0.5 if "<1" in r[share_i] else None
        if v is None:
            continue
        shares[name] = v
        order.append((k, name, v))
    if not shares:
        return {}, ""
    chips = {}
    lead_note = ""        # the primary-channel headline (always first)
    flag_notes = []       # deviations / leakage (surfaced first within the cap)
    ok_notes = []         # in-range channels (used only to pad the 2–3 lines)

    def _ki(name):
        return next((k for k, n, _ in order if n == name), None)
    # Primary channel = the highest-share channel (generalised — no hardcoded leader).
    # A healthy market is typically search-led, so flag only when search is NOT the
    # top channel; a "search" channel is any whose name mentions search.
    top_name = max(shares, key=shares.get)
    top_v = shares[top_name]
    search_names = [n for n in shares if "search" in n.lower()]
    top_is_search = "search" in top_name.lower()
    if search_names and not top_is_search:
        for sn in search_names:
            ki = _ki(sn)
            if ki is not None:
                chips[ki] = _flag_chip("bad", "not top")
        lead_note = (f"Primary channel is {top_name} ({top_v:.0f}%), not search-led "
                     f"(top search channel is below it) — investigate.")
    elif top_is_search and top_v < 45:
        ki = _ki(top_name)
        if ki is not None:
            chips[ki] = _flag_chip("warn", f"low ({top_v:.0f}%)")
        lead_note = f"{top_name} leads but at {top_v:.0f}% (below the ~50% norm)."
    else:
        lead_note = f"{top_name} leads at {top_v:.0f}% (primary channel)."
    # Known-channel Share benchmarks. Channels NOT in the dict degrade silently
    # (no false flag) — the dict is the allow-list of channels we have a norm for.
    for name, (tgt, tol) in _CHAN_BENCH.items():
        if name not in shares:
            continue
        v = shares[name]
        if abs(v - tgt) > tol:
            ki = _ki(name)
            if ki is not None:
                chips[ki] = _flag_chip("warn", f"{v:.0f}% vs ~{tgt:.0f}%")
            flag_notes.append(f"{name} {v:.0f}% (vs ~{tgt:.0f}% benchmark).")
        else:
            ok_notes.append(f"{name} {v:.0f}% in range.")
    # Cross-sell leakage: sum of EVERY channel whose name ends in "Cross-sell"
    # (generalised beyond Google/Bing) — combined > 10% is flagged.
    xs_names = [n for n in shares if n.strip().lower().endswith("cross-sell")]
    xs = sum(shares[n] for n in xs_names)
    if xs > 10:
        for nm in xs_names:
            ki = _ki(nm)
            if ki is not None:
                chips[ki] = _flag_chip("bad", "leakage")
        flag_notes.append(f"Cross-sell combined {xs:.0f}% (>10%) — watch for keyword leakage.")
    elif xs > 0:
        ok_notes.append(f"Cross-sell combined {xs:.0f}% — within tolerance.")
    # Lead with the primary-channel verdict, then problems, padding with in-range notes
    # up to 3 lines so the material flags are never crowded out.
    notes = ([lead_note] if lead_note else []) + flag_notes + ok_notes
    summary = " ".join(notes[:3])
    return chips, summary


# §9 Lead-time bands → dominant-band callout.
def leadtime_summary(hdr, rows):
    """2–3 line callout comparing the dominant lead-time band's Share to the typical
    0–2D-led pattern. '' on odd shapes."""
    band_i = _col_idx(hdr, "band")
    if band_i < 0:
        band_i = 0  # fall back to the identity column if no "Band" header
    share_i = _col_idx(hdr, "share")
    if share_i < 0:
        return ""
    bands = []
    for r in rows:
        if share_i >= len(r):
            continue
        name = r[band_i].strip().strip("*")
        if name.upper() == "TOTAL":
            continue
        v = numparse(r[share_i])
        if v is not None:
            bands.append((name, v))
    if not bands:
        return ""
    dom_name, dom_v = max(bands, key=lambda x: x[1])
    short = next((v for n, v in bands if "0-2" in n), None)
    if dom_name.startswith("0-2"):
        return (f"Bookings are 0–2D-led ({dom_v:.0f}% in the 0–2D band) — the typical "
                f"near-term-purchase pattern.")
    msg = f"{dom_name} drives {dom_v:.0f}% of bookings"
    if short is not None:
        msg += f" vs {short:.0f}% in 0–2D"
    msg += " — long-lead skew vs the usual 0–2D-led pattern."
    return msg


# §2 Vitals — the primary driver comes from the §7 Shapley decomposition (factor
# with the largest |contribution|), NOT from the largest vitals Δ (which mislabels
# Revenue). `shapley_top_vitals_row` maps that factor to a vitals table row if one
# exists, so we can bold it; factors with no vitals row (Traffic, CVR) → note only.

# Shapley factor → vitals-row matcher. Each entry: (factor_key, [name substrings]).
# Factors absent here (traffic, cvr) deliberately map to no vitals row.
_SHAP_VITALS_MATCH = {
    "aov": ["aov"],
    "take_rate": ["take rate", "take_rate", "tr"],
    "completion_rate": ["completion", "cr"],
}


def shapley_top_driver(contrib):
    """Given the §7 5-factor `contrib` dict, return (factor_key, signed_contribution)
    for the factor with the largest |contribution|. None if empty."""
    if not contrib:
        return None
    f = max(contrib, key=lambda k: abs(contrib[k]))
    return f, contrib[f]


def shapley_top_vitals_row(hdr, rows, factor):
    """Index of the vitals row that corresponds to a Shapley `factor`, or None if the
    factor has no vitals row (Traffic / CVR) or no row matches."""
    subs = _SHAP_VITALS_MATCH.get(factor)
    if not subs:
        return None
    for k, r in enumerate(rows):
        if not r:
            continue
        nm = r[0].strip().strip("*").lower()
        for s in subs:
            # Exact match for short tokens (tr/cr/orders) to avoid false hits.
            if (len(s) <= 3 and nm == s) or (len(s) > 3 and s in nm):
                return k
    return None


def _band_divider_cols(groups, hdr_len):
    """Column indices that start a new (non-blank) group band → blue divider there.
    Skips the leading blank/identity group so the first divider sits at the first
    real group boundary."""
    cols = set()
    col0 = 0
    prev_lbl = None
    for lbl, s in groups:
        if lbl and lbl != prev_lbl and col0 > 0:
            cols.add(col0)
        col0 += int(s)
        prev_lbl = lbl
    return cols


def build_tgid_main(hdr, rows):
    """Build the main TGID table: drop the lead-time-bucket columns, reorder so RPC
    sits in the Funnel group, sort rows desc by Share, then apply concentration
    (green up to ~80% cumulative) + conditional formatting (CR<80% red, S2C/C2O scale)
    + a derived-S2O high-traffic-low-S2O flag. Returns the full <div> table HTML +
    a classification pill. Degrades to a plain styled table on odd shapes."""
    lead_names = ('%0-2d', '%3-7d', '%7d+', '0-2d', '3-7d', '7d+')
    keep = [i for i, h in enumerate(hdr)
            if h.strip().lower() not in lead_names and not any(
                ln in h.strip().lower() for ln in lead_names)]
    # Reorder: identity cols, Revenue (Rev/Share), then move RPC after them so it
    # joins the funnel group, then the rest in original order.
    rpc_i = _col_idx([hdr[i] for i in keep], "rpc")
    # Build the new column order over `keep` indices.
    new_order = list(keep)
    if rpc_i >= 0:
        # Find the position of RPC and the position right after Share, move RPC there.
        keep_hdr = [hdr[i].strip().lower() for i in keep]
        rpc_pos = keep_hdr.index('rpc') if 'rpc' in keep_hdr else -1
        share_pos = next((j for j, h in enumerate(keep_hdr) if h == 'share'), -1)
        # Target: after the funnel-group-start; simplest is to leave RPC where the
        # group classifier already puts it in Funnel Metrics. Since classifier groups
        # by name (not position), reordering is only needed so the band is contiguous.
        # Move RPC to just before 'sel users'/'%traffic' (funnel block start).
        fstart = next((j for j, h in enumerate(keep_hdr)
                       if 'sel users' in h or 'traffic' in h or h in ('s2c', 'c2o')), -1)
        if rpc_pos >= 0 and fstart >= 0 and rpc_pos < fstart:
            col = new_order.pop(rpc_pos)
            new_order.insert(fstart - 1, col)
    nhdr = [hdr[i] for i in new_order]
    nrows = [[r[i] if i < len(r) else "" for i in new_order] for r in rows]

    # Derive an S2O column = S2C × C2O per row and insert it right after C2O so it
    # lands inside the Funnel Metrics group. S2O is NOT in the source data; this is a
    # presentation-derived approximation (S2C×C2O), pending an exact engine figure
    # (Wave B). Parse the two rate columns, ignoring any trailing delta token. Cells
    # with un-parseable inputs (or a TOTAL row) get an empty S2O cell.
    pre_s2c_i = _col_idx(nhdr, "s2c")
    pre_c2o_i = _col_idx(nhdr, "c2o")

    def _lead_rate(cell):
        # Parse the leading rate from a cell, IGNORING any trailing delta token
        # (e.g. "16.5% -4.8pp" → 16.5). Returns None if no leading number.
        m = re.match(r'\s*[$]?([\d,]+(?:\.\d+)?)', cell.strip().strip('*'))
        return float(m.group(1).replace(',', '')) if m else None

    if pre_s2c_i >= 0 and pre_c2o_i >= 0:
        insert_at = pre_c2o_i + 1
        nhdr.insert(insert_at, "S2O")
        for r in nrows:
            a = _lead_rate(r[pre_s2c_i]) if pre_s2c_i < len(r) else None
            b = _lead_rate(r[pre_c2o_i]) if pre_c2o_i < len(r) else None
            if a is not None and b is not None:
                r.insert(insert_at, f"{a / 100.0 * b:.1f}%")
            else:
                r.insert(insert_at, "")

    share_i = _col_idx(nhdr, "share")
    cr_i = _col_idx(nhdr, "cr")
    s2c_i = _col_idx(nhdr, "s2c")
    c2o_i = _col_idx(nhdr, "c2o")
    s2o_i = next((j for j, h in enumerate(nhdr) if h.strip().lower() == "s2o"), -1)
    traf_i = _col_idx(nhdr, "%traffic", "traffic")
    exp_i = _col_idx(nhdr, "experience")

    # Sort rows desc by Share (TOTAL rows, if any, sink to the bottom).
    def share_val(r):
        if share_i < 0 or share_i >= len(r):
            return -1
        v = numparse(r[share_i])
        return v if v is not None else -1
    is_total = [r[0].strip().strip("*").upper() == "TOTAL" for r in nrows]
    idxd = list(range(len(nrows)))
    idxd.sort(key=lambda k: (is_total[k], -share_val(nrows[k])))
    nrows = [nrows[k] for k in idxd]

    # Concentration: green until cumulative Share >= 80%; classification label.
    row_classes = [''] * len(nrows)
    cum = 0.0
    conc_rows = 0
    top_share = 0.0
    for k, r in enumerate(nrows):
        if r[0].strip().strip("*").upper() == "TOTAL":
            continue
        sv = share_val(r)
        if sv < 0:
            continue
        if k == 0:
            top_share = sv
        if cum < TGID_CONCENTRATION_PCT:
            row_classes[k] = 'ceh-conc'
            conc_rows += 1
        cum += sv
    if top_share > TGID_CONCENTRATION_PCT:
        cls_label = "Concentrated"
        cls_note = f"one TGID is {top_share:.0f}% of revenue"
    elif conc_rows <= 3:
        cls_label = "Normal"
        cls_note = f"top {conc_rows} TGIDs carry ~{TGID_CONCENTRATION_PCT:.0f}% of revenue"
    else:
        cls_label = "Fragmented"
        cls_note = f"~{conc_rows} TGIDs needed to reach {TGID_CONCENTRATION_PCT:.0f}% of revenue"

    # Conditional formatting + derived S2O flag.
    cell_classes = {}
    cell_html = {}

    def _scale_bg(frac):
        # frac in [0,1] → green (high) to red (low) light background.
        frac = max(0.0, min(1.0, frac))
        r = int(253 - frac * (253 - 232))
        g = int(236 + frac * (250 - 236))
        b = int(234 + frac * (240 - 234))
        return f'background:rgb({r},{g},{b});'

    s2c_vals = [_lead_num(r[s2c_i]) for r in nrows] if s2c_i >= 0 else []
    c2o_vals = [_lead_num(r[c2o_i]) for r in nrows] if c2o_i >= 0 else []
    s2o_vals = [_lead_num(r[s2o_i]) for r in nrows] if s2o_i >= 0 else []

    def _scale_range(vals):
        v = [x for x in vals if x is not None]
        return (min(v), max(v)) if v else (0, 1)
    s2c_lo, s2c_hi = _scale_range(s2c_vals)
    c2o_lo, c2o_hi = _scale_range(c2o_vals)
    s2o_lo, s2o_hi = _scale_range(s2o_vals)
    traf_vals = [_lead_num(r[traf_i]) for r in nrows] if traf_i >= 0 else []
    traf_v = [x for x in traf_vals if x is not None]
    traf_med = sorted(traf_v)[len(traf_v) // 2] if traf_v else None

    for k, r in enumerate(nrows):
        if r[0].strip().strip("*").upper() == "TOTAL":
            continue
        # Experience name: truncate with ellipsis but expose the full name on hover.
        if exp_i >= 0 and exp_i < len(r):
            full = r[exp_i].strip().strip("*")
            if full:
                cell_html[(k, exp_i)] = (f'<span class="ceh-exp" title="{_html.escape(full)}">'
                                         f'{_cell(full)}</span>')
        # CR < 80% → red highlight.
        if cr_i >= 0 and cr_i < len(r):
            cv = _lead_num(r[cr_i])
            if cv is not None and cv < 80:
                cell_classes[(k, cr_i)] = 'ceh-cr-low'
        # S2C / C2O colour scale (style override via cell_html wrapping not needed —
        # use inline style on a span). We override via cell_html to add the bg.
        for ci, lo, hi in ((s2c_i, s2c_lo, s2c_hi), (c2o_i, c2o_lo, c2o_hi),
                           (s2o_i, s2o_lo, s2o_hi)):
            if ci >= 0 and ci < len(r):
                vv = _lead_num(r[ci])
                if vv is not None and hi > lo:
                    frac = (vv - lo) / (hi - lo)
                    cell_html[(k, ci)] = (f'<span style="display:block;{_scale_bg(frac)}'
                                          f'margin:-6px -10px;padding:6px 10px;">'
                                          f'{_cell_split(r[ci])}</span>')
        # Derived S2O = S2C × C2O (presentation approximation; exact engine value is a
        # later wave). Flag high-traffic + low-S2O TGIDs.
        if s2c_i >= 0 and c2o_i >= 0 and traf_i >= 0 and traf_med is not None:
            s2c = _lead_num(r[s2c_i]); c2o = _lead_num(r[c2o_i]); tf = _lead_num(r[traf_i])
            if None not in (s2c, c2o, tf):
                s2o = s2c / 100.0 * c2o / 100.0 * 100  # %
                # high traffic vs median, low S2O (< TGID_LOW_S2O_PCT) → flag.
                if tf >= traf_med and s2o < TGID_LOW_S2O_PCT and traf_i < len(r):
                    base = cell_html.get((k, traf_i))
                    chip = _flag_chip("warn", f"low S2O ~{s2o:.0f}%")
                    if base:
                        cell_html[(k, traf_i)] = base + chip
                    else:
                        cell_html[(k, traf_i)] = _cell_split(r[traf_i]) + chip

    groups = _tgid_groups(nhdr)
    div_cols = _band_divider_cols(groups, len(nhdr)) if groups else set()
    pill = (f'<div class="ceh-class">CE classification: {cls_label}'
            f' <span style="font-weight:400;color:#5a6478;">— {cls_note}</span></div>')

    table = styled_table(nhdr, nrows, sticky_cols=2, sticky_widths=[64, 210],
                         split_deltas=True, groups=groups, div_cols=div_cols,
                         row_classes=row_classes, cell_classes=cell_classes,
                         cell_html=cell_html)
    note = ('<p style="font-size:11px;color:#888;margin-top:6px;">Green rows = TGIDs '
            'making up ~80% of revenue (sorted by Share). CR&lt;80% flagged red; S2C/C2O/S2O '
            'on a colour scale. S2O is a presentation-derived approximation (S2C×C2O), '
            'pending an exact engine figure (Wave B).</p>')
    return pill + table + note


def _landing_groups(hdr):
    """Grouped header bands for the Top-Landing-Pages sales table: a blank band over
    the 'Landing Page' identity column, 'Revenue' over Rev/Share, 'Order Metrics' over
    the rest (Orders/AOV/CR/TR)."""
    def label_of(h):
        n = h.strip().lower()
        if 'landing' in n or 'page' in n:
            return ''
        if 'rev' in n or n == 'share':
            return 'Revenue'
        return 'Order Metrics'
    bands = []
    for h in hdr:
        lbl = label_of(h)
        if bands and bands[-1][0] == lbl:
            bands[-1][1] += 1
        else:
            bands.append([lbl, 1])
    return bands if any(lbl for lbl, _ in bands) else None


def build_landing_main(hdr, rows):
    """Build the Top-Landing-Pages SALES table — revenue / order metrics straight from
    fct_orders, single 'Landing Page' identity column. 80%-revenue concentration green
    (sorted by Share), CR<80% red, blue group dividers, full-URL hover. No funnel
    columns or colour scale: the per-page funnel lives in its own section (§10), and
    fct_orders.landing_page ↔ mixpanel page_url is not a reliable per-row join."""
    nhdr = list(hdr)
    nrows = [list(r) for r in rows]

    share_i = _col_idx(nhdr, "share")
    cr_i = _col_idx(nhdr, "cr")
    lp_i = _col_idx(nhdr, "landing")

    # Sort rows desc by Share (TOTAL rows, if any, sink to the bottom).
    def share_val(r):
        if share_i < 0 or share_i >= len(r):
            return -1
        v = numparse(r[share_i])
        return v if v is not None else -1
    is_total = [r[0].strip().strip("*").upper() == "TOTAL" for r in nrows]
    idxd = list(range(len(nrows)))
    idxd.sort(key=lambda k: (is_total[k], -share_val(nrows[k])))
    nrows = [nrows[k] for k in idxd]

    # Concentration: green until cumulative Share >= 80%; classification label.
    row_classes = [''] * len(nrows)
    cum = 0.0
    conc_rows = 0
    top_share = 0.0
    for k, r in enumerate(nrows):
        if r[0].strip().strip("*").upper() == "TOTAL":
            continue
        sv = share_val(r)
        if sv < 0:
            continue
        if k == 0:
            top_share = sv
        if cum < TGID_CONCENTRATION_PCT:
            row_classes[k] = 'ceh-conc'
            conc_rows += 1
        cum += sv
    if top_share > TGID_CONCENTRATION_PCT:
        cls_label = "Concentrated"
        cls_note = f"one landing page is {top_share:.0f}% of revenue"
    elif conc_rows <= 3:
        cls_label = "Normal"
        cls_note = f"top {conc_rows} landing pages carry ~{TGID_CONCENTRATION_PCT:.0f}% of revenue"
    else:
        cls_label = "Fragmented"
        cls_note = f"~{conc_rows} landing pages needed to reach {TGID_CONCENTRATION_PCT:.0f}% of revenue"

    # Conditional formatting: CR<80% red + full-URL hover on the identity column.
    cell_classes = {}
    cell_html = {}
    for k, r in enumerate(nrows):
        if r[0].strip().strip("*").upper() == "TOTAL":
            continue
        if lp_i >= 0 and lp_i < len(r):
            full = r[lp_i].strip().strip("*")
            if full:
                cell_html[(k, lp_i)] = (f'<span class="ceh-exp" title="{_html.escape(full)}">'
                                        f'{_cell(full)}</span>')
        if cr_i >= 0 and cr_i < len(r):
            cv = _lead_num(r[cr_i])
            if cv is not None and cv < 80:
                cell_classes[(k, cr_i)] = 'ceh-cr-low'

    groups = _landing_groups(nhdr)
    div_cols = _band_divider_cols(groups, len(nhdr)) if groups else set()
    pill = (f'<div class="ceh-class">LP classification: {cls_label}'
            f' <span style="font-weight:400;color:#5a6478;">— {cls_note}</span></div>')

    table = styled_table(nhdr, nrows, sticky_cols=1, sticky_widths=[320],
                         split_deltas=True, groups=groups, div_cols=div_cols,
                         row_classes=row_classes, cell_classes=cell_classes,
                         cell_html=cell_html)
    note = ('<p style="font-size:11px;color:#888;margin-top:6px;">Green rows = landing '
            'pages making up ~80% of revenue (sorted by Share). CR&lt;80% flagged red. '
            'Per-page funnel metrics are in the Funnel section (§10), not joined here.</p>')
    return pill + table + note


def build_tgid_leadtime(hdr, rows):
    """Separate 'TGID × Lead-time mix' table: identity cols + the %0-2D/%3-7D/%7D+
    buckets only. '' if no lead-time columns present."""
    lead_idx = [i for i, h in enumerate(hdr)
                if any(ln in h.strip().lower() for ln in ('0-2d', '3-7d', '7d+'))]
    if not lead_idx:
        return ""
    # Keep TGID + Experience identity columns up front.
    id_idx = [i for i, h in enumerate(hdr)
              if 'tgid' in h.strip().lower() or 'experience' in h.strip().lower()]
    cols = id_idx + lead_idx
    nhdr = [hdr[i] for i in cols]
    nrows = [[r[i] if i < len(r) else "" for i in cols] for r in rows]
    return styled_table(nhdr, nrows, sticky_cols=min(2, len(id_idx)),
                        sticky_widths=[64, 210], split_deltas=True)


def build_funnel_cards(hdr, rows, period_label="MoM"):
    """4 KPI cards from the §4 funnel table: LP2S · S2C · C2O · LP Users, period Δ
    (current vs prior columns). `period_label` is the window-agnostic delta label
    ("MoM" for a calendar month, else "vs prior"). '' if expected stages aren't found."""
    # Locate the current/prior window columns by header rather than fixed position:
    # they're the first two value columns (skip the Stage label col 0 and any Δ / LY /
    # YoY columns). Falls back to positions 1, 2 if the header shape is unexpected.
    val_cols = [i for i, h in enumerate(hdr)
                if i > 0 and not re.search(r'^\s*[Δ∆]|\bly\b|yoy|vs prior|prior',
                                           h.strip().lower())]
    cur_i, pri_i = (val_cols + [1, 2])[:2] if len(val_cols) >= 2 else (1, 2)
    by = {}
    for r in rows:
        if not r:
            continue
        by[r[0].strip().strip("*").lower()] = r
    if not by:
        return ""

    def _card_pct(name, label):
        r = by.get(name)
        if not r or pri_i >= len(r):
            return ""
        cv, pv = numparse(r[cur_i]), numparse(r[pri_i])
        if cv is None:
            return ""
        if pv is not None:
            dtxt, dcls = pp_delta(cv, pv)
            dtxt = f"Δ {dtxt} {period_label}"
        else:
            dtxt, dcls = "", "delta-flat"
        return card(label, f"{cv:.1f}%", dtxt, dcls, f"{pv:.1f}%" if pv is not None else None)

    def _card_users(name, label):
        r = by.get(name)
        if not r or pri_i >= len(r):
            return ""
        cv, pv = numparse(r[cur_i]), numparse(r[pri_i])
        if cv is None:
            return ""
        dtxt, dcls = (pct_delta(cv, pv) if pv else ("", "delta-flat"))
        dtxt = f"Δ {dtxt} {period_label}" if dtxt else ""

        def _fmt(v):
            return f"{v/1000:.0f}K" if v >= 1000 else f"{v:.0f}"
        return card(label, _fmt(cv), dtxt, dcls, _fmt(pv) if pv else None)

    cards = "".join([
        _card_pct("lp2s", "LP2S"),
        _card_pct("s2c", "S2C"),
        _card_pct("c2o", "C2O"),
        _card_users("lp users", "LP Users"),
    ])
    if not cards.strip():
        return ""
    return f'<div class="metric-cards" style="grid-template-columns:repeat(4,1fr);">{cards}</div>'


def _load_insights(run_dir: Path) -> dict:
    """Load the LLM-authored per-section callouts written by the CE-Health-insights
    sub-agent (see references/ce_health_insights_guide.md). Shape:
    { "<section_id>": {"insight": "<HTML>", "sentiment": "pos|neg|flat"}, ... }.
    Absent / invalid / wrong-shape → {} so the renderer falls back to the
    deterministic summaries (§3/§9/§7) and shows no callout on the gap sections.
    Never raises — a failed sub-agent must never blank or break the tab."""
    f = run_dir / "ce_health_insights.json"
    try:
        if not f.exists():
            return {}
        obj = json.loads(f.read_text())
        return obj if isinstance(obj, dict) else {}
    except Exception:  # noqa: BLE001 — graceful: bad JSON → no insights
        return {}


def build_fragment(run_dir: Path) -> str:
    d = json.loads((run_dir / "ce_health_report.json").read_text())
    md = (run_dir / "ce_health_report.md").read_text()
    V, W = d["vitals"], d["windows"]
    cur, pri = V["current"], V["prior"]

    # LLM-authored per-section callouts (grounded in the facts pack, enriched from CE
    # Context with ↗ tie-ins). section_insight(bid) returns the HTML string for a
    # section id or None; each section's block(...) prefers it over the deterministic
    # summary. Absent/partial → deterministic fallback (§3/§9/§7) / no callout.
    _insights = _load_insights(run_dir)

    def section_insight(bid):
        rec = _insights.get(bid)
        if isinstance(rec, dict):
            ins = rec.get("insight")
            return ins if (isinstance(ins, str) and ins.strip()) else None
        if isinstance(rec, str) and rec.strip():
            return rec
        return None

    # Window-agnostic delta label: a calendar-month run is MoM; any custom window
    # gets the neutral "vs prior" (the literal "MoM" is wrong for custom ranges).
    # Used on the vitals cards, the funnel cards, and the vitals note. Date-driven
    # bits (columns / Shapley / 4-window table) already carry their own dates.
    period_label = "MoM" if d.get("range") == "month" else "vs prior"

    # §2 — vitals metric cards (TM = post, LM = pre). Pill = arrow + absolute change
    # + · + relative % (NOT "Δ"; Δ stays in table headers). Revenue card uses CE
    # Health's normalised revenue (matches the §2 table); §7 decomposes booking.
    # Money/count cards: abs = post − pre (money/comma-int), rel = pct_delta colour +
    # rel_pct. Rate cards: abs = pp change, rel = pp / pre. Colour class drives the
    # arrow (pos ↑ / neg ↓ / flat none) so direction + colour are unambiguous.
    rev_d = pct_delta(cur["revenue"], pri["revenue"]); roi_d = pp_delta(cur["roi_1"], pri["roi_1"])
    tr_d = pp_delta(cur["tr"], pri["tr"]); cr_d = pp_delta(cur["cr"], pri["cr"])
    aov_d = pct_delta(cur["aov"], pri["aov"]); ord_d = pct_delta(cur["orders"], pri["orders"])
    rev_pill = vitals_pill(_signed_money(cur["revenue"] - pri["revenue"]), rel_pct(cur["revenue"], pri["revenue"]), rev_d[1])
    ord_pill = vitals_pill(_signed_int(cur["orders"] - pri["orders"]), rel_pct(cur["orders"], pri["orders"]), ord_d[1])
    aov_pill = vitals_pill(_signed_money(cur["aov"] - pri["aov"]), rel_pct(cur["aov"], pri["aov"]), aov_d[1])
    tr_pill = vitals_pill(_signed_pp(cur["tr"], pri["tr"]), rel_pct_of_pp(cur["tr"], pri["tr"]), tr_d[1])
    cr_pill = vitals_pill(_signed_pp(cur["cr"], pri["cr"]), rel_pct_of_pp(cur["cr"], pri["cr"]), cr_d[1])
    roi_pill = vitals_pill(_signed_pp(cur["roi_1"], pri["roi_1"]), rel_pct_of_pp(cur["roi_1"], pri["roi_1"]), roi_d[1])
    # CVR = funnel CVR (orders/users) from vitals[*].cvr (added by the engine). It's
    # the SAME metric as the Shapley CVR factor. Rendered as a rate card (pp + rel %);
    # cards are added per-window grid width below. None-safe (older sidecars omit it).
    cvr_cur, cvr_pri = cur.get("cvr"), pri.get("cvr")
    has_cvr = cvr_cur is not None and cvr_pri is not None
    cvr_card = ""
    n_cards = 6
    if has_cvr:
        cvr_d = pp_delta(cvr_cur, cvr_pri)
        cvr_pill = vitals_pill(_signed_pp(cvr_cur, cvr_pri), rel_pct_of_pp(cvr_cur, cvr_pri), cvr_d[1])
        cvr_card = card("CVR", f"{cvr_cur:.2f}%", cvr_pill, cvr_d[1], f"{cvr_pri:.2f}%")
        n_cards = 7
    # NOTE: the "Orders / Converter" vitals card was deliberately removed — it is rarely
    # a headline mover, and its Omni (PMax-excluded) basis would contradict the §7 Shapley
    # "Orders / Converter" driver, which is computed all-channels (incl PMax). The metric
    # survives only as a Shapley driver. The engine still emits vitals[*].orders_per_converter
    # (now display-dead).
    # Card order: Revenue · Orders · CVR · AOV · Take Rate · Completion · ROI.
    # CVR sits with the conversion metrics (right after Orders).
    cards = "".join([
        card("Revenue", money(cur["revenue"]), rev_pill, rev_d[1], money(pri["revenue"])),
        card("Orders", f"{cur['orders']:,}", ord_pill, ord_d[1], f"{pri['orders']:,}"),
        cvr_card,
        card("AOV", f"${cur['aov']:.0f}", aov_pill, aov_d[1], f"${pri['aov']:.0f}"),
        card("Take Rate", f"{cur['tr']:.1f}%", tr_pill, tr_d[1], f"{pri['tr']:.1f}%"),
        card("Completion", f"{cur['cr']:.1f}%", cr_pill, cr_d[1], f"{pri['cr']:.1f}%",
             post_class=("ceh-cr-low-val" if (cur.get('cr') is not None and cur['cr'] < 80) else "")),
        card("ROI(1)", f"{cur['roi_1']:.0f}%", roi_pill, roi_d[1], f"{pri['roi_1']:.0f}%"),
    ])
    rev_norm_pct = pct_delta(cur["revenue"], pri["revenue"])[0]
    book_cur, book_pri = cur.get("revenue_actual"), pri.get("revenue_actual")
    book_pct = pct_delta(book_cur, book_pri)[0] if (book_cur and book_pri) else ""
    vit_note = (
        '<p style="font-size:12px;color:#777;margin-top:10px;">Note: the '
        f'<strong>Revenue</strong> row/card is <strong>Predicted Revenue</strong> '
        f'({money(cur["revenue"])}, {rev_norm_pct} {period_label}). The Driver Diagnosis (§7) '
        f'decomposes <strong>Actual Revenue</strong>'
        + (f' ({money(book_cur)}, {book_pct})' if book_cur else '')
        + '.</p>'
    )

    # §1 Metadata → header pills (rendered by compose.build_header). No block here.

    # §7 Shapley decomposition is computed ONCE here (before §2) so the primary driver
    # for the vitals annotation comes from the corrected 5-factor decomposition, not
    # the largest vitals Δ. The same `raw` is reused by build_shapley_block below —
    # we never double-query. On any Query-1 failure, `shap_raw` stays None and the
    # vitals render with NO primary-driver note (and §7 falls back to verbatim).
    ce_id = d.get("ce_id") or d.get("metadata", {}).get("combined_entity_id")
    shap_raw = None
    shap_contrib = None
    try:
        shap_raw = query_raw(str(ce_id), W)
        shap_contrib = _decompose(_facs(shap_raw["pre"]), _facs(shap_raw["post"]))
    except Exception as e:  # noqa: BLE001 — any failure → no driver note + verbatim §7
        print(f"WARN: Query 1 failed ({e}); no primary-driver note, §7 verbatim.", file=sys.stderr)

    # §2 — cards + full 4-window table. The primary driver is the Shapley factor with
    # the largest |contribution|; if it maps to a vitals row, bold/mark that row.
    # The cards come from the JSON sidecar (always present); the full 4-window table
    # comes from the md §2. If that md section is missing/empty (unexpected), degrade
    # to cards-only rather than crash — and the rest of the tab still renders.
    _vit_tables = tables_in(section(md, "CE Vitals"))
    if _vit_tables:
        vh, vr = _vit_tables[0]
        v_rowcls = [''] * len(vr)
    else:
        print("WARN: CE Vitals 4-window table missing — rendering cards only.", file=sys.stderr)
        vh, vr, v_rowcls = None, None, []
    v_cellhtml = {}
    v_cellcls = {}
    # Completion-rate < 80% → red across the vitals 4-window table (same rule as cards/TGID).
    if vr is not None:
        for _k, _row in enumerate(vr):
            _lbl0 = _row[0].strip().strip('*').lower() if _row else ''
            # The vitals 4-window row for completion rate is labelled "CR" (the card
            # is "Completion"); match either. Value cols are clean, delta cols (Δ …)
            # parse to None and are skipped — only level cells < 80 go red.
            if _row and (_lbl0 == 'cr' or 'completion' in _lbl0):
                for _i in range(1, len(_row)):
                    _v = _lead_num(_row[_i])
                    if _v is not None and _v < 80:
                        v_cellcls[(_k, _i)] = 'ceh-cr-low'
    driver_note = ""
    if shap_contrib:
        td = shapley_top_driver(shap_contrib)
        if td:
            fac, amt = td
            sign = "+" if amt >= 0 else "−"
            driver_note = (
                '<p style="font-size:12.5px;color:#3a4a6a;background:#f4f6fb;'
                'border-left:3px solid #6c8ebf;border-radius:4px;padding:8px 12px;'
                'margin:8px 0 0;"><strong>Primary driver (Shapley):</strong> '
                f'{_html.escape(_FLBL[fac])} ({sign}{money(abs(amt))})</p>')
            if vr is not None:  # only mark a row if we have the 4-window table
                pm_k = shapley_top_vitals_row(vh, vr, fac)
                if pm_k is not None and pm_k < len(vr):
                    v_rowcls[pm_k] = 'highlight-row'
                    nm = vr[pm_k][0].strip().strip("*")
                    v_cellhtml[(pm_k, 0)] = (f'<strong>{_html.escape(nm)}</strong>'
                                             '<span class="ceh-prime">primary driver</span>')
    _vit_table_html = (_subhead("Full 4-window comparison")
                       + styled_table(vh, vr, split_deltas=True, row_classes=v_rowcls,
                                      cell_classes=v_cellcls, cell_html=v_cellhtml)
                       ) if vr is not None else ""
    s2 = block("1. CE Vitals", "cehealth-vitals",
               f'<div class="metric-cards" style="grid-template-columns:repeat({n_cards},1fr);">{cards}</div>'
               + _vit_table_html
               + driver_note
               + vit_note,
               summary=section_insight("cehealth-vitals"))

    # §3 Channel Breakdown — Revenue + Share moved to the LEFT (current state first),
    # rule-based benchmark flags on Share, deterministic 2–3 line collapsed summary.
    ch_h, ch_r = tables_in(section(md, "Channel Breakdown"))[0]
    sh_i = _col_idx(ch_h, "share")
    rev_i = _col_idx(ch_h, "rev")
    if sh_i >= 0 and rev_i >= 0:
        # New order: name (0), Rev, Share, then everything else in original order.
        lead = [0, rev_i, sh_i]
        rest = [i for i in range(len(ch_h)) if i not in lead]
        order = lead + rest
        ch_h = [ch_h[i] for i in order]
        ch_r = [[r[i] if i < len(r) else "" for i in order] for r in ch_r]
        new_sh_i = 2  # Share is now column index 2
    else:
        new_sh_i = sh_i
    ch_chips, ch_summary = channel_flags_and_summary(ch_h, ch_r)
    ch_cellhtml = {}
    for k, chip in ch_chips.items():
        if k < len(ch_r) and new_sh_i >= 0 and new_sh_i < len(ch_r[k]):
            ch_cellhtml[(k, new_sh_i)] = _cell_split(ch_r[k][new_sh_i]) + chip
    s3 = block("4. Channel Breakdown", "cehealth-channels",
               styled_table(ch_h, ch_r, split_deltas=True, cell_html=ch_cellhtml),
               summary=section_insight("cehealth-channels") or ch_summary or None)

    # §4 Funnel — 4 KPI cards (MoM Δ) on top, then the 4-window table as YoY detail,
    # then the §10 Landing Pages table folded in as a funnel lens.
    fn_h, fn_r = tables_in(section(md, "Funnel"))[0]
    fn_cards = build_funnel_cards(fn_h, fn_r, period_label)
    # Flag a materially-off step on the 4-window table: largest negative MoM Δ among
    # the rate stages (LP2S/S2C/C2O) gets a red chip.
    fn_di = _col_idx(fn_h, "vs prior")
    fn_cellhtml = {}
    worst_k, worst_v = None, 0.0
    for k, r in enumerate(fn_r):
        nm = r[0].strip().strip("*").lower()
        if nm in ("lp2s", "s2c", "c2o") and fn_di >= 0 and fn_di < len(r):
            m = re.search(r'[+\-−]?[\d.,]+', r[fn_di].replace('−', '-'))
            if m:
                try:
                    v = float(m.group().replace(',', ''))
                except ValueError:
                    continue
                if v < worst_v:
                    worst_v, worst_k = v, k
    if worst_k is not None and worst_v < -1.0:  # > 1pp drop below prior is materially off
        fn_cellhtml[(worst_k, 0)] = (f'<strong>{_html.escape(fn_r[worst_k][0].strip())}</strong>'
                                     + _flag_chip("bad", f"↓ {abs(worst_v):.1f}pp vs prior"))
    lp_h, lp_r = tables_in(section(md, "Landing Pages"))[0]
    # Truncate the URL column with ellipsis but expose the full URL on hover. Landing
    # URLs are full in the source (unlike experience names, which are truncated at
    # source), so this genuinely helps. URL is the first column ("Page URL").
    lp_url_i = _col_idx(lp_h, "url", "page")
    if lp_url_i < 0:
        lp_url_i = 0
    lp_cellhtml = {}
    for k, r in enumerate(lp_r):
        if lp_url_i < len(r):
            u = r[lp_url_i].strip().strip("*")
            if u and u.upper() != "TOTAL":
                lp_cellhtml[(k, lp_url_i)] = (f'<span class="ceh-lpurl" title="{_html.escape(u)}">'
                                              f'{_cell(u)}</span>')
    # Funnel-by-dimension dropdown: Landing page (existing) + Channel + Language
    # (new engine cuts). Each is a panel; the <select> switches between them.
    fdim_panels = [("landing", "Landing page",
                    styled_table(lp_h, lp_r, split_deltas=True, cell_html=lp_cellhtml))]
    _ch_t = tables_in(section(md, "Funnel by Channel"))
    if _ch_t:
        fdim_panels.append(("channel", "Channel", styled_table(*_ch_t[0], split_deltas=True)))
    _lg_t = tables_in(section(md, "Funnel by Language"))
    if _lg_t:
        fdim_panels.append(("language", "Language", styled_table(*_lg_t[0], split_deltas=True)))
    s4_inner = (fn_cards
                + _subhead("4-window detail (YoY)")
                + styled_table(fn_h, fn_r, split_deltas=True, cell_html=fn_cellhtml)
                + _subhead("Funnel by dimension")
                + build_fdim_dropdown(fdim_panels))
    s4 = block(
        '5. Funnel'
        '<span style="font-size:11px;font-weight:600;color:#6b7280;background:#eef0f2;'
        'border-radius:10px;padding:2px 8px;margin-left:10px;letter-spacing:.04em;'
        'vertical-align:middle;">EXCLUDES PMAX</span>',
        "cehealth-funnel", s4_inner,
        summary=section_insight("cehealth-funnel"))

    # §5 Multi-Year Trajectory — charts replace the two monthly tables (same data),
    # plus a YoY pivot (Predicted Revenue, month × year) rendered beneath the chart.
    l12 = section(md, "Trajectory")
    _l12_tables = tables_in(l12)
    t_health, t_paid = _l12_tables[0], _l12_tables[-1]
    h_hdr = t_health[0]; hr = t_health[1]
    p_hdr = t_paid[0]; pr_ = t_paid[1]

    # Partial-month guard: the monthly query ends at CURRENT_DATE()-1, so when the run
    # happens mid-month the trailing month is incomplete (e.g. a run on the 5th gives
    # ~4 days). Plotted as a full month it reads as a sharp end-of-series drop that's
    # really just truncation. Drop any trailing row whose month == the generated month
    # (generated_at's YYYY-MM) so no phantom dip survives. Applied to BOTH monthly
    # tables since they share this builder. The month label is the first column.
    _gen_month = str(d.get("generated_at", ""))[:7]

    def _drop_partial_trailing(rows):
        if _gen_month and rows and str(rows[-1][0]).strip()[:7] == _gen_month:
            return rows[:-1]
        return rows
    hr = _drop_partial_trailing(hr)
    pr_ = _drop_partial_trailing(pr_)

    # Locate monthly-table columns by header name (robust to column reorders / a market
    # that omits a column). A missing column → that series/hover field is omitted, not
    # crashed. The Month label is the first column.
    def _cell_at(r, idx):
        return r[idx] if 0 <= idx < len(r) else ""

    def _series(rows, idx):
        # Parsed numeric series for an axis; idx<0 (absent column) → all-None series.
        return [numparse(_cell_at(r, idx)) if idx >= 0 else None for r in rows]

    def _custom(rows, idxs):
        # Per-row customdata: raw cell text for each requested column (absent → "").
        return [[_cell_at(r, i) for i in idxs] for r in rows]

    h_month_i = _col_idx(h_hdr, "month")
    h_rev_i = _col_idx(h_hdr, "revenue", "rev")
    h_ord_i = _col_idx(h_hdr, "orders", "order")
    h_roi_i = _col_idx(h_hdr, "roi")
    h_tr_i = _col_idx(h_hdr, "tr", "take rate")
    h_cr_i = _col_idx(h_hdr, "cr", "completion")
    h_aov_i = _col_idx(h_hdr, "aov")
    months = [_cell_at(r, max(h_month_i, 0)) for r in hr]
    rev = _series(hr, h_rev_i); orders = _series(hr, h_ord_i)
    # Per-month metric strings for the enriched hover (Revenue·Orders·ROI·TR·CR·AOV —
    # all already in the monthly table). customdata feeds the hovertemplate.
    h_custom = _custom(hr, [h_rev_i, h_ord_i, h_roi_i, h_tr_i, h_cr_i, h_aov_i])
    rev_hover = ("<b>%{x}</b><br>Revenue %{customdata[0]}<br>Orders %{customdata[1]}"
                 "<br>ROI %{customdata[2]}<br>TR %{customdata[3]}<br>CR %{customdata[4]}"
                 "<br>AOV %{customdata[5]}<extra></extra>")
    p_clicks_i = _col_idx(p_hdr, "clicks")
    p_roi_i = _col_idx(p_hdr, "paid roi", "roi")
    p_cvr_i = _col_idx(p_hdr, "cvr")
    clicks = _series(pr_, p_clicks_i); paidroi = _series(pr_, p_roi_i)
    # CVR-chart source resolution (honesty fix). The monthly CVR YoY chart must never
    # conflate Site CVR (funnel: converters / LP-users, what §2 vitals show) with Paid
    # CVR (ad conv / ad clicks). Prefer a monthly *Site* CVR column if the engine
    # surfaces one (header matches "site_cvr" / "site cvr"); look in the health table
    # first, then the paid table. If none exists yet, fall back to the existing paid
    # CVR column BUT title the chart "Paid CVR (monthly)" so the basis is explicit.
    # (Engine handoff to add a monthly site_cvr series is pending; this auto-prefers it.)
    h_site_cvr_i = _col_idx(h_hdr, "site_cvr", "site cvr")
    p_site_cvr_i = _col_idx(p_hdr, "site_cvr", "site cvr")
    if h_site_cvr_i >= 0:
        cvr_chart_rows, cvr_chart_hdr, cvr_chart_i = hr, h_hdr, h_site_cvr_i
        cvr_chart_title, cvr_chart_label = "Site CVR (monthly)", "Site CVR"
    elif p_site_cvr_i >= 0:
        cvr_chart_rows, cvr_chart_hdr, cvr_chart_i = pr_, p_hdr, p_site_cvr_i
        cvr_chart_title, cvr_chart_label = "Site CVR (monthly)", "Site CVR"
    else:
        cvr_chart_rows, cvr_chart_hdr, cvr_chart_i = pr_, p_hdr, p_cvr_i
        cvr_chart_title, cvr_chart_label = "Paid CVR (monthly)", "Paid CVR"
    # (The old Revenue+Orders dual-axis chart is replaced by the single-metric
    # selector chart `c_metric`, built below once the CVR series is resolved.)
    c_paid = ('<div id="chart-cehealth-l12m-paid" class="chart-container" style="width:100%"></div>'
              f'''<script>Plotly.newPlot('chart-cehealth-l12m-paid',[{{type:'bar',name:'Clicks',x:{json.dumps(months)},y:{json.dumps(clicks)},marker:{{color:'#90a4d4'}}}},{{type:'scatter',mode:'lines+markers',name:'Paid ROI %',x:{json.dumps(months)},y:{json.dumps(paidroi)},line:{{color:'#43A047',width:2}},yaxis:'y2'}}],{{height:300,autosize:true,margin:{{l:62,r:55,t:14,b:55}},plot_bgcolor:'#fff',paper_bgcolor:'#fff',font:{{family:'-apple-system,sans-serif',size:11,color:'#1a1a2e'}},legend:{{orientation:'h',y:-0.25}},yaxis:{{title:'Clicks',gridcolor:'#eef'}},yaxis2:{{title:'Paid ROI %',overlaying:'y',side:'right',showgrid:false,ticksuffix:'%'}}}},{{responsive:true,displayModeBar:false}});</script>''')
    # Year-overlay charts: group monthly YYYY-MM data into one trace per calendar year,
    # x = month-of-year (Jan…Dec) so years align seasonally. Replaces the old YoY pivot table.
    _MN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    _COLORS = ["#6c8ebf", "#43A047", "#c62828", "#8e44ad", "#f39c12", "#16a085"]

    def yoy_chart(cid, title, ytitle, mkeys, vals, tickprefix="", ticksuffix="",
                  cmap=None, hovertemplate=None):
        # mkeys: list of "YYYY-MM"; vals: parallel list of numbers (Nones skipped).
        # cmap: optional {mkey: [customdata...]} for an enriched per-point hover.
        by_year = {}
        cust_by_year = {}
        for mk, v in zip(mkeys, vals):
            if v is None or "-" not in str(mk):
                continue
            y, m = str(mk).split("-")[:2]
            try:
                mi = int(m)
            except ValueError:
                continue
            by_year.setdefault(y, {})[mi] = v
            if cmap is not None:
                cust_by_year.setdefault(y, {})[mi] = cmap.get(str(mk), [])
        if not by_year:
            return ""  # no monthly data — skip gracefully
        traces = []
        for i, y in enumerate(sorted(by_year)):
            pts = by_year[y]
            xs = [_MN[mi - 1] for mi in sorted(pts)]
            ys = [pts[mi] for mi in sorted(pts)]
            tr = {"type": "scatter", "mode": "lines+markers", "name": y,
                  "x": xs, "y": ys, "line": {"shape": "spline", "width": 2,
                  "color": _COLORS[i % len(_COLORS)]}, "marker": {"size": 5}}
            if cmap is not None and hovertemplate:
                cy = cust_by_year.get(y, {})
                tr["customdata"] = [cy.get(mi, []) for mi in sorted(pts)]
                tr["hovertemplate"] = hovertemplate
            traces.append(tr)
        return (f'<div id="{cid}" class="chart-container" style="width:100%"></div>'
                f'''<script>Plotly.newPlot('{cid}',{json.dumps(traces)},{{height:320,autosize:true,'''
                f'''title:{json.dumps(title)},margin:{{l:62,r:30,t:32,b:55}},plot_bgcolor:'#fff',paper_bgcolor:'#fff','''
                f'''font:{{family:'-apple-system,sans-serif',size:11,color:'#1a1a2e'}},legend:{{orientation:'h',y:-0.2}},'''
                f'''xaxis:{{categoryorder:'array',categoryarray:{json.dumps(_MN)}}},'''
                f'''yaxis:{{title:{json.dumps(ytitle)},tickprefix:{json.dumps(tickprefix)},ticksuffix:{json.dumps(ticksuffix)},gridcolor:'#eef'}}}},'''
                f'''{{responsive:true,displayModeBar:false}});</script>''')

    # Enriched YoY hovers built from the same monthly table rows as the linear charts.
    # Revenue YoY: reuse the health-table per-month metrics (Revenue·Orders·ROI·TR·CR·AOV),
    # indexed by header name (same maps as the linear charts above).
    p_month_i = _col_idx(p_hdr, "month")

    def _mkey(r, idx):
        return _cell_at(r, idx) if idx >= 0 else _cell_at(r, 0)
    rev_cmap = {_mkey(r, h_month_i): [_cell_at(r, h_rev_i), _cell_at(r, h_ord_i),
                                      _cell_at(r, h_roi_i), _cell_at(r, h_tr_i),
                                      _cell_at(r, h_cr_i), _cell_at(r, h_aov_i)] for r in hr}
    yoy_rev_hover = ("<b>%{x} %{data.name}</b><br>Revenue %{customdata[0]}<br>Orders %{customdata[1]}"
                     "<br>ROI %{customdata[2]}<br>TR %{customdata[3]}<br>CR %{customdata[4]}"
                     "<br>AOV %{customdata[5]}<extra></extra>")
    yoy_html = yoy_chart("chart-cehealth-yoy-rev", "Revenue YoY", "Revenue",
                         months, rev, tickprefix="$",
                         cmap=rev_cmap, hovertemplate=yoy_rev_hover)
    # CVR chart: plot the resolved CVR source (Site CVR if a monthly site_cvr column
    # exists, else Paid CVR — see resolution above). Title states the basis explicitly
    # so Site vs Paid is never conflated. clicks/paid-ROI context come from the paid
    # table (matched by month key) regardless of which CVR series is plotted.
    cvr_month_i = _col_idx(cvr_chart_hdr, "month")
    cvr_keys = [_mkey(r, cvr_month_i) for r in cvr_chart_rows]
    cvr_vals = _series(cvr_chart_rows, cvr_chart_i)
    # Paid clicks/ROI by month key for the hover context.
    _paid_ctx = {_mkey(r, p_month_i): [_cell_at(r, p_clicks_i), _cell_at(r, p_roi_i)] for r in pr_}
    cvr_cmap = {_mkey(r, cvr_month_i): [_cell_at(r, cvr_chart_i)]
                + _paid_ctx.get(_mkey(r, cvr_month_i), ["", ""]) for r in cvr_chart_rows}
    yoy_cvr_hover = ("<b>%{x} %{data.name}</b><br>" + cvr_chart_label + " %{customdata[0]}"
                     "<br>Clicks %{customdata[1]}<br>Paid ROI %{customdata[2]}<extra></extra>")
    yoy_html += yoy_chart("chart-cehealth-yoy-cvr", cvr_chart_title, cvr_chart_label + " %",
                          cvr_keys, cvr_vals, ticksuffix="%",
                          cmap=cvr_cmap, hovertemplate=yoy_cvr_hover)
    # §2 metric-selector chart — replaces the old Revenue+Orders dual-axis chart.
    # ONE always-visible Plotly line chart + native `updatemenus` buttons that swap the
    # shown metric AND reformat the y-axis. Single-metric only (no multi-axis problem;
    # each metric auto-scales its own axis). All series come from the monthly health
    # table (Revenue/Orders/ROI/CR/TR/AOV) + the resolved CVR series, aligned to `months`.
    _cvr_by_month = {k: v for k, v in zip(cvr_keys, cvr_vals)}
    _cvr_aligned = [_cvr_by_month.get(m) for m in months]
    _sel = [
        ("Revenue", rev, "$", "", "Revenue"),
        ("Orders", orders, "", "", "Orders"),
        ("ROI", _series(hr, h_roi_i), "", "%", "ROI %"),
        ("Completion", _series(hr, h_cr_i), "", "%", "Completion %"),
        ("Take Rate", _series(hr, h_tr_i), "", "%", "Take Rate %"),
        ("AOV", _series(hr, h_aov_i), "$", "", "AOV"),
        (cvr_chart_label, _cvr_aligned, "", "%", cvr_chart_label + " %"),
    ]
    _sel_traces = [{"type": "scatter", "mode": "lines+markers", "name": nm,
                    "x": months, "y": ys, "visible": (i == 0),
                    "line": {"color": _COLORS[i % len(_COLORS)], "width": 2},
                    "marker": {"size": 4}}
                   for i, (nm, ys, _tp, _ts, _tt) in enumerate(_sel)]
    _sel_buttons = [{"method": "update", "label": nm,
                     "args": [{"visible": [j == i for j in range(len(_sel))]},
                              {"yaxis": {"title": tt, "tickprefix": tp, "ticksuffix": ts,
                                         "gridcolor": "#eef"}}]}
                    for i, (nm, _ys, tp, ts, tt) in enumerate(_sel)]
    _sel_layout = {"height": 320, "autosize": True,
                   "margin": {"l": 64, "r": 30, "t": 48, "b": 55},
                   "plot_bgcolor": "#fff", "paper_bgcolor": "#fff",
                   "font": {"family": "-apple-system,sans-serif", "size": 11, "color": "#1a1a2e"},
                   "showlegend": False,
                   "yaxis": {"title": "Revenue", "tickprefix": "$", "gridcolor": "#eef"},
                   "updatemenus": [{"type": "buttons", "direction": "right",
                                    "x": 0, "xanchor": "left", "y": 1.16, "yanchor": "top",
                                    "showactive": True, "active": 0, "bgcolor": "#f6f6fa",
                                    "pad": {"r": 4, "t": 4}, "font": {"size": 11},
                                    "buttons": _sel_buttons}]}
    c_metric = ('<div id="chart-cehealth-l12m-metric" class="chart-container" style="width:100%"></div>'
                f'<script>Plotly.newPlot("chart-cehealth-l12m-metric",{json.dumps(_sel_traces)},'
                f'{json.dumps(_sel_layout)},{{responsive:true,displayModeBar:false}});</script>')

    # "(new)" pill when history is thin (no LY) — engine emits has_ly/history_months.
    new_pill = "" if d.get("has_ly", True) else '<span class="ceh-new">new</span>'
    # Linear ↔ YoY view toggle so the 4 charts aren't stacked. Default = Linear.
    # A Plotly chart in a display:none container has zero width until shown, so the
    # toggle script must resize each .js-plotly-plot in the newly-shown group
    # (mirrors the on-load resize script).
    traj_style = ('<style>.ceh-traj{display:none}.ceh-traj.active{display:block}'
                  '.ceh-traj-toggle{display:inline-flex;gap:4px;margin:0 0 12px;border:1px solid #d6d6e0;'
                  'border-radius:6px;overflow:hidden}.ceh-traj-toggle label{font-size:12px;padding:5px 12px;'
                  'cursor:pointer;color:#555;background:#f6f6fa;user-select:none}'
                  '.ceh-traj-toggle label:has(input:checked){background:#6c8ebf;color:#fff}'
                  '.ceh-traj-toggle input{position:absolute;opacity:0;pointer-events:none}</style>')
    traj_toggle = ('<div class="ceh-traj-toggle">'
                   '<label><input type="radio" name="ceh-traj-view" value="linear" checked>Linear trajectory</label>'
                   '<label><input type="radio" name="ceh-traj-view" value="yoy">YoY comparison</label>'
                   '</div>')
    traj_script = ("<script>(function(){var t=document.getElementById('tab-cehealth');if(!t)return;"
                   "t.addEventListener('change',function(e){var i=e.target;"
                   "if(!i||i.name!=='ceh-traj-view')return;"
                   "t.querySelectorAll('.ceh-traj-linear').forEach(function(g){"
                   "g.classList.toggle('active',i.value==='linear');});"
                   "t.querySelectorAll('.ceh-traj-yoy').forEach(function(g){"
                   "g.classList.toggle('active',i.value==='yoy');});"
                   "var sel=i.value==='yoy'?'.ceh-traj-yoy':'.ceh-traj-linear';"
                   "if(window.Plotly)t.querySelectorAll(sel+' .js-plotly-plot').forEach(function(el){"
                   "try{window.Plotly.Plots.resize(el);}catch(err){}});});})();</script>")
    traj_body = (traj_toggle
                 + '<div class="ceh-traj ceh-traj-linear active">'
                 + _subhead("CE Health (Monthly)") + c_metric
                 + _subhead("Paid Performance (Monthly)") + c_paid + '</div>'
                 + '<div class="ceh-traj ceh-traj-yoy">' + yoy_html + '</div>'
                 + traj_script)
    s5 = block("2. Metric trajectory" + (" " if new_pill else ""), "cehealth-l12m",
               (traj_style + new_pill + traj_body
                + '<p style="font-size:12px;color:#777;margin-top:8px;">Charts visualise CE Health\'s '
                'monthly tables (same data). The full monthly tables remain in the CE Health source.</p>'),
               summary=section_insight("cehealth-l12m"))

    # §6 Top TGIDs — single main table (Order/Funnel groups + blue dividers, RPC in
    # Funnel, 80%-concentration green, classification pill, CR<80% / S2C / C2O
    # conditional formatting, derived-S2O flag), plus a SEPARATE TGID × Lead-time mix
    # table below, plus the §9 CE-level lead-time cohorts (its own collapsible block).
    # The engine emits up to TWO TGID tables: [0] MoM (current vs prior), [1] YoY
    # (current vs LY-same-period; present only when LY data exists). Render the MoM
    # table as the main view; when a YoY table is present, wrap both in a "Compare
    # current vs" toggle (same panel-switch widget as the funnel-by-dimension drop).
    _tg_tbls = tables_in(section(md, "Top TGIDs"))
    tg = _tg_tbls[0]
    try:
        tgid_main = build_tgid_main(tg[0], tg[1])
        tgid_lead = build_tgid_leadtime(tg[0], tg[1])
    except Exception as e:  # noqa: BLE001 — never emit a broken table
        print(f"WARN: TGID enrichment failed ({e}); plain table fallback.", file=sys.stderr)
        tgid_main = styled_table(tg[0], tg[1], sticky_cols=2, sticky_widths=[64, 210],
                                 split_deltas=True, groups=_tgid_groups(tg[0]))
        tgid_lead = ""
    tgid_yoy = None
    if len(_tg_tbls) > 1:
        try:
            tgid_yoy = build_tgid_main(_tg_tbls[1][0], _tg_tbls[1][1])
        except Exception as e:  # noqa: BLE001 — YoY is additive; drop it if it fails
            print(f"WARN: TGID YoY view failed ({e}); MoM only.", file=sys.stderr)
            tgid_yoy = None
    if tgid_yoy:
        s6_inner = build_fdim_dropdown(
            [("mom", "vs Pre period", tgid_main), ("yoy", "vs LY (same period)", tgid_yoy)],
            label="Compare current vs:")
    else:
        s6_inner = tgid_main
    if tgid_lead:
        s6_inner += _subhead("TGID × Lead-time mix") + tgid_lead
    s6 = block("6. Top TGIDs", "cehealth-tgids", s6_inner,
               summary=section_insight("cehealth-tgids"))

    # §6b Top Landing Pages — sales matrix at landing-page grain, mirroring the TGID
    # table but with a single identity column. Graceful: empty string if the source
    # markdown lacks the section (e.g. older runs), so the block silently drops.
    # The engine emits up to TWO landing tables: [0] MoM (current vs prior), [1] YoY
    # (current vs LY-same-period; present only when LY data exists). Mirror the TGID
    # toggle: render MoM as the main view, and when YoY is present wrap both in a
    # "Compare current vs" dropdown (same widget as TGID / funnel-by-dimension).
    _lp_tbls = tables_in(section(md, "Top Landing Pages"))
    if _lp_tbls:
        try:
            lp_main = build_landing_main(_lp_tbls[0][0], _lp_tbls[0][1])
        except Exception as e:  # noqa: BLE001 — never emit a broken table
            print(f"WARN: landing-page enrichment failed ({e}); plain table fallback.", file=sys.stderr)
            lp_main = styled_table(_lp_tbls[0][0], _lp_tbls[0][1], split_deltas=True)
        lp_yoy = None
        if len(_lp_tbls) > 1:
            try:
                lp_yoy = build_landing_main(_lp_tbls[1][0], _lp_tbls[1][1])
            except Exception as e:  # noqa: BLE001 — YoY is additive; drop it if it fails
                print(f"WARN: landing-page YoY view failed ({e}); MoM only.", file=sys.stderr)
                lp_yoy = None
        if lp_yoy:
            lp_inner = build_fdim_dropdown(
                [("mom", "vs Pre period", lp_main), ("yoy", "vs LY (same period)", lp_yoy)],
                label="Compare current vs:")
        else:
            lp_inner = lp_main
        s_landing = block("7. Top Landing Pages", "cehealth-landing-pages", lp_inner,
                          summary=section_insight("cehealth-landing-pages"))
    else:
        s_landing = ""

    # Vendor Breakdown — supply/sales landscape, right after TGID. Two-line
    # value+delta cells (MoM revenue Δ); graceful: empty string if absent.
    _vb = tables_in(section(md, "Vendor Breakdown"))
    s_vendor = (block("8. Vendor Breakdown", "cehealth-vendors",
                      styled_table(*_vb[0], split_deltas=True),
                      summary=section_insight("cehealth-vendors"))
                if _vb else "")

    # §7 Driver Diagnosis (Shapley) — corrected 5-factor waterfall, reusing the
    # `shap_raw` already pulled above (no double-query). On any Query-1 failure
    # (shap_raw is None), fall back to CE Health's §7 table, verbatim.
    _shap_ins = section_insight("cehealth-shapley")
    if shap_raw is not None:
        # When an LLM insight exists it becomes the section-top callout and the
        # deterministic verdict is dropped (drag/lift detail is already in the chart);
        # absent → the deterministic verdict renders as before.
        s7 = build_shapley_block(shap_raw, W, insight=_shap_ins)
        print("§7 Shapley: corrected 5-factor waterfall (Query 1 OK)")
    else:
        print("WARN: Query 1 unavailable; rendering CE Health's §7 table verbatim.", file=sys.stderr)
        sec7 = section(md, "Driver Diagnosis")
        tbls = tables_in(sec7)
        inner = styled_table(*tbls[0], split_deltas=True) if tbls else f'<div class="md-content">{render_markdown_to_html(sec7)}</div>'
        s7 = block("3. Driver Diagnosis (Shapley)", "cehealth-shapley", inner,
                   summary=_shap_ins)

    # Historical Context (CE history + prior-run index + user context) has MOVED to
    # its own "CE Context" tab (render_ce_context.py, which imports the three block
    # builders — ce_history_block / prior_runs_block / user_context_subsection — from
    # this module). CE Health is now a pure data/metrics tab; no §Historical block here.

    # Lead Time Cohorts — all rows + rule-based dominant-band callout (collapsed).
    lt_h, lt_r = tables_in(section(md, "Lead Time Cohorts"))[0]
    lt_summary = leadtime_summary(lt_h, lt_r)
    s9 = block("9. Lead Time Cohorts", "cehealth-leadtime",
               styled_table(lt_h, lt_r, split_deltas=True),
               summary=lt_summary or None)

    # §10 Landing Pages — folded into the Funnel block (§4) as a funnel lens.

    # Customer Countries — ALL rows
    s11 = block("10. Customer Countries", "cehealth-countries",
                styled_table(*tables_in(section(md, "Customer Countries"))[0], split_deltas=True),
                summary=section_insight("cehealth-countries"))

    # "Where are bookings coming from?" — L12M revenue matrix with a Channel /
    # Landing Page dropdown. Each panel is a wide table (first column sticky/frozen,
    # 12 month columns, scrolls horizontally) plus an inline-SVG sparkline of each
    # row's 12-month trend. Graceful: a missing table → a short note; both missing
    # → the whole section is omitted.
    _na = '<p style="color:#8a8a8a;">Monthly revenue not available for this dimension.</p>'

    def _rev_matrix_panel(sec_name):
        tabs = tables_in(section(md, sec_name))
        if not tabs:
            return None
        hdr, rows = tabs[0]
        hdr = hdr + ["Trend"]
        out_rows = []
        cell_html = {}
        for k, r in enumerate(rows):
            vals = [numparse(c) for c in r[1:]]  # skip the dimension-name column
            out_rows.append(r + [""])
            spark = _sparkline(vals)
            cell_html[(k, len(hdr) - 1)] = spark or "—"
        return styled_table(hdr, out_rows, sticky_cols=1, cell_html=cell_html)

    bs_panels = []
    _bs_ch = _rev_matrix_panel("Monthly Revenue by Channel")
    bs_panels.append(("channel", "Channel", _bs_ch if _bs_ch else _na))
    _bs_lp = _rev_matrix_panel("Monthly Revenue by Landing Page")
    bs_panels.append(("landing", "Landing Page", _bs_lp if _bs_lp else _na))
    if _bs_ch is None and _bs_lp is None:
        s_bookings_src = ""
    else:
        s_bookings_src = block(
            "Last 12-month revenue over channel/Landing Pages",
            "cehealth-bookings-source",
            build_fdim_dropdown(bs_panels, label="Break revenue down by:"))

    footer = (f'<footer style="text-align:center;font-size:12px;color:#aaa;padding:18px;">'
              f'CE Health v2.0 | {d.get("generated_at", "")} | {d.get("range", "month")} windows</footer>')
    resize = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "if(window.Plotly)document.querySelectorAll('#tab-cehealth .js-plotly-plot')"
              ".forEach(function(el){try{window.Plotly.Plots.resize(el);}catch(e){}});},200);});</script>")

    # Page order: Vitals → Revenue trajectory → Driver diagnosis (Shapley) → Channels
    # → Funnel (Landing folded in) → TGIDs → Top Landing Pages → Vendors → Lead-time
    # cohorts → Customer countries. (Historical/user/Slack context now lives in the
    # separate CE Context tab — see render_ce_context.py.)
    ordered = [
        ("cehealth-vitals", s2),
        ("cehealth-l12m", s5),
        ("cehealth-shapley", s7),
        ("cehealth-channels", s3),
        ("cehealth-bookings-source", s_bookings_src),
        ("cehealth-funnel", s4),
        ("cehealth-tgids", s6),
        ("cehealth-landing-pages", s_landing),
        ("cehealth-vendors", s_vendor),
        ("cehealth-leadtime", s9),
        ("cehealth-countries", s11),
    ]
    # Apply the default-open set centrally: collapse every block NOT in
    # CEH_DEFAULT_OPEN by injecting the collapsed class + flipping aria-expanded.
    def _maybe_collapse(bid, frag):
        if bid in CEH_DEFAULT_OPEN:
            return frag
        frag = frag.replace(f'<div class="analysis-block" id="{bid}">',
                            f'<div class="analysis-block ceh-collapsed" id="{bid}">', 1)
        frag = frag.replace('class="ceh-toggle" aria-expanded="true"',
                            'class="ceh-toggle" aria-expanded="false"', 1)
        return frag
    body = "".join(_maybe_collapse(bid, frag) for bid, frag in ordered if frag)

    # Widen the CE Health tab beyond the 1050px .container so the wide tables
    # (TGIDs, Channels, Landing) are readable. Centered breakout.
    open_div = '<div style="width:min(1280px,95vw);margin-left:50%;transform:translateX(-50%);">'
    return (CEH_TABLE_STYLE + CEH_COLLAPSE_STYLE + open_div + body
            + footer + '</div>' + CEH_COLLAPSE_SCRIPT + CEH_FDIM_STYLE + CEH_FDIM_SCRIPT + resize)


# ─────────────────────────────────────────────────────────────────────────────
# Facts pack (--emit-facts) — the compact, grounded data backbone the CE-Health
# insights sub-agent phrases into per-section one-liners. NO bq, NO raw table
# dumps: every number here is read from ce_health_report.{md,json} and the existing
# deterministic generators, so the facts pack is fast + reproducible. The sub-agent
# (see references/ce_health_insights_guide.md) may cite ONLY these numbers in a
# section's data line, then enrich from the CE Context artifacts with a ↗ tie-in.
# ─────────────────────────────────────────────────────────────────────────────

def _round(v, n=1):
    """Round a float for the facts pack; None passes through. Keeps the JSON small
    and the numbers human-cite-able (no 12-dp noise)."""
    try:
        return round(float(v), n)
    except (TypeError, ValueError):
        return None


def _funnel_facts(md):
    """Worst rate-stage MoM drop (LP2S/S2C/C2O) + whether the others held — mirrors
    the §4 worst-step flag in build_fragment. Returns {} on odd shapes."""
    tbls = tables_in(section(md, "Funnel"))
    if not tbls:
        return {}
    hdr, rows = tbls[0]
    di = _col_idx(hdr, "vs prior")
    if di < 0:
        di = _col_idx(hdr, "mom")
    cur_i = 1  # first value column = current window
    stage_d = {}
    for r in rows:
        nm = r[0].strip().strip("*").lower()
        if nm in ("lp2s", "s2c", "c2o") and 0 <= di < len(r):
            m = re.search(r'[+\-−]?[\d.,]+', r[di].replace('−', '-'))
            if m:
                try:
                    stage_d[nm.upper()] = float(m.group().replace(',', ''))
                except ValueError:
                    pass
    if not stage_d:
        return {}
    worst = min(stage_d, key=stage_d.get)
    others_ok = all(v > -1.0 for k, v in stage_d.items() if k != worst)
    cur_vals = {}
    for r in rows:
        nm = r[0].strip().strip("*").lower()
        if nm in ("lp2s", "s2c", "c2o") and cur_i < len(r):
            cur_vals[nm.upper()] = numparse(r[cur_i])
    return {
        "worst_step": worst,
        "delta_pp": _round(stage_d[worst], 1),
        "stage_deltas_pp": {k: _round(v, 1) for k, v in stage_d.items()},
        "current_pct": {k: _round(v, 1) for k, v in cur_vals.items()},
        "others_ok": others_ok,
    }


def _share_table_facts(md, name, id_kw, top_n=3):
    """Generic 'top-N by Share' concentration facts for the TGID / Landing / Vendor /
    Country tables: top item name + share %, topN cumulative share %, item count.
    `id_kw` matches the identity column. Returns {} on odd shapes."""
    tbls = tables_in(section(md, name))
    if not tbls:
        return {}
    hdr, rows = tbls[0]
    share_i = _col_idx(hdr, "share")
    name_i = _col_idx(hdr, *id_kw)
    if name_i < 0:
        name_i = 0
    if share_i < 0:
        return {}
    items = []
    for r in rows:
        if share_i >= len(r):
            continue
        nm = r[name_i].strip().strip("*") if name_i < len(r) else ""
        if nm.upper() == "TOTAL" or not nm:
            continue
        v = numparse(r[share_i])
        if v is not None:
            items.append((nm, v))
    if not items:
        return {}
    items.sort(key=lambda x: -x[1])
    topn = items[:top_n]
    return {
        "item_count": len(items),
        "top_item": topn[0][0][:60],
        "top_share_pct": _round(topn[0][1], 1),
        f"top{top_n}_share_pct": _round(sum(v for _, v in topn), 1),
        "top_items": [{"name": n[:60], "share_pct": _round(s, 1)} for n, s in topn],
    }


def _tgid_facts(md):
    """TGID concentration facts, reusing build_tgid_main's classification + the share
    backbone. Adds the flagship (top-share) TGID's notable MoM moves (C2O/CR if the
    columns carry deltas)."""
    base = _share_table_facts(md, "Top TGIDs", ("experience", "tgid"), top_n=3)
    if not base:
        return {}
    tbls = tables_in(section(md, "Top TGIDs"))
    hdr, rows = tbls[0]
    share_i = _col_idx(hdr, "share")
    # Flagship = highest-share row; pull any trailing-delta moves on its rate columns.
    flagship = None
    if share_i >= 0:
        best = None
        for r in rows:
            if r and r[0].strip().strip("*").upper() == "TOTAL":
                continue
            v = numparse(r[share_i]) if share_i < len(r) else None
            if v is not None and (best is None or v > best[0]):
                best = (v, r)
        if best:
            r = best[1]
            moves = {}
            for col in ("c2o", "s2c", "cr", "rpc"):
                ci = _col_idx(hdr, col)
                if 0 <= ci < len(r):
                    m = _TRAIL_DELTA.match(r[ci].strip())
                    if m:
                        moves[col.upper()] = m.group("delta")
            flagship = {"moves": moves} if moves else None
    # Classify like build_tgid_main: count rows until cumulative Share >= ~80%
    # (Concentrated if one TGID alone clears it, Normal if <=3 rows, else Fragmented).
    top_share = base.get("top_share_pct") or 0
    cum = 0.0
    conc_rows = 0
    for it in base.get("top_items", []):
        if cum < TGID_CONCENTRATION_PCT:
            conc_rows += 1
        cum += it.get("share_pct") or 0
    # top_items is capped at top_n; if 80% isn't reached within it, treat as fragmented.
    reached_80 = (sum((it.get("share_pct") or 0) for it in base.get("top_items", []))
                  >= TGID_CONCENTRATION_PCT)
    if top_share > TGID_CONCENTRATION_PCT:
        cls = "Concentrated"
    elif reached_80 and conc_rows <= 3:
        cls = "Normal"
    else:
        cls = "Fragmented"
    base["classification"] = cls
    if flagship:
        base["flagship_moves"] = flagship["moves"]
    return base


def _vitals_facts(d):
    """Headline vitals deltas from the JSON sidecar (no bq). Each metric carries its
    current value, prior value, and signed % / pp delta — the exact figures the §2
    cards show. The Shapley primary driver lives in the `shapley` facts (needs bq),
    so it is NOT duplicated here."""
    V = d.get("vitals", {})
    cur, pri = V.get("current", {}), V.get("prior", {})

    def _pct(k):
        return pct_delta(cur.get(k), pri.get(k))[0] if cur.get(k) is not None and pri.get(k) else None

    def _pp(k):
        if cur.get(k) is None or pri.get(k) is None:
            return None
        return _round(cur[k] - pri[k], 2)

    out = {
        "revenue": cur.get("revenue"), "revenue_delta_pct": _pct("revenue"),
        "revenue_actual": cur.get("revenue_actual"),
        "orders": cur.get("orders"), "orders_delta_pct": _pct("orders"),
        "aov": _round(cur.get("aov"), 0), "aov_delta_pct": _pct("aov"),
        "cr_pct": _round(cur.get("cr"), 1), "cr_delta_pp": _pp("cr"),
        "tr_pct": _round(cur.get("tr"), 1), "tr_delta_pp": _pp("tr"),
        "roi_1_pct": _round(cur.get("roi_1"), 0), "roi_1_delta_pp": _pp("roi_1"),
    }
    if cur.get("cvr") is not None:
        out["cvr_pct"] = _round(cur.get("cvr"), 2)
        out["cvr_delta_pp"] = _pp("cvr")
    return {k: v for k, v in out.items() if v is not None}


def _shapley_facts(md):
    """Top drag + top lift + net Δ from CE Health's own §7 Driver Diagnosis table
    (md, no bq — the renderer's corrected 5-factor waterfall needs Query 1 and is
    NOT recomputed here). Embeds the table's own factor list as `det_summary`."""
    tbls = tables_in(section(md, "Driver Diagnosis"))
    if not tbls:
        return {}
    hdr, rows = tbls[0]
    fac_i = 0
    imp_i = _col_idx(hdr, "impact", "$")
    if imp_i < 0:
        imp_i = 1
    facs = []
    for r in rows:
        if imp_i >= len(r):
            continue
        nm = r[fac_i].strip().strip("*")
        v = numparse(r[imp_i])
        if nm and v is not None:
            facs.append((nm, v))
    if not facs:
        return {}
    drags = sorted([f for f in facs if f[1] < 0], key=lambda x: x[1])
    lifts = sorted([f for f in facs if f[1] > 0], key=lambda x: -x[1])
    return {
        "top_drag": ({"factor": drags[0][0], "usd": _round(drags[0][1], 0)} if drags else None),
        "top_lift": ({"factor": lifts[0][0], "usd": _round(lifts[0][1], 0)} if lifts else None),
        "factors": [{"factor": n, "usd": _round(v, 0)} for n, v in facs],
        "det_summary": ("CE Health §7 names "
                        + (f"{drags[0][0]} as the primary drag" if drags else "no drag")
                        + (f", offset by {lifts[0][0]}" if lifts else "")
                        + " (this is CE Health's own 5-factor table; the rendered tab "
                          "uses a corrected 5-factor waterfall)."),
    }


def _channels_facts(md):
    """Primary channel + its share + the deterministic flag summary, reusing
    channel_flags_and_summary (the same function that feeds the §4 callout)."""
    tbls = tables_in(section(md, "Channel Breakdown"))
    if not tbls:
        return {}
    hdr, rows = tbls[0]
    chips, summary = channel_flags_and_summary(hdr, rows)
    share_i = _col_idx(hdr, "share")
    name_i = _col_idx(hdr, "channel")
    if name_i < 0:
        name_i = 0
    primary, primary_share = None, None
    if share_i >= 0:
        best = None
        for r in rows:
            nm = r[name_i].strip().strip("*") if name_i < len(r) else ""
            if nm.upper() == "TOTAL" or not nm:
                continue
            v = numparse(r[share_i]) if share_i < len(r) else None
            if v is not None and (best is None or v > best[1]):
                best = (nm, v)
        if best:
            primary, primary_share = best
    return {
        "primary_channel": primary,
        "share_pct": _round(primary_share, 1),
        "flag_count": len(chips),
        "det_summary": summary or None,
    }


def _leadtime_facts(md):
    """Dominant lead-time band + its share + skew flag, reusing leadtime_summary for
    the deterministic callout text."""
    tbls = tables_in(section(md, "Lead Time Cohorts"))
    if not tbls:
        return {}
    hdr, rows = tbls[0]
    summary = leadtime_summary(hdr, rows)
    band_i = _col_idx(hdr, "band")
    if band_i < 0:
        band_i = 0
    share_i = _col_idx(hdr, "share")
    bands = []
    if share_i >= 0:
        for r in rows:
            if share_i >= len(r):
                continue
            nm = r[band_i].strip().strip("*") if band_i < len(r) else ""
            if nm.upper() == "TOTAL" or not nm:
                continue
            v = numparse(r[share_i])
            if v is not None:
                bands.append((nm, v))
    dom = max(bands, key=lambda x: x[1]) if bands else (None, None)
    return {
        "dominant_band": dom[0],
        "share_pct": _round(dom[1], 1),
        "skew": (None if not dom[0] else ("near-term" if str(dom[0]).startswith("0-2") else "long-lead")),
        "det_summary": summary or None,
    }


def _l12m_facts(d, md):
    """Trajectory facts: history depth + LY availability, plus a compact revenue-trend
    story parsed from the §5 'CE Health (Monthly)' table (direction, latest vs peak) so
    the insight agent can phrase the trajectory, paired with the §2 YoY in `vitals`."""
    out = {"has_ly": bool(d.get("has_ly", False))}
    if d.get("history_months") is not None:
        out["history_months"] = d.get("history_months")

    def _rev(s):
        s = s.strip().replace("$", "").replace(",", "")
        mult = 1.0
        if s[-1:] == "K":
            mult, s = 1e3, s[:-1]
        elif s[-1:] == "M":
            mult, s = 1e6, s[:-1]
        try:
            return float(s) * mult
        except ValueError:
            return None

    try:
        tbls = tables_in(section(md, "Multi-Year Trajectory"))
        _hdr, rows = tbls[0]  # CE Health (Monthly): Month | Revenue | ...
        series = [(r[0], _rev(r[1])) for r in rows if len(r) > 1 and _rev(r[1]) is not None]
        if len(series) >= 3:
            vals = [v for _, v in series]
            latest_m, latest_v = series[-1]
            peak_m, peak_v = max(series, key=lambda x: x[1])
            # The final monthly bucket is the in-progress (partial) month when it
            # coincides with the run's post-window cutoff — don't read it as a decline.
            _cur = (d.get("windows") or {}).get("current") or []
            post_end = _cur[1] if len(_cur) >= 2 else None
            partial = bool(post_end and latest_m == str(post_end)[:7])
            complete_m, complete_v = (series[-2] if partial and len(series) >= 2 else series[-1])
            first3, last3 = sum(vals[:3]) / 3, sum(vals[-3:]) / 3
            trend = ("rising" if last3 > first3 * 1.1
                     else "falling" if last3 < first3 * 0.9 else "flat/volatile")
            out["months_count"] = len(series)
            out["latest"] = {"month": latest_m, "revenue": round(latest_v), "partial": partial}
            out["last_complete"] = {"month": complete_m, "revenue": round(complete_v)}
            out["peak"] = {"month": peak_m, "revenue": round(peak_v)}
            out["last_complete_vs_peak_pct"] = round((complete_v / peak_v - 1) * 100) if peak_v else None
            out["trend"] = trend
    except Exception as e:  # noqa: BLE001 — never sink the pack on a trajectory parse
        print(f"WARN: l12m trajectory facts failed ({e}).", file=sys.stderr)
    return out


def compute_facts(run_dir: Path) -> dict:
    """Compact, grounded facts pack keyed by CE Health section id. Read from
    ce_health_report.{md,json} + the deterministic generators only — no bq, no raw
    table dumps. Each section degrades to {} (never raises) so a thin/odd source
    still yields a usable pack. Consumed by the CE-Health-insights sub-agent."""
    d = json.loads((run_dir / "ce_health_report.json").read_text())
    md = (run_dir / "ce_health_report.md").read_text()

    def _safe(fn, *a):
        try:
            return fn(*a) or {}
        except Exception as e:  # noqa: BLE001 — one bad section never sinks the pack
            print(f"WARN: facts for a section failed ({e}).", file=sys.stderr)
            return {}

    facts = {
        "meta": {
            "ce_id": d.get("ce_id"),
            "ce_name": d.get("ce_name"),
            "range": d.get("range"),
            "windows": d.get("windows"),
        },
        "vitals": _safe(_vitals_facts, d),
        "l12m": _safe(_l12m_facts, d, md),
        "shapley": _safe(_shapley_facts, md),
        "channels": _safe(_channels_facts, md),
        "funnel": _safe(_funnel_facts, md),
        "tgids": _safe(_tgid_facts, md),
        "landing-pages": _safe(_share_table_facts, md, "Top Landing Pages", ("landing", "page"), 3),
        "vendors": _safe(_share_table_facts, md, "Vendor Breakdown", ("vendor",), 3),
        "leadtime": _safe(_leadtime_facts, md),
        "countries": _safe(_share_table_facts, md, "Customer Countries", ("country",), 3),
    }
    return facts


def _write_standalone(run_dir: Path, frag: str):
    """Wrap the body fragment into a full openable `report.html` (standalone runs).
    Reuses the shared `standalone_report.wrap_fragment`; graceful if it's unreachable."""
    try:
        from standalone_report import wrap_fragment, build_header_meta, build_rich_header
    except Exception as e:  # noqa: BLE001
        print(f"standalone wrap unavailable ({e}) — fragment written, no report.html")
        return
    try:
        d = json.loads((run_dir / "ce_health_report.json").read_text())
    except Exception:  # noqa: BLE001
        d = {}
    md = d.get("metadata", {}) or {}
    ce_id = d.get("ce_id") or md.get("combined_entity_id")
    ce_name = d.get("ce_name") or md.get("combined_entity_name") or ""
    # Full composite-style header: identity + pre/post + Omni pill + the 5 CE
    # metadata chips (category/subcategory/evolution/management/status), from the sidecar.
    meta = build_header_meta(md, ce_id=ce_id, ce_name=ce_name, windows=d.get("windows"))
    title = f"CE Health — {ce_name or ('CE ' + str(ce_id) if ce_id else 'CE')}"
    banner = build_rich_header(meta, eyebrow="CE Health")
    doc = wrap_fragment(frag, scope_id="tab-cehealth", title=title, banner_html=banner)
    out = run_dir / "report.html"
    out.write_text(doc, encoding="utf-8")
    print(f"wrote {out} ({len(doc)} bytes) [standalone]")


def main():
    ap = argparse.ArgumentParser(description="Render the beautified CE Health tab fragment.")
    ap.add_argument("--run-dir", required=True, help="Run directory with CE Health artifacts.")
    ap.add_argument("--emit-facts", action="store_true",
                    help="Compute the compact CE Health facts pack (no bq, no render) and "
                         "write <run_dir>/ce_health_facts.json, then exit. Feeds the "
                         "CE-Health-insights sub-agent (references/ce_health_insights_guide.md).")
    ap.add_argument("--standalone", action="store_true",
                    help="Also wrap the fragment into an openable standalone report.html.")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).expanduser()
    if args.emit_facts:
        facts = compute_facts(run_dir)
        out = run_dir / "ce_health_facts.json"
        out.write_text(json.dumps(facts, indent=2), encoding="utf-8")
        print(f"wrote {out} ({len(json.dumps(facts))} bytes)")
        return
    frag = build_fragment(run_dir)
    out = run_dir / "ce_health_tab.html"
    out.write_text(frag, encoding="utf-8")
    print(f"wrote {out} ({len(frag)} bytes)")
    if args.standalone:
        _write_standalone(run_dir, frag)


if __name__ == "__main__":
    main()
