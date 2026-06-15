"""
Perf Audit v6.1 -- Report skeleton renderer.

Transforms bq.py output into a complete markdown document with pre-formatted
tables. Claude fills in <!-- NARRATIVE --> markers only.

Architecture: bq.py (data) -> render.py (tables) -> Claude (narrative)

Python 3.9 compatible. No external dependencies.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# FORMATTING HELPERS
# ============================================================================

def fm(v):
    # type: (Any) -> str
    """Format money: $129.4K or $887 or --"""
    if v is None:
        return '\u2014'
    v = float(v)
    sign = '-' if v < 0 else ''
    av = abs(v)
    if av >= 1000:
        return f"{sign}${av/1000:,.1f}K"
    return f"{sign}${av:,.0f}"


def fp(v):
    # type: (Any) -> str
    """Format percentage (2 decimal): 163.18%. Value already a percentage."""
    if v is None:
        return '\u2014'
    return f"{float(v):.2f}%"


def fp1(v):
    # type: (Any) -> str
    """Format percentage (1 decimal): 14.2%. For cohort table."""
    if v is None:
        return '\u2014'
    return f"{float(v):.1f}%"


def fd(v):
    # type: (Any) -> str
    """Format dollars: $2.07"""
    if v is None:
        return '\u2014'
    return f"${float(v):,.2f}"


def fi(v):
    # type: (Any) -> str
    """Format integer: 2,180"""
    if v is None:
        return '\u2014'
    return f"{int(v):,}"


def dp(n, o):
    # type: (Any, Any) -> str
    """Delta percentage: +86% or -14%"""
    if n is None or o is None:
        return '\u2014'
    n, o = float(n), float(o)
    if not o:
        return 'new'
    d = (n - o) / o * 100
    return f"+{d:.0f}%" if d >= 0 else f"{d:.0f}%"


def da(n, o):
    # type: (Any, Any) -> str
    """Delta absolute money: +$59.7K or -$21.0K"""
    if n is None or o is None:
        return '\u2014'
    d = float(n) - float(o)
    return f"+{fm(d)}" if d >= 0 else fm(d)


def dpp(n, o):
    # type: (Any, Any) -> str
    """Delta percentage points: +4.2pp or -11.1pp"""
    if n is None or o is None:
        return '\u2014'
    d = float(n) - float(o)
    return f"+{d:.1f}pp" if d >= 0 else f"{d:.1f}pp"


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _cohort_display(name):
    # type: (str) -> str
    if name in ('Other Languages', 'Other'):
        return name
    return f"{name} \u2014 All Geos"


def _g(d, k, default=None):
    # type: (Any, str, Any) -> Any
    """Safe dict get with float coercion."""
    if not d:
        return default
    v = d.get(k) if isinstance(d, dict) else default
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ============================================================================
# SECTION RENDERERS
# ============================================================================

def render_header(ce_name, market, today, l4w, p4w, ly, lp_url):
    # type: (str, str, str, Tuple[str,str], Tuple[str,str], Tuple[str,str], str) -> str
    lines = [
        f"# Paid Performance Audit: {ce_name}",
        f"**Market**: {market}",
        f"**Date**: {today}",
        f"**Period**: L4W ({l4w[0]} \u2014 {l4w[1]}) vs P4W ({p4w[0]} \u2014 {p4w[1]}) vs LY ({ly[0]} \u2014 {ly[1]})",
    ]
    if lp_url:
        lines.append(f"**Landing Page**: {lp_url}")
    lines.extend(["", "---"])
    return "\n".join(lines)


def render_table1(t1):
    # type: (Dict) -> str
    """Table 1: CE Health (all channels)."""
    if not t1:
        return "*Table 1 data unavailable.*"
    l = t1.get("l4w") or {}
    p = t1.get("p4w") or {}
    y = t1.get("ly") or {}
    if not l:
        return "*Table 1 data unavailable.*"

    rows = [
        "**Table 1: CE Health (all channels) \u2014 `combined_entity_stats`**",
        "",
        "| Period | Revenue | ROI (1) | TR | CR | AOV | Orders |",
        "|--------|---------|---------|----|----|-----|--------|",
    ]
    for label, d in [("L4W", l), ("P4W", p), ("LY", y)]:
        rows.append(
            f"| {label} | {fm(_g(d,'revenue'))} | {fp(_g(d,'roi_1'))} | "
            f"{fp(_g(d,'tr'))} | {fp(_g(d,'cr'))} | {fd(_g(d,'aov'))} | "
            f"{fi(_g(d,'orders'))} |"
        )
    for label, base in [("**\u0394 P4W**", p), ("**\u0394 LY**", y)]:
        rl, rb = _g(l, 'revenue'), _g(base, 'revenue')
        rows.append(
            f"| {label} | {dp(rl, rb)} ({da(rl, rb)}) | "
            f"{dpp(_g(l,'roi_1'), _g(base,'roi_1'))} | "
            f"{dpp(_g(l,'tr'), _g(base,'tr'))} | "
            f"{dpp(_g(l,'cr'), _g(base,'cr'))} | "
            f"{dp(_g(l,'aov'), _g(base,'aov'))} | "
            f"{dp(_g(l,'orders'), _g(base,'orders'))} |"
        )
    return "\n".join(rows)


def render_table2(t2):
    # type: (Dict) -> str
    """Table 2: Paid Performance."""
    if not t2:
        return "*Table 2 data unavailable.*"
    l = t2.get("l4w") or {}
    p = t2.get("p4w") or {}
    y = t2.get("ly") or {}
    if not l:
        return "*Table 2 data unavailable.*"

    rows = [
        "**Table 2: Paid Performance (Google Search + PMax + Bing)**",
        "",
        "| Period | Paid Rev | Paid ROI | RPC | CPC | Ad Spend | Clicks | CTR | CVR | CM1 | Paid TR | Paid CR |",
        "|--------|----------|----------|-----|-----|----------|--------|-----|-----|-----|---------|---------|",
    ]
    for label, d in [("L4W", l), ("P4W", p), ("LY", y)]:
        rows.append(
            f"| {label} | {fm(_g(d,'paid_rev'))} | {fp(_g(d,'paid_roi'))} | "
            f"{fd(_g(d,'rpc'))} | {fd(_g(d,'cpc'))} | {fm(_g(d,'ad_spend'))} | "
            f"{fi(_g(d,'clicks'))} | {fp(_g(d,'ctr'))} | {fp(_g(d,'cvr'))} | "
            f"{fm(_g(d,'cm1'))} | {fp(_g(d,'paid_tr'))} | {fp(_g(d,'paid_cr'))} |"
        )
    for label, b in [("**\u0394 P4W**", p), ("**\u0394 LY**", y)]:
        rows.append(
            f"| {label} | {dp(_g(l,'paid_rev'), _g(b,'paid_rev'))} | "
            f"{dpp(_g(l,'paid_roi'), _g(b,'paid_roi'))} | "
            f"{dp(_g(l,'rpc'), _g(b,'rpc'))} | "
            f"{dp(_g(l,'cpc'), _g(b,'cpc'))} | "
            f"{dp(_g(l,'ad_spend'), _g(b,'ad_spend'))} | "
            f"{dp(_g(l,'clicks'), _g(b,'clicks'))} | "
            f"{dpp(_g(l,'ctr'), _g(b,'ctr'))} | "
            f"{dpp(_g(l,'cvr'), _g(b,'cvr'))} | "
            f"{dp(_g(l,'cm1'), _g(b,'cm1'))} | "
            f"{dpp(_g(l,'paid_tr'), _g(b,'paid_tr'))} | "
            f"{dpp(_g(l,'paid_cr'), _g(b,'paid_cr'))} |"
        )
    return "\n".join(rows)


def render_table3(channels):
    # type: (Dict) -> str
    """Table 3: Channel Breakdown."""
    tw = channels.get("tw") or []
    ly_list = channels.get("ly") or []
    p4w_list = channels.get("prior_4w") or []
    if not tw:
        return "*Table 3 data unavailable.*"

    ly_map = {r["channel"]: r for r in ly_list}
    p4w_map = {r["channel"]: r for r in p4w_list}

    tw_total = sum(_g(r, "revenue", 0) for r in tw)
    ly_total = sum(_g(r, "revenue", 0) for r in ly_list)
    p4w_total = sum(_g(r, "revenue", 0) for r in p4w_list)

    tw_sorted = sorted(tw, key=lambda r: _g(r, "revenue", 0), reverse=True)

    rows = [
        "**Channel Breakdown**",
        "",
        "| Channel | L4W Rev | \u0394 LY | \u0394 P4W | TR | CR | AOV | Orders | Share |",
        "|---------|---------|------|-------|------|------|------|--------|-------|",
    ]

    for ch in tw_sorted:
        name = ch["channel"]
        rev = _g(ch, "revenue", 0)
        ly_ch = ly_map.get(name, {})
        p4w_ch = p4w_map.get(name, {})

        tw_share = rev / tw_total * 100 if tw_total else 0

        if tw_share < 1:
            share_str = "<1%"
        else:
            share_str = f"{tw_share:.0f}%"

        d_ly = dp(rev, _g(ly_ch, "revenue")) if ly_ch else '\u2014'
        d_p4w = dp(rev, _g(p4w_ch, "revenue")) if p4w_ch else '\u2014'

        rows.append(
            f"| {name} | {fm(rev)} | {d_ly} | {d_p4w} | "
            f"{fp(_g(ch,'tr'))} | {fp(_g(ch,'cr'))} | "
            f"{fd(_g(ch,'aov'))} | {fi(_g(ch,'orders'))} | {share_str} |"
        )

    total_d_ly = dp(tw_total, ly_total) if ly_total else '\u2014'
    total_d_p4w = dp(tw_total, p4w_total) if p4w_total else '\u2014'
    tw_total_orders = sum(_g(r, "orders", 0) for r in tw)
    rows.append(
        f"| **TOTAL** | **{fm(tw_total)}** | **{total_d_ly}** | **{total_d_p4w}** "
        f"| | | | **{fi(tw_total_orders)}** | **100%** |"
    )
    return "\n".join(rows)


# ============================================================================
# COHORT TABLE (Section 4a)
# ============================================================================

def _cohort_data_cells(d):
    # type: (Dict) -> List[str]
    """13 formatted cells: Spend..CR (1 decimal percentages)."""
    if not d:
        return ['\u2014'] * 13
    return [
        fm(_g(d, "spend")),
        fd(_g(d, "cpc")),
        fi(_g(d, "clicks")),
        fp1(_g(d, "ctr")),
        fi(_g(d, "conversions")),
        fm(_g(d, "cm1")),
        fm(_g(d, "revenue")),
        fd(_g(d, "aov")),
        fp1(_g(d, "cvr")),
        fp1(_g(d, "roi")),
        fd(_g(d, "rpc")),
        fp1(_g(d, "tr")),
        fp1(_g(d, "cr")),
    ]


def _cohort_delta_cells(curr, base):
    # type: (Dict, Dict) -> List[str]
    """13 delta cells matching _cohort_data_cells column order."""
    if not curr or not base:
        return ['\u2014'] * 13
    return [
        dp(_g(curr, "spend"), _g(base, "spend")),
        dp(_g(curr, "cpc"), _g(base, "cpc")),
        dp(_g(curr, "clicks"), _g(base, "clicks")),
        dpp(_g(curr, "ctr"), _g(base, "ctr")),
        dp(_g(curr, "conversions"), _g(base, "conversions")),
        dp(_g(curr, "cm1"), _g(base, "cm1")),
        dp(_g(curr, "revenue"), _g(base, "revenue")),
        dp(_g(curr, "aov"), _g(base, "aov")),
        dpp(_g(curr, "cvr"), _g(base, "cvr")),
        dpp(_g(curr, "roi"), _g(base, "roi")),
        dp(_g(curr, "rpc"), _g(base, "rpc")),
        dpp(_g(curr, "tr"), _g(base, "tr")),
        dpp(_g(curr, "cr"), _g(base, "cr")),
    ]


def _aggregate_cohorts(cohorts):
    # type: (List[Dict]) -> Dict[str, Any]
    """Sum cohort metrics for TOTAL row."""
    sum_keys = ["spend", "clicks", "impressions", "conversions", "cm1",
                "revenue", "order_value", "order_value_completed", "coupon_wallet"]
    agg = {k: sum(_g(c, k, 0) for c in cohorts) for k in sum_keys}  # type: Dict[str, Any]
    orders = sum(int(_g(c, "orders", 0)) for c in cohorts)
    agg["orders"] = orders

    cl = agg["clicks"]
    sp = agg["spend"]
    conv = agg["conversions"]
    cm1 = agg["cm1"]
    rev = agg["revenue"]
    ov = agg["order_value"]
    ovc = agg["order_value_completed"]
    cw = agg["coupon_wallet"]
    impr = agg["impressions"]
    mkt = sp + cw

    agg["cpc"] = sp / cl if cl else None
    agg["ctr"] = cl / impr * 100 if impr else None
    agg["cvr"] = conv / cl * 100 if cl else None
    agg["aov"] = ov / orders if orders else None
    agg["tr"] = rev / ovc * 100 if ovc else None
    agg["cr"] = ovc / ov * 100 if ov else None
    agg["roi"] = cm1 / mkt * 100 if mkt else None
    agg["rpc"] = rev / cl if cl else None
    return agg


def render_cohort_table(cohorts):
    # type: (Dict) -> str
    """Section 4a: Campaign Cohort Table."""
    tw = cohorts.get("tw") or []
    ly_list = cohorts.get("ly") or []
    p4w_list = cohorts.get("prior_4w") or []
    if not tw:
        return "*Cohort data unavailable.*"

    ly_map = {r["cohort"]: r for r in ly_list}
    p4w_map = {r["cohort"]: r for r in p4w_list}
    tw_sorted = sorted(tw, key=lambda r: _g(r, "revenue", 0), reverse=True)
    total_cm1 = sum(_g(r, "cm1", 0) for r in tw)

    rows = [
        "| Cohort | Window | Spend | CPC | Clicks | CTR | Conv | CM1 | Rev | AOV | CVR | ROI | RPC | TR | CR | SIS | CM1 % |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for c in tw_sorted:
        name = c["cohort"]
        display = _cohort_display(name)
        ly_c = ly_map.get(name, {})
        p4w_c = p4w_map.get(name, {})
        cm1_pct = _g(c, "cm1", 0) / total_cm1 * 100 if total_cm1 else 0

        # L4W row
        cells = _cohort_data_cells(c)
        parts = [display, "L4W"] + cells + [fp1(_g(c, "avg_sis")), f"{cm1_pct:.1f}%"]
        rows.append("| " + " | ".join(parts) + " |")

        # LY row
        cells = _cohort_data_cells(ly_c)
        parts = ["", "LY"] + cells + ['\u2014', '\u2014']
        rows.append("| " + " | ".join(parts) + " |")

        # P4W row
        cells = _cohort_data_cells(p4w_c)
        parts = ["", "P4W"] + cells + ['\u2014', '\u2014']
        rows.append("| " + " | ".join(parts) + " |")

        # Delta LY
        dcells = _cohort_delta_cells(c, ly_c)
        parts = ["", "**\u0394 LY**"] + dcells + ['\u2014', '\u2014']
        rows.append("| " + " | ".join(parts) + " |")

        # Delta P4W
        dcells = _cohort_delta_cells(c, p4w_c)
        parts = ["", "**\u0394 P4W**"] + dcells + ['\u2014', '\u2014']
        rows.append("| " + " | ".join(parts) + " |")

    # TOTAL row
    total_d = _aggregate_cohorts(tw)
    cells = _cohort_data_cells(total_d)
    bold_cells = [f"**{c}**" for c in cells]
    parts = ["**TOTAL**", "**L4W**"] + bold_cells + ['\u2014', "**100%**"]
    rows.append("| " + " | ".join(parts) + " |")

    rows.append("")
    rows.append("*\\* Google Search only \u2014 PMax & Bing in Table 3.*")

    return "\n".join(rows)


# ============================================================================
# BUDGET TABLE
# ============================================================================

def _budget_rows(budget):
    # type: (List) -> List[str]
    """Render budget rows for a list of campaign dicts."""
    rows = []
    for b in budget:
        name = (b.get("campaign_name") or "")[:50]
        troas = _g(b, "troas_target")
        ctype = b.get("campaign_type") or "\u2014"
        rows.append(
            f"| {name} | {ctype} | {fp1(troas) if troas else '\u2014'} | "
            f"{b.get('bid_strategy') or '\u2014'} | "
            f"{fd(_g(b,'daily_budget')) if _g(b,'daily_budget') else '\u2014'} | "
            f"{fm(_g(b,'spend'))} | {fp1(_g(b,'sis'))} | "
            f"{fp1(_g(b,'budget_lost_is'))} | {fp1(_g(b,'rank_lost_is'))} |"
        )
    return rows


_BUDGET_HEADER = [
    "| Campaign | Type | tROAS | Bid Strategy | Daily Budget | L4W Spend | SIS | Budget Lost | Rank Lost |",
    "|----------|------|-------|-------------|--------------|-----------|-----|-------------|-----------|",
]


def render_budget_table(budget):
    # type: (List) -> str
    """Summary by bidding type (Individual vs Portfolio) for main body."""
    if not budget:
        return "*Budget data unavailable.*"
    active = [b for b in budget if _g(b, "spend", 0) > 0]
    if not active:
        return "*No active campaigns in L4W.*"

    types = {}  # type: Dict[str, Dict]
    for b in active:
        ctype = b.get("campaign_type") or "Unknown"
        if ctype not in types:
            types[ctype] = {"count": 0, "spend": 0, "cm1": 0, "clicks": 0,
                            "conv": 0, "sis_num": 0, "sis_den": 0,
                            "rank_num": 0, "rank_den": 0, "budget_limited": []}
        t = types[ctype]
        t["count"] += 1
        sp = _g(b, "spend", 0)
        t["spend"] += sp
        t["cm1"] += _g(b, "cm1", 0)
        t["clicks"] += _g(b, "clicks", 0)
        t["conv"] += _g(b, "conversions", 0)
        if _g(b, "sis") is not None:
            t["sis_num"] += _g(b, "sis", 0) * sp
            t["sis_den"] += sp
        if _g(b, "rank_lost_is") is not None:
            t["rank_num"] += _g(b, "rank_lost_is", 0) * sp
            t["rank_den"] += sp
        if _g(b, "budget_lost_is", 0) > 10:
            name = (b.get("campaign_name") or "")[:30]
            t["budget_limited"].append(f"{name} {_g(b,'budget_lost_is'):.0f}%")

    rows = [
        "**Bidding Summary**",
        "",
        "| Bidding Type | Campaigns | L4W Spend | ROI | CVR | Avg SIS | Avg Rank Lost | Budget Limited |",
        "|-------------|-----------|-----------|-----|-----|---------|---------------|----------------|",
    ]
    for ctype in ["Individual", "Portfolio", "Unknown"]:
        t = types.get(ctype)
        if not t:
            continue
        sp = t["spend"]
        roi = t["cm1"] / sp * 100 if sp else None
        cvr = t["conv"] / t["clicks"] * 100 if t["clicks"] else None
        avg_sis = t["sis_num"] / t["sis_den"] if t["sis_den"] else None
        avg_rank = t["rank_num"] / t["rank_den"] if t["rank_den"] else None
        bl = ", ".join(t["budget_limited"][:2]) if t["budget_limited"] else "No"
        rows.append(
            f"| {ctype} | {t['count']} | {fm(sp)} | {fp1(roi)} | {fp1(cvr)} | "
            f"{fp1(avg_sis)} | {fp1(avg_rank)} | {bl} |"
        )
    return "\n".join(rows)


def render_budget_table_full(budget):
    # type: (List) -> str
    """All campaigns for appendix A6."""
    if not budget:
        return "*Budget data unavailable.*"
    return "\n".join(_BUDGET_HEADER + _budget_rows(budget))


# ============================================================================
# GEO TABLE
# ============================================================================

def render_geo_table(geo, customers, customers_ly=None):
    # type: (Dict, List, Optional[List]) -> str
    l4w = geo.get("l4w") or []
    ly = geo.get("ly") or []
    if not l4w:
        return "*Geo data unavailable.*"

    ly_map = {r.get("country"): r for r in ly}
    total_clicks = sum(_g(r, "clicks", 0) for r in l4w)
    ly_total_clicks = sum(_g(r, "clicks", 0) for r in ly)

    cust_map = {}  # type: Dict[str, float]
    if customers:
        cust_total = sum(_g(r, "orders", 0) for r in customers)
        for r in customers:
            cc = r.get("customer_country")
            if cc and cust_total:
                cust_map[cc] = _g(r, "orders", 0) / cust_total * 100

    cust_ly_map = {}  # type: Dict[str, float]
    if customers_ly:
        cust_ly_total = sum(_g(r, "orders", 0) for r in customers_ly)
        for r in customers_ly:
            cc = r.get("customer_country")
            if cc and cust_ly_total:
                cust_ly_map[cc] = _g(r, "orders", 0) / cust_ly_total * 100

    rows = [
        "| Country | Ad Clicks (\u0394 LY) | Click Share (\u0394 LY) | Customer Share (\u0394 LY) | Gap | CPC (\u0394 LY) |",
        "|---------|------------------|-------------------|------------------------|-----|------------|",
    ]

    for r in l4w:
        country = r.get("country", "Unknown")
        cl = _g(r, "clicks", 0)
        ly_r = ly_map.get(country, {})
        ly_cl = _g(ly_r, "clicks", 0)

        tw_share = cl / total_clicks * 100 if total_clicks else 0
        ly_share = ly_cl / ly_total_clicks * 100 if ly_total_clicks and ly_r else None

        click_str = fi(cl)
        if ly_r:
            click_str += f" ({dp(cl, ly_cl)})"
        share_str = f"{tw_share:.1f}%"
        if ly_share is not None:
            share_str += f" ({tw_share - ly_share:+.1f}pp)"

        cust_share = cust_map.get(country)
        cust_ly_share = cust_ly_map.get(country)
        gap = cust_share - tw_share if cust_share is not None else None

        cust_str = f"{cust_share:.1f}%" if cust_share is not None else '\u2014'
        if cust_share is not None and cust_ly_share is not None:
            cust_str += f" ({cust_share - cust_ly_share:+.1f}pp)"

        cpc_str = fd(_g(r, "cpc"))
        if ly_r and _g(ly_r, "cpc") is not None:
            cpc_str += f" ({dp(_g(r,'cpc'), _g(ly_r,'cpc'))})"

        rows.append(
            f"| {country} | {click_str} | {share_str} | "
            f"{cust_str} | "
            f"{f'{gap:+.1f}pp' if gap is not None else '\u2014'} | "
            f"{cpc_str} |"
        )
    return "\n".join(rows)


# ============================================================================
# MONEY ON THE TABLE (Section 4c-iii)
# ============================================================================

def _render_cohort_opportunity(c, total_cm1):
    # type: (Dict, float) -> Optional[List[str]]
    """Render money-on-table for a single cohort. Returns lines or None if no SIS data."""
    cm1_pct = _g(c, "cm1", 0) / total_cm1 * 100 if total_cm1 else 0
    cohort_name = _cohort_display(c.get("cohort", "Unknown"))
    sis = _g(c, "avg_sis")
    rank_lost = _g(c, "avg_rank_lost", 0) * 100
    budget_lost = _g(c, "avg_budget_lost", 0) * 100
    impressions = _g(c, "impressions", 0)
    clicks = _g(c, "clicks", 0)
    rpc = _g(c, "rpc")

    if not sis or not impressions or sis >= 50:
        return None

    eligible = impressions / (sis / 100)
    rank_lost_searches = eligible * (rank_lost / 100) if rank_lost else 0
    ctr_raw = clicks / impressions if impressions else 0
    sis_int = round(sis)
    gap_to_50 = max(50 - sis_int, 1)

    def scenario(pp):
        add_impr = eligible * pp / 100
        add_cl = int(round(add_impr * ctr_raw))
        add_rev = int(round(add_cl * rpc)) if rpc else 0
        return add_cl, add_rev

    cl_10, rev_10 = scenario(10)
    cl_50, rev_50 = scenario(gap_to_50)
    cl_1, rev_1 = scenario(1)

    constraint = "budget" if budget_lost > rank_lost else "rank"
    other = "rank" if constraint == "budget" else "budget"

    return [
        f"**{cohort_name} ({cm1_pct:.1f}% of Google Search CM1):**",
        f"- Current SIS: {sis:.1f}% | Rank-Lost IS: {rank_lost:.1f}% | Budget-Lost IS: {budget_lost:.0f}%",
        f"- Eligible searches (L4W): ~{fi(eligible)} | We show in: ~{fi(impressions)}",
        f"- Rank-lost searches: ~{fi(rank_lost_searches)}",
        "",
        "| Scenario | SIS Gain | Additional Clicks | Revenue Opportunity |",
        "|----------|----------|------------------|-------------------|",
        f"| +10pp SIS ({sis_int}%\u2192{sis_int+10}%) | +10pp | +{fi(cl_10)} | **+${fi(rev_10)}/L4W** |",
        f"| +{gap_to_50}pp SIS ({sis_int}%\u219250%) | +{gap_to_50}pp | +{fi(cl_50)} | **+${fi(rev_50)}/L4W** |",
        "",
        f"Every 1pp SIS = ~{fi(cl_1)} clicks = ~${fi(rev_1)}/L4W at current RPC ({fd(rpc)}).",
        f"Constraint: **{constraint}** ({budget_lost:.0f}% budget-lost).",
    ]


def render_money_on_table(cohorts):
    # type: (Dict) -> str
    tw = cohorts.get("tw") or []
    if not tw:
        return "*Money on the Table data unavailable.*"

    total_cm1 = sum(_g(c, "cm1", 0) for c in tw)

    # Rank by opportunity: highest revenue potential = lowest SIS × highest RPC × most spend
    # Filter to cohorts with SIS data and meaningful spend (>$500)
    candidates = [c for c in tw if _g(c, "avg_sis") and _g(c, "spend", 0) > 500]
    if not candidates:
        return "*Money on the Table: SIS data unavailable.*"

    # Sort by opportunity: rank-lost % × RPC × eligible searches (descending)
    def opportunity_score(c):
        sis = _g(c, "avg_sis", 0)
        rpc = _g(c, "rpc", 0) or 0
        impr = _g(c, "impressions", 0)
        eligible = impr / (sis / 100) if sis else 0
        rank_lost_pct = _g(c, "avg_rank_lost", 0)
        return eligible * rank_lost_pct * rpc

    ranked = sorted(candidates, key=opportunity_score, reverse=True)

    lines = []
    for c in ranked[:3]:
        section = _render_cohort_opportunity(c, total_cm1)
        if section:
            lines.extend(section)
            lines.append("")

    return "\n".join(lines) if lines else "*Money on the Table: no cohorts with SIS < 50%.*"


# ============================================================================
# PAID VALUE SHAPLEY (Section 4 — driver attribution)
# ============================================================================

def _signed_money(v):
    # type: (Optional[float]) -> str
    if v is None:
        return '—'
    return f"+{fm(v)}" if v >= 0 else fm(v)


def _shapley_cells(decomp):
    # type: (Dict) -> Tuple[Dict[str, Tuple[str, str]], bool]
    """Per-factor (contribution, share) cells for one comparison + the net-flat flag.

    When the net change is near zero but drivers are large and offsetting (e.g.
    clicks down cancelled by avg CM1 up), "share of Δ" explodes and is meaningless —
    so the share switches to "share of gross movement" (contribution ÷ Σ|contrib|)
    and net_flat is returned True so the caller can label the column accordingly.
    """
    total = decomp.get("total_delta") or 0.0
    names = ["clicks", "cvr", "avg_cm1"]
    contribs = {nm: (decomp.get(nm) or {}).get("contribution") for nm in names}
    gross = sum(abs(c) for c in contribs.values() if c is not None) or 1.0
    net_flat = abs(total) < 0.30 * gross
    out = {}
    for nm in names:
        c = contribs.get(nm)
        if c is None:
            out[nm] = ('—', '—')
        elif net_flat:
            out[nm] = (_signed_money(c), f"{c / gross * 100:+.0f}%")
        else:
            share = (decomp.get(nm) or {}).get("share_pct")
            out[nm] = (_signed_money(c), f"{share:+.0f}%" if share is not None else '—')
    return out, net_flat


def render_paid_shapley(shapley):
    # type: (Optional[Dict]) -> str
    """Render the paid-value Shapley decomposition (Clicks x CVR x Avg CM1)."""
    if not shapley:
        return "*Paid value decomposition unavailable.*"
    w = shapley.get("windows") or {}
    cur = w.get("l4w") or {}
    pri = w.get("p4w") or {}
    lyw = w.get("ly") or {}
    if not cur.get("cm1") and not pri.get("cm1") and not lyw.get("cm1"):
        return "*Paid value decomposition: no paid CM1 in any window.*"

    mom_cells, mom_flat = _shapley_cells(shapley.get("mom") or {})
    yoy_cells, yoy_flat = _shapley_cells(shapley.get("yoy") or {})
    mom_hdr = "MoM Share*" if mom_flat else "MoM Share of Δ"
    yoy_hdr = "YoY Share*" if yoy_flat else "YoY Share of Δ"

    factors = [
        ("clicks", "Clicks (volume)", lambda win: fi(win.get("clicks"))),
        ("cvr", "CVR (conv/click)", lambda win: fp1((win.get("cvr") or 0) * 100)),
        ("avg_cm1", "Avg CM1 (CM1/conv)", lambda win: fd(win.get("avg_cm1"))),
    ]

    lines = [
        f"Paid CM1 (Google Search + PMax + Bing): "
        f"MoM {da(cur.get('cm1'), pri.get('cm1'))} ({fm(pri.get('cm1'))} → {fm(cur.get('cm1'))}) · "
        f"YoY {da(cur.get('cm1'), lyw.get('cm1'))} ({fm(lyw.get('cm1'))} → {fm(cur.get('cm1'))}).",
        "",
        f"| Factor | L4W | P4W | LY | MoM Contrib | {mom_hdr} | YoY Contrib | {yoy_hdr} |",
        "|--------|-----|-----|----|-------------|-----------|-------------|----------------|",
    ]
    for nm, disp, fmt in factors:
        mc, ms = mom_cells.get(nm, ('—', '—'))
        yc, ys = yoy_cells.get(nm, ('—', '—'))
        lines.append(
            f"| {disp} | {fmt(cur)} | {fmt(pri)} | {fmt(lyw)} | {mc} | {ms} | {yc} | {ys} |"
        )
    lines.append(
        f"| **Paid CM1** | {fm(cur.get('cm1'))} | {fm(pri.get('cm1'))} | {fm(lyw.get('cm1'))} | "
        f"**{da(cur.get('cm1'), pri.get('cm1'))}** | — | **{da(cur.get('cm1'), lyw.get('cm1'))}** | — |"
    )
    lines.append("")
    note = (
        "*Shapley decomposition of paid CM1 = Clicks × CVR × Avg CM1; contributions sum to the total Δ. "
        "Avg CM1 (CM1/conv) absorbs AOV × TR × CR — if it leads, value-per-conversion (take rate / mix) moved, not volume.*"
    )
    if mom_flat or yoy_flat:
        note += (
            "\n*\\* Net ≈ flat block (large offsetting drivers): Share shows share of gross movement "
            "(÷ Σ|contributions|), not share of Δ.*"
        )
    lines.append(note)
    return "\n".join(lines)


# ============================================================================
# PRODUCT MIX — TGID / EXPERIENCE (Section 4 — assortment shift)
# ============================================================================

def render_tgid_table(tgid):
    # type: (Optional[Dict]) -> str
    """Render the top-experiences (TGID) revenue + assortment-shift table."""
    if not tgid or not tgid.get("rows"):
        return "*Product mix (TGID) data unavailable.*"
    rows = tgid["rows"]

    out = [
        "| TGID | Experience | L4W Rev | Share | LY Rev | LY Share | Δ Share | Orders | AOV | CR | TR | Net Rev/Ord | CM1/Ord |",
        "|------|-----------|---------|-------|--------|----------|---------|--------|-----|----|----|-------------|---------| ",
    ]
    for r in rows:
        name = r["experience_name"]
        if len(name) > 30:
            name = name[:29] + "…"
        tag = ""
        if r.get("is_new"):
            tag = " \U0001f195"          # new hero this year
        elif r.get("is_dropped"):
            tag = " ⚠️"        # dropped vs LY
        ds = r.get("delta_share") or 0.0
        ds_s = f"{ds:+.1f}pp" if abs(ds) >= 0.05 else "~0pp"
        out.append(
            f"| {r['tgid']} | {name}{tag} | {fm(r['l4w_rev'])} | {fp1(r['l4w_share'])} | "
            f"{fm(r['ly_rev'])} | {fp1(r['ly_share'])} | {ds_s} | {fi(r.get('orders'))} | "
            f"{fd(r['aov'])} | {fp1(r['cr'])} | {fp1(r['tr'])} | "
            f"{fd(r.get('net_rev_per_order'))} | {fd(r.get('cm1_per_order'))} |"
        )

    footer = (
        f"\n*Top experiences by L4W net revenue (+ any LY ≥5%-share product that decayed). "
        f"Catalogue breadth: {tgid.get('n_l4w', 0)} TGIDs L4W vs {tgid.get('n_ly', 0)} LY. "
        f"Δ Share = L4W share − LY share (the assortment-shift signal). "
        f"Net Rev/Ord = net revenue per order (AOV × CR × TR, Headout's take); "
        f"CM1/Ord = (net revenue − direct costs) / order (true per-order margin). "
        f"Source: `fct_orders.experience_id`, net revenue.*"
    )
    return "\n".join(out) + footer


def render_campaign_product_mix(campaign_product, top_n=15):
    # type: (Optional[Dict], int) -> str
    """Render the paid campaign × product (TGID) join — which campaign sells what.

    Summary mini-table (top_n pairs by net revenue) for the report; the full
    matrix lives in the Google Sheet (Tab 7).
    """
    if not campaign_product or not campaign_product.get("rows"):
        return "*Campaign × product data unavailable.*"
    rows = campaign_product["rows"]

    out = [
        "| Campaign | Channel | Product (TGID) | Orders | Net Rev | Share | AOV | TR | CM1/Ord |",
        "|----------|---------|----------------|--------|---------|-------|-----|----|---------|",
    ]
    for r in rows:
        camp = r.get("campaign_name") or "(no campaign)"
        # Strip the common "Paris - " / market prefix noise and trim for scanability.
        camp = camp.replace(" - All - Search - All", "").replace(" - Search - All", "")
        if len(camp) > 34:
            camp = camp[:33] + "…"
        name = r.get("experience_name") or "(unknown)"
        if len(name) > 24:
            name = name[:23] + "…"
        prod = f"{r.get('tgid')} {name}"
        out.append(
            f"| {camp} | {r.get('channel', '—')} | {prod} | {fi(r.get('orders'))} | "
            f"{fm(r.get('net_rev'))} | {fp1(r.get('share'))} | {fd(r.get('aov'))} | "
            f"{fp1(r.get('tr'))} | {fd(r.get('cm1_per_order'))} |"
        )

    n_all = len(campaign_product.get("all", rows))
    footer = (
        f"\n*Top {len(rows)} paid (campaign × product) pairs by L4W net revenue "
        f"({n_all} pairs total — full matrix in Google Sheet Tab 7). "
        f"Paid scope only (Google/Bing campaign-attributed orders). "
        f"Margin from `fct_orders`: TR = net rev / GMV-completed; CM1/Ord = "
        f"(net rev − direct costs) / order. Spend is campaign-level only, so ROI "
        f"can't split by product — TR/CM1 are the per-product margin read.*"
    )
    return "\n".join(out) + footer


# ============================================================================
# FUNNEL (Section 5)
# ============================================================================

def render_funnel(funnel_data):
    # type: (Optional[Dict]) -> str
    if not funnel_data:
        return ""
    l = funnel_data.get("l4w") or {}
    p = funnel_data.get("p4w") or {}
    y = funnel_data.get("ly") or {}
    if not l:
        return ""

    def rate(num, den):
        # type: (float, float) -> Optional[float]
        return num / den * 100 if den else None

    stages = []
    for label, vals in [("L4W", l), ("P4W", p), ("LY", y)]:
        lp = _g(vals, "lp", 0)
        s = _g(vals, "s", 0)
        c = _g(vals, "c", 0)
        o = _g(vals, "o", 0)
        stages.append({"lp": lp, "s": s, "c": c, "o": o,
                        "lp2s": rate(s, lp), "s2c": rate(c, s), "c2o": rate(o, c)})
    lw, pw, yw = stages

    rows = [
        "| Stage | L4W | P4W | LY | \u0394 LY (pp) | \u0394 P4W (pp) |",
        "|-------|-----|-----|----|-----------|-----------| ",
        f"| LP Sessions | {fi(lw['lp'])} | {fi(pw['lp'])} | {fi(yw['lp'])} | {dp(lw['lp'], yw['lp'])} | {dp(lw['lp'], pw['lp'])} |",
        f"| LP2S | {fp1(lw['lp2s'])} | {fp1(pw['lp2s'])} | {fp1(yw['lp2s'])} | {dpp(lw['lp2s'], yw['lp2s'])} | {dpp(lw['lp2s'], pw['lp2s'])} |",
        f"| S2C | {fp1(lw['s2c'])} | {fp1(pw['s2c'])} | {fp1(yw['s2c'])} | {dpp(lw['s2c'], yw['s2c'])} | {dpp(lw['s2c'], pw['s2c'])} |",
        f"| C2O | {fp1(lw['c2o'])} | {fp1(pw['c2o'])} | {fp1(yw['c2o'])} | {dpp(lw['c2o'], yw['c2o'])} | {dpp(lw['c2o'], pw['c2o'])} |",
    ]
    return "\n".join(rows)


# ============================================================================
# LANDING PAGE TABLE
# ============================================================================


def render_lp_funnel_table(lp_funnel, top_n=8):
    # type: (Optional[List], int) -> str
    """On-site funnel per LP from mixpanel_user_page_funnel_progression."""
    if not lp_funnel:
        return "*LP funnel data unavailable.*"
    rows = [r for r in lp_funnel if r.get("l4w_users", 0) >= 500]
    if not rows:
        return "*No LPs with >= 500 users in L4W.*"
    rows = rows[:top_n]

    lines = [
        "| Page URL | Users | CVR | LP2S | S2C | C2O | \u0394 LP2S | \u0394 S2C | \u0394 C2O |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        url = r.get("page_url", "")
        if len(url) > 50:
            url = "..." + url.split(".com", 1)[-1] if ".com" in url else url[:47] + "..."
        users = r.get("l4w_users", 0)
        u_str = "{:.1f}K".format(users / 1000) if users >= 1000 else str(users)
        cvr = r.get("l4w_cvr")
        lp2s = r.get("l4w_lp2s")
        s2c = r.get("l4w_s2c")
        c2o = r.get("l4w_c2o")
        ly_lp2s = r.get("ly_lp2s")
        ly_s2c = r.get("ly_s2c")
        ly_c2o = r.get("ly_c2o")

        def _fp(v):
            return "{:.1f}%".format(v) if v is not None else "\u2014"

        def _dp(a, b):
            if a is not None and b is not None and b > 0:
                return "{:+.1f}pp".format(a - b)
            return "\u2014"

        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                url, u_str, _fp(cvr), _fp(lp2s), _fp(s2c), _fp(c2o),
                _dp(lp2s, ly_lp2s), _dp(s2c, ly_s2c), _dp(c2o, ly_c2o),
            )
        )
    return "\n".join(lines)


def render_landing_page_table(landing_pages):
    # type: (Optional[Dict]) -> str
    if not landing_pages:
        return "*Landing page data unavailable.*"
    l4w = landing_pages.get("l4w") or []
    ly = landing_pages.get("ly") or []
    if not l4w:
        return "*No landing page data for L4W.*"

    ly_map = {r.get("final_url"): r for r in ly}

    rows = [
        "| Landing Page | CTR | Clicks (\u0394 LY) | CPC |",
        "|-------------|-----|----------------|-----|",
    ]
    for r in l4w:
        url = r.get("final_url") or ""
        if len(url) > 60:
            url = url[:57] + "..."
        ly_r = ly_map.get(r.get("final_url"), {})

        click_str = fi(_g(r, "clicks"))
        if ly_r:
            click_str += f" ({dp(_g(r,'clicks'), _g(ly_r,'clicks'))})"

        rows.append(
            f"| {url} | {fp1(_g(r,'ctr'))} | {click_str} | {fd(_g(r,'cpc'))} |"
        )
    return "\n".join(rows)


# ============================================================================
# CAMPAIGN TARGETING TABLE (Appendix A7)
# ============================================================================

def render_campaign_targeting(targeting):
    # type: (Optional[List]) -> str
    if not targeting:
        return "<!-- NARRATIVE: Claude fills campaign targeting config after reviewing data. -->"
    rows = [
        "| Campaign | Language | Location | Budget | Strategy | tROAS |",
        "|----------|----------|----------|--------|----------|-------|",
    ]
    for t in targeting:
        name = (t.get("campaign_name") or "")[:50]
        rows.append(
            f"| {name} | {t.get('language') or '\u2014'} | "
            f"{t.get('targeting_location') or '\u2014'} | "
            f"{fd(_g(t,'daily_budget')) if _g(t,'daily_budget') else '\u2014'} | "
            f"{t.get('bidding_strategy') or '\u2014'} | "
            f"{fp1(_g(t,'target_roas')) if _g(t,'target_roas') else '\u2014'} |"
        )
    return "\n".join(rows)


# ============================================================================
# AD GROUP COVERAGE TABLE
# ============================================================================

def render_ad_group_table(ad_groups):
    # type: (Optional[List]) -> str
    if not ad_groups:
        return "*Ad group data unavailable.*"

    type_lang = {}  # type: Dict[str, Dict[str, Dict]]
    for ag in ad_groups:
        name = ag.get("ad_group_name") or ""
        parts = name.split(" - ")
        ag_type = parts[0].strip() if parts else "Unknown"
        lang = parts[2].strip() if len(parts) > 2 else "Unknown"

        key = ag_type
        if key not in type_lang:
            type_lang[key] = {}
        if lang not in type_lang[key]:
            type_lang[key][lang] = {"clicks": 0, "spend": 0, "conv": 0, "cm1": 0, "ag_count": 0}
        d = type_lang[key][lang]
        d["clicks"] += ag.get("clicks", 0)
        d["spend"] += ag.get("spend", 0)
        d["conv"] += ag.get("conversions", 0)
        d["cm1"] += ag.get("cm1", 0)
        d["ag_count"] += 1

    # Aggregate by type
    type_totals = {}
    for ag_type, langs in type_lang.items():
        t = {"clicks": 0, "spend": 0, "conv": 0, "cm1": 0, "ag_count": 0, "languages": []}
        for lang, d in sorted(langs.items(), key=lambda x: x[1]["clicks"], reverse=True):
            t["clicks"] += d["clicks"]
            t["spend"] += d["spend"]
            t["conv"] += d["conv"]
            t["cm1"] += d["cm1"]
            t["ag_count"] += d["ag_count"]
            if d["clicks"] > 0:
                t["languages"].append(lang)
        type_totals[ag_type] = t

    rows = [
        "**Ad Group Coverage**",
        "",
        "| Ad Group Type | Ad Groups | Languages | Clicks | Spend | CVR | CPC | ROI |",
        "|---------------|-----------|-----------|--------|-------|-----|-----|-----|",
    ]
    for ag_type, t in sorted(type_totals.items(), key=lambda x: x[1]["clicks"], reverse=True):
        if t["clicks"] == 0:
            continue
        cl = t["clicks"]
        sp = t["spend"]
        cv = t["conv"]
        cm1 = t["cm1"]
        langs = ", ".join(t["languages"][:5])
        if len(t["languages"]) > 5:
            langs += f" +{len(t['languages'])-5}"
        cvr = f"{cv/cl*100:.1f}%" if cl else "\u2014"
        cpc = fd(sp / cl) if cl else "\u2014"
        roi = f"{cm1/sp*100:.0f}%" if sp else "\u2014"
        rows.append(
            f"| {ag_type} | {t['ag_count']} | {langs} | {fi(cl)} | {fm(sp)} | {cvr} | {cpc} | {roi} |"
        )
    return "\n".join(rows)


def render_ad_group_audit(ad_group_audit):
    # type: (Optional[Dict]) -> str
    """Ad-group-level audit: per-ad-group performance + bid-headroom opportunity."""
    if not ad_group_audit or not ad_group_audit.get("rows"):
        return "*Ad-group audit data unavailable.*"
    rows = ad_group_audit["rows"]

    out = [
        "| Ad Group | Type | Lang | Spend | Clicks | CVR | CPC | ROI | tROAS | vs Tgt | Flag |",
        "|----------|------|------|-------|--------|-----|-----|-----|-------|--------|------|",
    ]
    for r in rows:
        name = r.get("ad_group_name") or ""
        if len(name) > 30:
            name = name[:29] + "\u2026"
        vt = r.get("vs_target")
        vt_s = f"{vt:+.0f}pp" if vt is not None else "\u2014"
        # MoM trend inlined into Spend and ROI cells, e.g. "$19.3K (-2%)" / "135.6% (-3pp)".
        sp_s = fm(r.get("spend"))
        smp = r.get("spend_mom_pct")
        if smp is not None:
            sp_s += f" ({smp:+.0f}%)"
        roi_s = fp1(r.get("roi"))
        rmp = r.get("roi_mom_pp")
        if rmp is not None:
            roi_s += f" ({rmp:+.0f}pp)"
        out.append(
            f"| {name} | {r.get('ag_type', '\u2014')} | {r.get('language', '\u2014')} | "
            f"{sp_s} | {fi(r.get('clicks'))} | {fp1(r.get('cvr'))} | "
            f"{fd(r.get('cpc'))} | {roi_s} | {fp1(r.get('target_pct')) if r.get('target_pct') else '\u2014'} | "
            f"{vt_s} | {r.get('flag', '\u2014')} |"
        )
    footer = (
        f"\n*Top {len(rows)} ad groups by L4W spend (of {ad_group_audit.get('n_total', 0)}; "
        f"full set in Google Sheet Tab 8). Opportunity = **bid headroom vs the ad group's tROAS target** "
        f"(no impression-share at ad-group grain). **Scale** = ROI \u2265 target \u00d71.15 at material spend "
        f"(under-bid \u2014 volume left on the table); **Leak** = ROI <130% at material spend (spend at risk); "
        f"vs Tgt = actual ROI \u2212 target. Scale candidates: {ad_group_audit.get('scale_count', 0)} "
        f"({fm(ad_group_audit.get('scale_spend'))} spend) \u00b7 Leaks: {ad_group_audit.get('leak_count', 0)} "
        f"({fm(ad_group_audit.get('leak_spend'))} spend). Spend and ROI carry the **MoM \u0394 inline** "
        f"(vs P4W) \u2014 a worsening Leak reads differently from a recovering one; full MoM columns in Tab 8. "
        f"No YoY (ad-group names churn across the consolidation). Ad group \u00d7 product (experience_id) is not "
        f"available \u2014 fct_orders has no ad_group_id; the Type column is the product-intent proxy.*"
    )
    return "\n".join(out) + footer


# ============================================================================
# APPENDIX
# ============================================================================

def render_appendix(channels, cohorts, budget, targeting=None):
    # type: (Dict, Dict, List) -> str
    lines = ["## A. Evidence Appendix", ""]

    # A1: Monthly CE Health
    lines.append("### A1. Monthly CE Health (L12M)")
    monthly = channels.get("monthly") or []
    if monthly:
        lines.extend(["",
            "| Month | Revenue | Orders | ROI(1) | TR | CR | AOV |",
            "|-------|---------|--------|--------|----|----|-----|"])
        for m in monthly:
            roi = _g(m, "roi_1")
            tr = _g(m, "tr")
            cr = _g(m, "cr")
            lines.append(
                f"| {m.get('month','\u2014')} | {fm(_g(m,'revenue'))} | "
                f"{fi(_g(m,'orders'))} | "
                f"{fp1(roi * 100 if roi else None)} | "
                f"{fp1(tr * 100 if tr else None)} | "
                f"{fp1(cr * 100 if cr else None)} | "
                f"{fd(_g(m,'aov'))} |"
            )
    else:
        lines.append("*Data unavailable.*")

    # A2: Monthly Paid Performance
    lines.extend(["", "### A2. Monthly Paid Performance (L12M)"])
    if monthly:
        lines.extend(["",
            "| Month | Ad Spend | CPC | Clicks | CVR | CM1 | Paid ROI |",
            "|-------|----------|-----|--------|-----|-----|----------|"])
        for m in monthly:
            paid_roi = _g(m, "paid_roi")
            paid_cvr = _g(m, "paid_cvr")
            lines.append(
                f"| {m.get('month','\u2014')} | {fm(_g(m,'paid_spend'))} | "
                f"{fd(_g(m,'paid_cpc'))} | {fi(_g(m,'paid_clicks'))} | "
                f"{fp1(paid_cvr * 100 if paid_cvr else None)} | "
                f"{fm(_g(m,'paid_cm1'))} | "
                f"{fp1(paid_roi * 100 if paid_roi else None)} |"
            )
    else:
        lines.append("*Data unavailable.*")

    # A6: Budget/Bidding Detail (ALL campaigns — full version)
    lines.extend(["", "### A6. Budget/Bidding Detail (all campaigns)"])
    if budget:
        lines.extend(["", render_budget_table_full(budget)])
    else:
        lines.append("*Data unavailable.*")

    # A7: Campaign Targeting
    lines.extend(["", "### A7. Campaign Targeting"])
    if targeting:
        lines.extend(["", render_campaign_targeting(targeting)])
    else:
        lines.append("*Campaign targeting data unavailable.*")

    return "\n".join(lines)


def render_signals_checklist(signals):
    # type: (Optional[List[Dict]]) -> str
    """Render the coverage-gate 'Signals to Close' table (Phase 3).

    One row per engine-enumerated material mover, each with its basis, MoM recency,
    and L12M trajectory, plus an empty Disposition cell Claude must fill
    (CONFIRMED / RULED OUT / DATA GAP). This is the gate: a row that exists here
    cannot be silently dropped.
    """
    if not signals:
        return "*No material signals enumerated — all movements within thresholds.*"

    def lab(s, n):
        x = s.get("label") or ""
        return x[:n - 1] + "…" if len(x) > n else x

    high = [s for s in signals if s.get("severity_hint") == "high"]
    rest = [s for s in signals if s.get("severity_hint") != "high"]

    out = []
    # Primary: HIGH-severity movers — disposed inline with reasoning.
    out.append("**Material movers (HIGH) — dispose each inline:**")
    out.append("")
    out.append("| # | Signal | Win | Basis | MoM | L12M | Disposition |")
    out.append("|---|--------|-----|-------|-----|------|-------------|")
    if high:
        for i, s in enumerate(high, 1):
            out.append(
                f"| {i} | {lab(s, 44)} | {s.get('window','')} | {s.get('basis','')} | "
                f"{s.get('mom_recency','')} | {s.get('trajectory','')} | _(dispose)_ |"
            )
    else:
        out.append("| — | _(no HIGH-severity movers)_ | | | | | — |")

    # Secondary: everything else — terse, one-line dispositions (most RULED OUT).
    if rest:
        out.append("")
        out.append(f"**Also enumerated ({len(rest)}) — one-line disposition each (do not narrate individually):**")
        out.append("")
        out.append("| # | Signal | Basis | L12M | Disposition |")
        out.append("|---|--------|-------|------|-------------|")
        for j, s in enumerate(rest, len(high) + 1):
            out.append(f"| {j} | {lab(s, 40)} | {s.get('basis','')} | {s.get('trajectory','')} | _(dispose)_ |")
    return "\n".join(out)


def render_data_sources():
    # type: () -> str
    return """## B. Data Sources

