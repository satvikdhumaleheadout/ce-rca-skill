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
    """Active campaigns only (spend > $0) for main body."""
    if not budget:
        return "*Budget data unavailable.*"
    active = [b for b in budget if _g(b, "spend", 0) > 0]
    if not active:
        return "*No active campaigns in L4W.*"
    return "\n".join(_BUDGET_HEADER + _budget_rows(active))


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
        "| Country | Ad Clicks (\u0394 LY) | Click Share (\u0394 LY) | Customer Share (\u0394 LY) | Gap | CPC (\u0394 LY) | Conv (\u0394 LY) |",
        "|---------|------------------|-------------------|------------------------|-----|------------|-------------|",
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
        conv_str = fi(_g(r, "conversions"))
        if ly_r and _g(ly_r, "conversions") is not None:
            conv_str += f" ({dp(_g(r,'conversions'), _g(ly_r,'conversions'))})"

        rows.append(
            f"| {country} | {click_str} | {share_str} | "
            f"{cust_str} | "
            f"{f'{gap:+.1f}pp' if gap is not None else '\u2014'} | "
            f"{cpc_str} | {conv_str} |"
        )
    return "\n".join(rows)


# ============================================================================
# MONEY ON THE TABLE (Section 4c-iii)
# ============================================================================

def render_money_on_table(cohorts):
    # type: (Dict) -> str
    tw = cohorts.get("tw") or []
    if not tw:
        return "*Money on the Table data unavailable.*"

    largest = max(tw, key=lambda c: _g(c, "cm1", 0))
    total_cm1 = sum(_g(c, "cm1", 0) for c in tw)
    cm1_pct = _g(largest, "cm1", 0) / total_cm1 * 100 if total_cm1 else 0

    cohort_name = _cohort_display(largest.get("cohort", "Unknown"))
    sis = _g(largest, "avg_sis")
    rank_lost = _g(largest, "avg_rank_lost", 0) * 100
    budget_lost = _g(largest, "avg_budget_lost", 0) * 100
    impressions = _g(largest, "impressions", 0)
    clicks = _g(largest, "clicks", 0)
    rpc = _g(largest, "rpc")

    if not sis or not impressions:
        return "*Money on the Table: SIS data unavailable.*"

    eligible = impressions / (sis / 100)
    rank_lost_searches = eligible * (rank_lost / 100) if rank_lost else 0
    ctr_raw = clicks / impressions if impressions else 0
    sis_int = round(sis)
    gap_to_50 = max(50 - sis_int, 1)

    def scenario(pp):
        # type: (int) -> Tuple[int, int]
        add_impr = eligible * pp / 100
        add_cl = int(round(add_impr * ctr_raw))
        add_rev = int(round(add_cl * rpc)) if rpc else 0
        return add_cl, add_rev

    cl_10, rev_10 = scenario(10)
    cl_50, rev_50 = scenario(gap_to_50)
    cl_1, rev_1 = scenario(1)

    constraint = "budget" if budget_lost > rank_lost else "rank"
    other = "rank" if constraint == "budget" else "budget"

    lines = [
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
        f"At current RPC ({fd(rpc)}), every 1pp of SIS gained = ~{fi(cl_1)} clicks = ~${fi(rev_1)}/L4W.",
        f"The constraint is **{constraint}, not {other}** ({budget_lost:.0f}% budget-lost).",
    ]
    return "\n".join(lines)


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

    # A3: Monthly SIS/CPC/Clicks trend from cohort monthly
    lines.extend(["", "### A3. Monthly Paid Metrics Trend"])
    cohort_monthly = cohorts.get("monthly") or []
    if cohort_monthly:
        month_agg = {}  # type: Dict[str, Dict[str, float]]
        for r in cohort_monthly:
            mo = r.get("month")
            if mo not in month_agg:
                month_agg[mo] = {"spend": 0, "clicks": 0, "cm1": 0}
            month_agg[mo]["spend"] += _g(r, "spend", 0)
            month_agg[mo]["clicks"] += _g(r, "clicks", 0)
            month_agg[mo]["cm1"] += _g(r, "cm1", 0)

        lines.extend(["",
            "| Month | CPC | Clicks | ROI |",
            "|-------|-----|--------|-----|"])
        for mo in sorted(month_agg.keys()):
            a = month_agg[mo]
            cpc = a["spend"] / a["clicks"] if a["clicks"] else None
            roi = a["cm1"] / a["spend"] * 100 if a["spend"] else None
            lines.append(f"| {mo} | {fd(cpc)} | {fi(a['clicks'])} | {fp1(roi)} |")
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


