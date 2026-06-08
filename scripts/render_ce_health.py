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
      §7 Shapley   → the ONE agreed exception: a corrected canonical 6-factor
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
    m = re.search(rf'^## .*{re.escape(name)}.*?$(.*?)(?=^## |\Z)', md, re.M | re.S)
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
    "</style>"
)

_TRAIL_DELTA = re.compile(r'^(?P<main>.*\S)\s+(?P<delta>[+\-−][\d.,]+(?:pp|%))(?:\s*\([^)]*\))?$')
_PURE_DELTA = re.compile(r'^(?P<delta>[+\-−][\d.,]+(?:pp|%))(?:\s*\([^)]*\))?$')


def _delta_dir(delta):
    """Classify a delta token like '+3.7pp' / '-63%' → 'up' | 'down' | 'flat'.
    Near-flat band (amber): |Δ| < 1pp or < 5%. Tunable."""
    m = re.match(r'^([+\-−])([\d.,]+)(pp|%)$', delta.replace('−', '-').strip())
    if not m:
        return 'flat'
    sign, num, unit = m.groups()
    val = float(num.replace(',', '')) * (-1 if sign == '-' else 1)
    thr = 1.0 if unit == 'pp' else 5.0
    return 'flat' if abs(val) < thr else ('up' if val > 0 else 'down')


def _cell_split(c):
    """Render a cell that may carry a trailing delta as a two-line value+delta, a
    lone delta as a single coloured token, else fall back to plain `_cell`."""
    s = c.strip()
    m = _TRAIL_DELTA.match(s)
    if m:
        d = _delta_dir(m.group('delta'))
        return (f'<span class="ceh-val">{_cell(m.group("main"))}</span>'
                f'<span class="ceh-chg {d}">{_html.escape(m.group("delta"))}</span>')
    m = _PURE_DELTA.match(s)
    if m:
        d = _delta_dir(m.group('delta'))
        return f'<span class="ceh-chg {d}">{_html.escape(m.group("delta"))}</span>'
    return _cell(c)


def styled_table(hdr, rows, highlight_first=False, maxrows=None, sticky_cols=0,
                 sticky_widths=None, split_deltas=False, groups=None):
    """Visual-kit styled table. `sticky_cols` freezes the first N columns on
    horizontal scroll (position:sticky), `sticky_widths` their px widths.
    `split_deltas` renders 'value + trailing delta' cells as a bold value with a
    coloured delta beneath (and lone-delta cells coloured). `groups` is an ordered
    list of (label, span) rendered as a grouped header band above the column row
    (only when the spans sum to the column count — else skipped, never broken)."""
    if maxrows: rows = rows[:maxrows]
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

    th = ""
    for i, h in enumerate(hdr):
        cls = ' class="num"' if numcol[i] else ''
        st = _stick(i, True)
        style_attr = ' style="' + st + '"' if st else ''
        th += "<th" + cls + style_attr + ">" + _cell(h) + "</th>"
    # Optional grouped header band — only when spans line up with the columns.
    grp = ""
    if groups and sum(int(s) for _, s in groups) == ncol:
        gcells = "".join(
            f'<th class="ceh-group"{f" colspan=\"{int(s)}\"" if int(s) > 1 else ""}>{_html.escape(str(lbl))}</th>'
            for lbl, s in groups)
        grp = f"<tr>{gcells}</tr>"
    trs = ""
    for k, r in enumerate(rows):
        rcls = ' class="highlight-row"' if (highlight_first and k == 0) else ''
        tds = ""
        for i, c in enumerate(r):
            cls = ' class="num"' if (i < ncol and numcol[i]) else ''
            st = _stick(i, False)
            style_attr = ' style="' + st + '"' if st else ''
            inner = _cell_split(c) if split_deltas else _cell(c)
            tds += "<td" + cls + style_attr + ">" + inner + "</td>"
        trs += f"<tr{rcls}>{tds}</tr>"
    return f'<div style="overflow-x:auto;"><table><thead>{grp}<tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def block(title, bid, inner, verdict=None):
    v = f'<div class="verdict-line neutral">{verdict}</div>' if verdict else ''
    return f'<div class="analysis-block" id="{bid}"><div class="block-title">{title}</div>{v}{inner}</div>'


def _subhead(t):
    return f'<div style="font-size:13px;font-weight:700;color:#2a2a44;margin:14px 0 6px;">{t}</div>'