| Source | Used For |
|--------|----------|
| combined_entity_stats | Section 2 (CE Overview), Appendix A1 |
| ads_campaign_stats | Section 4 (Paid Deep Dive), cohorts, Appendix A2-A3 |
| google_ads_pmax_asset_stats | Section 4 PMax metrics, Paid Value Shapley |
| fct_orders | Section 3 (Channel Breakdown), cohorts revenue, Section 4 Product Mix (TGID) |
| google_ads_campaign_stats | Section 5 Budget/Bidding, Cohort paid |
| google_ads_campaign_budget_stats | Section 5 Budget |
| google_ads_ad_group_geo_stats | Section 5 Geography |
| google_ads_ad_group_stats | Section 8 Ad Group Coverage |
| google_ads_campaign_page_stats | Section 4 Landing Pages |
| stg_google_ads_new__campaigns | Appendix A7 Campaign Targeting |
| /cvr-rca skill | Section 7 Funnel (calls CVR-RCA, reads summary.json) |
| Ahrefs | Section 6a Demand (if available) |
| Search terms CSV | Section 8 Clusters (if uploaded) |"""


# ============================================================================
# MAIN RENDER FUNCTION
# ============================================================================

def render_audit(
    ce_name,          # type: str
    market,           # type: str
    today,            # type: str
    l4w,              # type: Tuple[str, str]
    p4w,              # type: Tuple[str, str]
    ly,               # type: Tuple[str, str]
    lp_url,           # type: str
    ce_health,        # type: Dict
    paid_perf,        # type: Dict
    channels,         # type: Dict
    cohorts,          # type: Dict
    budget,           # type: List
    geo,              # type: Dict
    customers,        # type: List
    customers_ly=None,  # type: Optional[List]
    landing_pages=None, # type: Optional[Dict]
    lp_funnel=None,   # type: Optional[List]
    targeting=None,   # type: Optional[List]
    ad_groups=None,   # type: Optional[List]
    ad_group_audit=None,  # type: Optional[Dict]
    shapley=None,     # type: Optional[Dict]
    tgid=None,        # type: Optional[Dict]
    campaign_product=None,  # type: Optional[Dict]
    signals=None,     # type: Optional[List[Dict]]
):
    # type: (...) -> str
    """Assemble full audit skeleton with pre-formatted tables and NARRATIVE markers."""
    s = []
    s.append(render_header(ce_name, market, today, l4w, p4w, ly, lp_url))

    # Section 1: CE Overview
    # Section 1: Executive Summary (written LAST by Claude, but appears first for the reader)
    s.append("\n## 1. Executive Summary\n")
    s.append("<!-- NARRATIVE: Status (CRITICAL/WARNING/HEALTHY). Highest-confidence actions table (crisp Why column). Causal story. Channel attribution. Secondary issues. Write this section LAST after completing all other sections. -->\n")

    # Section 2: CE Overview
    s.append("\n---\n\n## 2. CE Overview\n")
    s.append(render_table1(ce_health))
    s.append("\n<!-- NARRATIVE: What does Table 1 tell us? ROI trend, revenue trajectory. Connect to channel breakdown. -->\n")

    # Section 3: Channel Breakdown
    s.append("\n---\n\n## 3. Channel Breakdown\n")
    s.append(render_table3(channels))
    s.append("\n<!-- NARRATIVE: Which channel drove the delta? Revenue mix shift. L12M trajectory. -->\n")

    # Section 4: Paid Deep Dive (Search + PMax + Bing)
    s.append("\n---\n\n## 4. Paid Deep Dive\n")
    s.append("\n### Paid Value Decomposition (Clicks × CVR × Avg CM1)\n")
    s.append(render_paid_shapley(shapley))
    s.append("\n<!-- NARRATIVE: Lead with the dominant driver from the Shapley (the factor with the largest |contribution|). "
             "State it in the driver order clicks → avg CM1 → CVR. e.g. 'Paid CM1 fell $Xk MoM — clicks drove ~Y% (volume), "
             "avg CM1 drove ~Z% (value/conv). CVR was immaterial.' Do NOT narrate a CVR story if CVR's share is small. "
             "If avg CM1 is the lead driver, route to the TR/CR + product-mix (TGID) tables below. -->\n")
    s.append("\n" + render_table2(paid_perf))
    s.append("\n<!-- NARRATIVE: Paid performance story. CPC justified by RPC? Efficiency trend. PMax contribution. -->\n")
    if landing_pages and len(landing_pages.get("l4w", [])) > 1:
        s.append("\n### Landing Pages — Ad Performance\n")
        s.append(render_landing_page_table(landing_pages))
        s.append("\n*Source: Google Ads.*\n")
    if lp_funnel:
        s.append("\n### Landing Pages — On-Site Funnel\n")
        s.append(render_lp_funnel_table(lp_funnel))
        s.append("\n*Source: `mixpanel_user_page_funnel_progression`, unique users (matches Omni). Mixpanel collapses language variants into root URL. Full dump in Google Sheet Tab 6.*\n")
    s.append("\n<!-- NARRATIVE: Ad LP CTR by language. On-site funnel: which stage leaks, which pages, product-level vs page-specific. Mobile vs desktop S2C gap if >5pp. -->\n")
    s.append("\n### Product Mix — Top Experiences (TGID)\n")
    s.append(render_tgid_table(tgid))
    s.append("\n<!-- NARRATIVE: Did the product mix shift? Flag any TGID with |Δ Share| > 5pp. A new hero (🆕) or a decayed/dropped product (⚠️) "
             "means revenue/CVR/RPC moved because of assortment, not funnel or traffic quality. Connect to the avg CM1 driver above: "
             "if a low-TR or low-AOV product grew share, that drags blended avg CM1 → constrains bidding. Route lost heroes to Supply, "
             "new low-economics products to Product/pricing. If mix is stable (all |Δ Share| < 5pp), say 'product mix stable' and move on. -->\n")
    if campaign_product and campaign_product.get("rows"):
        s.append("\n### Campaign × Product — Which Campaign Sells What (paid)\n")
        # Table is backend reference only (full matrix lives in Google Sheet Tab 7).
        # The report shows the *insight*, not the table — keep it tight.
        s.append("<!-- DATA (backend — do NOT render this table in the report; full matrix in Sheet Tab 7):\n"
                 + render_campaign_product_mix(campaign_product)
                 + "\n-->\n")
        s.append("\n<!-- NARRATIVE: 2-3 sentences, NO table. State only the campaign × product *insight* from the data above: "
                 "(1) any high-volume campaign concentrated in a LOW-TR product (e.g. dining ~10% vs tickets ~24%) dragging blended economics — tie to the Avg CM1 Shapley driver + TGID mix; "
                 "(2) which channel sells the hero SKU (coverage signal). Route low-margin concentrations to Product/pricing. Point to Sheet Tab 7 for the full matrix. If everything maps to healthy-TR products, say so in one line. -->\n")

    # Section 5: Coverage + Matchmaking
    s.append("\n---\n\n## 5. Coverage + Matchmaking\n")
    s.append(render_cohort_table(cohorts))
    s.append("\n<!-- NARRATIVE: Top 3 cohort driver breakdown (CVR vs AOV vs TR). Coverage gaps. L12M trajectory per cohort. -->\n")
    s.append(render_budget_table(budget))
    s.append("\n")
    s.append(render_geo_table(geo, customers, customers_ly))
    s.append("\n<!-- NARRATIVE: Geo gap analysis. Tourist context (1-2 sentences). -->\n")

    # Section 6: External Dynamics
    s.append("\n---\n\n## 6. External Dynamics\n")
    s.append("\n### 6a. Demand\n")
    s.append("<!-- NARRATIVE: Ahrefs search volume trend. L12M monthly volumes if available. -->\n")
    s.append("\n### 6b. Competition\n")
    s.append("<!-- NARRATIVE: CPC 3-lens (quality → structural → competition). Separate CPC story from SIS story.\n"
             "If auction insights CSV provided, parse and render competitor tables here. -->\n")
    s.append("\n### 6c. Money on the Table\n")
    s.append(render_money_on_table(cohorts))

    # Section 7: Funnel (via /cvr-rca)
    s.append("\n\n---\n\n## 7. Funnel\n")
    s.append("<!-- Run /cvr-rca <CE_ID> <P4W_START> <P4W_END> <L4W_START> <L4W_END>\n"
             "Read summary.json. Validate: CVR-RCA Google Ads CVR delta vs cohort table TOTAL CVR delta (Section 5).\n"
             "\n"
             "Write narrative from CVR-RCA output:\n"
             "- Shapley: which step drove the change (LP2S vs S2C vs C2O %)\n"
             "- C2O split: C2A (checkout submission) vs A2O (payment success)\n"
             "- Device: mobile vs desktop concentration\n"
             "- Top experiences by |Δrate| per significant step\n"
             "- LY gap: structural vs seasonal\n"
             "- Link CVR-RCA HTML report\n"
             "\n"
             "If CVR-RCA unavailable: use cohort CVR + SIS from Section 5. -->\n")

    # Section 8: Search Intelligence (ad group coverage + CSV cluster analysis)
    s.append("\n---\n\n## 8. Search Intelligence\n")
    if ad_groups:
        s.append("\n### Ad Group Coverage\n")
        s.append(render_ad_group_table(ad_groups))
        s.append("\n<!-- NARRATIVE: Which ad group types drive performance? Any language gaps? Cross-reference with experience archetypes if assortment data available. -->\n")
    if ad_group_audit and ad_group_audit.get("rows"):
        s.append("\n### Ad Group Audit — performance & bid headroom\n")
        s.append(render_ad_group_audit(ad_group_audit))
        s.append("\n<!-- NARRATIVE: the ad-group-level audit (the type-level coverage above is the rollup). "
                 "Lead with the opportunity: name the **Scale** ad groups (ROI well above target = the algorithm is under-bidding a profitable group — Perf can raise budget / lower tROAS to capture volume; you set the magnitude) and the **Leak** ad groups (ROI <130% at material spend — say the $ at risk and route to LP/quality/match-type or trim). "
                 "Cross-check Leaks against the §4 Campaign × Product read (a low-TR product can explain a low-ROI ad group — that's a Product call, not a paid one). "
                 "If no Scale/Leak flags, say 'ad groups are on-target' and move on. Note: ad group × product isn't available (no ad_group_id on fct_orders) — use the Type column as the intent proxy. -->\n")
    s.append("\n### Search Term Clusters\n")
    s.append("<!-- If search terms CSV uploaded:\n"
             "Cluster analysis — map search terms to clusters. Cross-reference with ad group types above.\n"
             "Flag terms with \u2265100 clicks and 0 conversions.\n"
             "Keyword volumes per cluster (from keyword planner if available).\n"
             "\n"
             "If no CSV: abbreviate — use keyword IS data from Section 5 budget table + cohort SIS only. -->\n")

    # Section 9: Red Flags \u2014 coverage gate (Signals to Close) then ranked Red Flags
    s.append("\n---\n\n## 9. Red Flags Summary\n")
    # Coverage gate = backend discipline only. Disposed inside a comment (NOT rendered
    # in the report); the visible \u00a79 is just the ranked Red Flags table.
    s.append("<!-- COVERAGE GATE (backend \u2014 do NOT render this checklist in the report). "
             "Close every signal here as CONFIRMED / RULED OUT / DATA GAP + one-line reason + \u00a7ref so "
             "nothing material is silently dropped (EVAL checks this). HIGH rows get real reasoning "
             "(DIAGNOSTICS.md \u00a70 + per-signal trees + L12M trajectory); 'Also enumerated' rows get one line each. "
             "The visible Red Flags table below is the CONFIRMED subset.\n\n"
             + render_signals_checklist(signals)
             + "\n-->\n")
    s.append("\n<!-- NARRATIVE: the ranked Red Flags table = the CONFIRMED rows from the coverage gate above, "
             "HIGH first, plus any qualitative flag (data caveats, competitor surges). "
             "Columns: | Severity | Category | Issue | Section |. Lead with the 3\u20134 HIGH conclusions; do not drown them. -->\n")

    # Section 10: Conclusions (forwardable, not bid-prescriptive)
    s.append("\n---\n\n## 10. Conclusions\n")
    s.append("<!-- NARRATIVE: Table | # | Conclusion (lever) | Sized Opportunity | Owner | Constraint / why | Evidence |. "
             "Every row carries a lever + $ size + owner + constraint \u2014 forwardable. Name the lever and let Perf set the magnitude; "
             "do NOT prescribe a bid/tROAS number or cut bids >5%. No vague 'monitor/investigate' rows \u2014 each has a sized lever + owner. "
             "Order by $ opportunity (largest first). -->\n")

    # Appendix
    s.append("\n---\n")
    s.append(render_appendix(channels, cohorts, budget, targeting))
    s.append("\n")
    s.append(render_data_sources())
    s.append(f"\n\n*Report skeleton generated {today} | v6.1*\n")

    return "\n".join(s)