def render_data_sources():
    # type: () -> str
    return """## B. Data Sources

| Source | Used For |
|--------|----------|
| combined_entity_stats | Section 2 (CE Overview), Appendix A1 |
| ads_campaign_stats | Section 4 (Paid Deep Dive), cohorts, Appendix A2-A3 |
| google_ads_pmax_asset_stats | Section 4 PMax metrics |
| fct_orders | Section 3 (Channel Breakdown), cohorts revenue |
| google_ads_campaign_stats | Section 5 Budget/Bidding, Cohort paid |
| google_ads_campaign_budget_stats | Section 5 Budget |
| google_ads_ad_group_geo_stats | Section 5 Geography |
| google_ads_ad_group_stats | Section 8 Ad Group Coverage |
| google_ads_campaign_page_stats | Section 4 Landing Pages |
| stg_google_ads_new__campaigns | Appendix A7 Campaign Targeting |
| mixpanel_user_funnel_progression | Section 7 Funnel (Claude queries) |
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
    funnel=None,      # type: Optional[Dict]
    customers_ly=None,  # type: Optional[List]
    landing_pages=None, # type: Optional[Dict]
    targeting=None,   # type: Optional[List]
    ad_groups=None,   # type: Optional[List]
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
    s.append(render_table2(paid_perf))
    s.append("\n<!-- NARRATIVE: Paid performance story. CPC justified by RPC? Efficiency trend. PMax contribution. -->\n")
    if landing_pages and len(landing_pages.get("l4w", [])) > 1:
        s.append("\n### Landing Pages\n")
        s.append(render_landing_page_table(landing_pages))
        s.append("\n<!-- NARRATIVE: CTR comparison across landing pages. Dedicated LP vs generic — is there merit? -->\n")

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

    # Section 7: Funnel
    s.append("\n\n---\n\n## 7. Funnel\n")
    if funnel:
        s.append(render_funnel(funnel))
    else:
        s.append("<!-- Run funnel query: BQ mixpanel_user_funnel_progression for L4W/P4W/LY, paid-filtered. -->\n")
    s.append("\n<!-- NARRATIVE: Which stage leaks? Accelerating or recovering? Size the impact. Route to owner. -->\n")

    # Section 8: Search Intelligence (ad group coverage + CSV cluster analysis)
    s.append("\n---\n\n## 8. Search Intelligence\n")
    if ad_groups:
        s.append("\n### Ad Group Coverage\n")
        s.append(render_ad_group_table(ad_groups))
        s.append("\n<!-- NARRATIVE: Which ad group types drive performance? Any language gaps? Cross-reference with experience archetypes if assortment data available. -->\n")
    s.append("\n### Search Term Clusters\n")
    s.append("<!-- If search terms CSV uploaded:\n"
             "Cluster analysis — map search terms to clusters. Cross-reference with ad group types above.\n"
             "Flag terms with \u2265100 clicks and 0 conversions.\n"
             "Keyword volumes per cluster (from keyword planner if available).\n"
             "\n"
             "If no CSV: abbreviate — use keyword IS data from Section 5 budget table + cohort SIS only. -->\n")

    # Section 9: Red Flags
    s.append("\n---\n\n## 9. Red Flags Summary\n")
    s.append("<!-- NARRATIVE: Consolidated table \u2014 | Severity | Category | Issue | Section | -->\n")

    # Section 10: Actions
    s.append("\n---\n\n## 10. Recommended Actions\n")
    s.append("<!-- NARRATIVE: | # | Action | Owner | Est. Impact | Timeline | Evidence | \u2014 Specific, sized, owned, timed. Crisp. -->\n")

    # Appendix
    s.append("\n---\n")
    s.append(render_appendix(channels, cohorts, budget, targeting))
    s.append("\n")
    s.append(render_data_sources())
    s.append(f"\n\n*Report skeleton generated {today} | v6.1*\n")

    return "\n".join(s)