# ─────────────────────────────────────────────────────────────────────────────
# Query 1 (via bq CLI) — raw revenue-component rows for the 6-factor Shapley
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
    AND page_type IN (
      'Collection','ShoulderPage','Cruises Landing Page','Hop-On Hop-Off',
      'Airport Transfers','Content Page','Theme','Collection Page','Experience Page'
    )
    AND (advertising_channel_type IS NULL OR advertising_channel_type != 'PERFORMANCE_MAX')
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
# (revenue_actual) — the figure the 6-factor identity reconstructs.
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
    """Build {'pre': {...}, 'post': {...}} of the six 6-factor inputs via Query 1.

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
# Canonical 6-factor Shapley revenue bridge
#   revenue = traffic × cvr × orders/converter × aov × completion × take_rate
# All 720 permutations; unattributable = actual_delta − sum(contributions) ≈ $0.
# ─────────────────────────────────────────────────────────────────────────────

_FAC = ["traffic", "cvr", "orders_per_converter", "aov", "completion_rate", "take_rate"]
_FLBL = {"traffic": "Traffic", "cvr": "CVR", "orders_per_converter": "Orders / User",
         "aov": "AOV", "completion_rate": "Completion Rate", "take_rate": "Take Rate"}


def _facs(r):
    return dict(
        traffic=r["overall_traffic"],
        cvr=r["users_order_completed"] / r["overall_traffic"],
        orders_per_converter=r["count_orders"] / r["users_order_completed"],
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


def build_shapley_block(raw, windows):
    """The §7 corrected 6-factor booking-revenue waterfall (Plotly)."""
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
    x = [pre_lbl] + [_FLBL[f] for f in _FAC] + ["Unattributable", post_lbl]
    y = [round(pre_rev, 2)] + [round(contrib[f], 2) for f in _FAC] + [round(unattr, 2), round(post_rev, 2)]
    measure = ["absolute"] + ["relative"] * (len(_FAC) + 1) + ["total"]
    text = [money(pre_rev)] + [_sm(contrib[f]) for f in _FAC] + [_sm(unattr), money(post_rev)]
    drags = [f"{_FLBL[k]} ({_sm(v)})" for k, v in sorted(contrib.items(), key=lambda x: x[1]) if v < 0][:2]
    lifts = [f"{_FLBL[k]} ({_sm(v)})" for k, v in sorted(contrib.items(), key=lambda x: -x[1]) if v > 0][:2]

    verdict = (
        f"Booking revenue {'fell' if delta < 0 else 'rose'} {_sm(delta)} ({net_pct:.1f}%) "
        f"Pre → Post. Biggest {'drags' if drags else 'movers'}: {', '.join(drags) or '—'}; "
        f"offset by {', '.join(lifts) or '—'}. The 6-factor identity reconciles fully "
        f"({_sm(unattr)} unattributable). <em>Note: this decomposes booking revenue "
        f"(≈ CE Health's revenue_actual); the headline card shows CE Health's normalised Revenue.</em>"
    )
    return f'''<div class="analysis-block" id="cehealth-shapley">
  <div class="block-title">7. Driver Diagnosis (Shapley)</div>
  <div class="verdict-line neutral">{verdict}</div>
  <div id="chart-cehealth-shapley" class="chart-container"></div>
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
    height:420,margin:{{l:75,r:30,t:64,b:90}},plot_bgcolor:'#fff',paper_bgcolor:'#fff',
    font:{{family:'-apple-system,sans-serif',size:11,color:'#1a1a2e'}},showlegend:false,
    yaxis:{{title:'Revenue (USD)',tickprefix:'$',gridcolor:'#eef',zerolinecolor:'#ccc'}},
    xaxis:{{tickangle:15}}}},
    {{responsive:true,displayModeBar:false}});</script>
</div>'''


# ─────────────────────────────────────────────────────────────────────────────
# Build the fragment
# ─────────────────────────────────────────────────────────────────────────────

def card(label, post_val, delta_txt, delta_cls, pre_val=None):
    pre_html = f'<span class="pre">{pre_val}</span>' if pre_val else ''
    return (f'<div class="metric-card"><div class="label">{label}</div>'
            f'<div class="values">{pre_html}<span class="post">{post_val}</span></div>'
            f'<div class="delta {delta_cls}">{delta_txt}</div></div>')


def user_context_subsection(run_dir: Path) -> str:
    """Fill §8 with user-provided + recent context if any was captured this run.

    Deterministic embed of already-distilled markdown (user_context.md +
    user_data_*.md + slack_context.md) — no synthesis, no new sub-agent. 'What the
    RCA found against it' lives in the Summary; we just link there. Returns '' when
    nothing is present, so §8 renders exactly as before. Never fatal.
    """
    pieces = []
    try:
        uc = run_dir / "user_context.md"
        if uc.exists() and uc.read_text().strip():
            pieces.append(("Analyst context (focus · priors · known events)", uc.read_text().strip()))
        for p in sorted(run_dir.glob("user_data_*.md")):
            t = p.read_text().strip()
            if t:
                pieces.append((f"User data — {p.stem.replace('user_data_', '')}", t))
        sc = run_dir / "slack_context.md"
        if sc.exists():
            t = sc.read_text().strip()
            if t and "0 signals" not in t:
                pieces.append(("Recent Slack signals", t))
    except Exception:  # noqa: BLE001 — never let context embedding break the tab
        return ""
    if not pieces:
        return ""
    inner = "".join(
        f'{_subhead(title)}<div class="md-content">{render_markdown_to_html(body)}</div>'
        for title, body in pieces
    )
    link = ('<p style="font-size:12px;color:#666;margin-top:10px;">What the RCA found '
            'against this context → '
            '<a class="ref-link" href="#summary-cross-reference">Summary ↗</a></p>')
    return f'{_subhead("User-Provided &amp; Recent Context")}{inner}{link}'


def _prior_headline(d: Path) -> str:
    """Best-effort one-line headline for a prior run (its findings.md root cause)."""
    f = d / "findings.md"
    try:
        if f.exists():
            for ln in f.read_text().splitlines():
                t = ln.strip().lstrip("#").strip()
                if t and not t.startswith(("---", "|", "<")) and len(t) > 15:
                    return (t[:120] + "…") if len(t) > 120 else t
    except Exception:  # noqa: BLE001
        pass
    return "—"


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
            "Slack context: searched by SKILL.md")
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
        if n in ('rpc', 'aov', 'cr', 'tr'):
            return 'Order Metrics'
        if 'sel users' in n or 'traffic' in n or n in ('s2c', 'c2o', 's2o'):
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


def build_fragment(run_dir: Path) -> str:
    d = json.loads((run_dir / "ce_health_report.json").read_text())
    md = (run_dir / "ce_health_report.md").read_text()
    V, W = d["vitals"], d["windows"]
    cur, pri = V["current"], V["prior"]

    # §2 — vitals metric cards (TM = post, LM = pre, Δ MoM). Revenue card uses
    # CE Health's normalised revenue (matches the §2 table); §7 decomposes booking.
    rev_d = pct_delta(cur["revenue"], pri["revenue"]); roi_d = pp_delta(cur["roi_1"], pri["roi_1"])
    tr_d = pp_delta(cur["tr"], pri["tr"]); cr_d = pp_delta(cur["cr"], pri["cr"])
    aov_d = pct_delta(cur["aov"], pri["aov"]); ord_d = pct_delta(cur["orders"], pri["orders"])
    cards = "".join([
        card("Revenue", money(cur["revenue"]), f"Δ {rev_d[0]} MoM", rev_d[1], money(pri["revenue"])),
        card("ROI(1)", f"{cur['roi_1']:.0f}%", f"Δ {roi_d[0]} MoM", roi_d[1], f"{pri['roi_1']:.0f}%"),
        card("Take Rate", f"{cur['tr']:.1f}%", f"Δ {tr_d[0]} MoM", tr_d[1], f"{pri['tr']:.1f}%"),
        card("Completion", f"{cur['cr']:.1f}%", f"Δ {cr_d[0]} MoM", cr_d[1], f"{pri['cr']:.1f}%"),
        card("AOV", f"${cur['aov']:.0f}", f"Δ {aov_d[0]} MoM", aov_d[1], f"${pri['aov']:.0f}"),
        card("Orders", f"{cur['orders']:,}", f"Δ {ord_d[0]} MoM", ord_d[1], f"{pri['orders']:,}"),
    ])
    rev_norm_pct = pct_delta(cur["revenue"], pri["revenue"])[0]
    book_cur, book_pri = cur.get("revenue_actual"), pri.get("revenue_actual")
    book_pct = pct_delta(book_cur, book_pri)[0] if (book_cur and book_pri) else ""
    vit_note = (
        '<p style="font-size:12px;color:#777;margin-top:10px;">Note: the '
        f'<strong>Revenue</strong> row/card is CE Health\'s normalised figure '
        f'({money(cur["revenue"])}, {rev_norm_pct} MoM). The Driver Diagnosis (§7) '
        f'decomposes <strong>booking revenue</strong> (revenue_actual'
        + (f', {money(book_cur)}, {book_pct}' if book_cur else '')
        + ') — the figure the 6-factor identity reconstructs.</p>'
    )

    # §1 Metadata → header pills (rendered by compose.build_header). No block here.

    # §2 — cards + full 4-window table
    vh, vr = tables_in(section(md, "CE Vitals"))[0]
    s2 = block("2. CE Vitals", "cehealth-vitals",
               f'<div class="metric-cards" style="grid-template-columns:repeat(6,1fr);">{cards}</div>'
               + _subhead("Full 4-window comparison") + styled_table(vh, vr) + vit_note)

    # §3 Channel Breakdown — ALL rows (Δ columns coloured up/down/flat)
    s3 = block("3. Channel Breakdown", "cehealth-channels",
               styled_table(*tables_in(section(md, "Channel Breakdown"))[0], split_deltas=True))

    # §4 Funnel — all rows
    s4 = block("4. Funnel", "cehealth-funnel", styled_table(*tables_in(section(md, "Funnel"))[0]))

    # §5 L12M Trajectory — charts replace the two monthly tables (same data)
    l12 = section(md, "L12M Trajectory")
    t_health, t_paid = tables_in(l12)[0], tables_in(l12)[1]
    hr = t_health[1]; months = [r[0] for r in hr]
    rev = [numparse(r[1]) for r in hr]; orders = [numparse(r[2]) for r in hr]
    pr_ = t_paid[1]; clicks = [numparse(r[3]) for r in pr_]; paidroi = [numparse(r[6]) for r in pr_]
    c_rev = ('<div id="chart-cehealth-l12m-rev" class="chart-container" style="width:100%"></div>'
             f'''<script>Plotly.newPlot('chart-cehealth-l12m-rev',[{{type:'bar',name:'Revenue',x:{json.dumps(months)},y:{json.dumps(rev)},marker:{{color:'#6c8ebf'}}}},{{type:'scatter',mode:'lines+markers',name:'Orders',x:{json.dumps(months)},y:{json.dumps(orders)},line:{{color:'#c62828',width:2}},yaxis:'y2'}}],{{height:300,autosize:true,margin:{{l:62,r:55,t:14,b:55}},plot_bgcolor:'#fff',paper_bgcolor:'#fff',font:{{family:'-apple-system,sans-serif',size:11,color:'#1a1a2e'}},legend:{{orientation:'h',y:-0.25}},yaxis:{{title:'Revenue',tickprefix:'$',gridcolor:'#eef'}},yaxis2:{{title:'Orders',overlaying:'y',side:'right',showgrid:false}}}},{{responsive:true,displayModeBar:false}});</script>''')
    c_paid = ('<div id="chart-cehealth-l12m-paid" class="chart-container" style="width:100%"></div>'
              f'''<script>Plotly.newPlot('chart-cehealth-l12m-paid',[{{type:'bar',name:'Clicks',x:{json.dumps(months)},y:{json.dumps(clicks)},marker:{{color:'#90a4d4'}}}},{{type:'scatter',mode:'lines+markers',name:'Paid ROI %',x:{json.dumps(months)},y:{json.dumps(paidroi)},line:{{color:'#43A047',width:2}},yaxis:'y2'}}],{{height:300,autosize:true,margin:{{l:62,r:55,t:14,b:55}},plot_bgcolor:'#fff',paper_bgcolor:'#fff',font:{{family:'-apple-system,sans-serif',size:11,color:'#1a1a2e'}},legend:{{orientation:'h',y:-0.25}},yaxis:{{title:'Clicks',gridcolor:'#eef'}},yaxis2:{{title:'Paid ROI %',overlaying:'y',side:'right',showgrid:false,ticksuffix:'%'}}}},{{responsive:true,displayModeBar:false}});</script>''')
    s5 = block("5. L12M Trajectory", "cehealth-l12m",
               _subhead("CE Health (Monthly)") + c_rev + _subhead("Paid Performance (Monthly)") + c_paid
               + '<p style="font-size:12px;color:#777;margin-top:8px;">Charts visualise CE Health\'s '
               'monthly tables (same data). The full monthly tables remain in the CE Health source.</p>')

    # §6 Top TGIDs — ALL rows, first two cols (TGID, Experience) frozen on scroll,
    # in-cell deltas split into value+coloured-delta, grouped header bands.
    tg = tables_in(section(md, "Top TGIDs"))[0]
    s6 = block("6. Top TGIDs", "cehealth-tgids",
               styled_table(tg[0], tg[1], sticky_cols=2, sticky_widths=[64, 210],
                            split_deltas=True, groups=_tgid_groups(tg[0])))

    # §7 Driver Diagnosis (Shapley) — corrected 6-factor waterfall (Query 1).
    # On any Query-1 failure, fall back to CE Health's §7 table, verbatim.
    ce_id = d.get("ce_id") or d.get("metadata", {}).get("combined_entity_id")
    try:
        raw = query_raw(str(ce_id), W)
        s7 = build_shapley_block(raw, W)
        print("§7 Shapley: corrected 6-factor waterfall (Query 1 OK)")
    except Exception as e:  # noqa: BLE001 — any failure → verbatim fallback
        print(f"WARN: Query 1 failed ({e}); rendering CE Health's §7 table verbatim.", file=sys.stderr)
        sec7 = section(md, "Driver Diagnosis")
        tbls = tables_in(sec7)
        inner = styled_table(*tbls[0]) if tbls else f'<div class="md-content">{render_markdown_to_html(sec7)}</div>'
        s7 = block("7. Driver Diagnosis (Shapley)", "cehealth-shapley", inner)

    # §8 Historical Context — CE Health's markdown, plus our institutional memory
    # (prior RCAs for this CE) and any user-provided context captured this run.
    hist = ce_history_block(run_dir)          # synthesised trajectory (sub-agent)
    prior = prior_runs_block(run_dir, ce_id)  # deterministic prior-run index + links
    uctx = user_context_subsection(run_dir)   # user-provided + recent Slack
    hist_md = section(md, "Historical Context")
    if hist or prior or uctx:
        hist_md = _clean_history_md(hist_md)  # drop dead "None found" placeholders
    s8 = block("8. Historical Context", "cehealth-history",
               f'<div class="md-content">{render_markdown_to_html(hist_md)}</div>'
               + hist + prior + uctx)

    # §9 Lead Time Cohorts — all rows
    s9 = block("9. Lead Time Cohorts", "cehealth-leadtime",
               styled_table(*tables_in(section(md, "Lead Time Cohorts"))[0]))

    # §10 Landing Pages — ALL rows
    s10 = block("10. Landing Pages", "cehealth-landing",
                styled_table(*tables_in(section(md, "Landing Pages"))[0]))

    # §11 Customer Countries — ALL rows
    s11 = block("11. Customer Countries", "cehealth-countries",
                styled_table(*tables_in(section(md, "Customer Countries"))[0]))

    footer = (f'<footer style="text-align:center;font-size:12px;color:#aaa;padding:18px;">'
              f'CE Health v2.0 | {d.get("generated_at", "")} | {d.get("range", "month")} windows</footer>')
    resize = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "if(window.Plotly)document.querySelectorAll('#tab-cehealth .js-plotly-plot')"
              ".forEach(function(el){try{window.Plotly.Plots.resize(el);}catch(e){}});},200);});</script>")
    # Widen the CE Health tab beyond the 1050px .container so the wide tables
    # (TGIDs, Channels, Landing) are readable. Centered breakout.
    open_div = '<div style="width:min(1280px,95vw);margin-left:50%;transform:translateX(-50%);">'
    return (CEH_TABLE_STYLE + open_div + s2 + s3 + s4 + s5 + s6 + s7 + s8 + s9 + s10 + s11
            + footer + '</div>' + resize)


def main():
    ap = argparse.ArgumentParser(description="Render the beautified CE Health tab fragment.")
    ap.add_argument("--run-dir", required=True, help="Run directory with CE Health artifacts.")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).expanduser()
    frag = build_fragment(run_dir)
    out = run_dir / "ce_health_tab.html"
    out.write_text(frag, encoding="utf-8")
    print(f"wrote {out} ({len(frag)} bytes)")


if __name__ == "__main__":
    main()
