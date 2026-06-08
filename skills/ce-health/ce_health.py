#!/usr/bin/env python3
"""
CE Health Briefing Packet — everything you need to know about a CE before
starting any depth analysis (perf audit, weekly review, etc.).

Usage:
    python3 scripts/ce_health.py --ce-id 252 --range week
    python3 scripts/ce_health.py --ce-id 252 --range month
    python3 scripts/ce_health.py --ce-id 252 --range 3m
    python3 scripts/ce_health.py --ce-id 252 --range 6m
    python3 scripts/ce_health.py --ce-id 252 --start 2026-03-06 --end 2026-04-05
    python3 scripts/ce_health.py --ce-id 252 --range week --output thoughts/shared/ce-health/louvre-2026-05-29.md

Python 3.9 compatible.
"""
from __future__ import annotations

import argparse
import glob as glob_mod
import itertools
import json
import math
import os
import sys
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

_repo_root = os.path.dirname(os.path.abspath(__file__))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from engine.sources.bq import (
    run_bq_query,
    fetch_ce_health,
    _fetch_channel_window_v2,
    _fetch_monthly_summary,
    fetch_customer_country_distribution,
    fetch_lp_funnel,
    PROJECT_ID,
    DATASET,
)
from engine.render.audit_skeleton import (
    fm, fp, fp1, fd, fi, dp, da, dpp, _g,
)


# ============================================================================
# DATE HELPERS
# ============================================================================

def _last_day_of_month(year, month):
    # type: (int, int) -> date
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


def _month_offset(year, month, delta):
    # type: (int, int, int) -> Tuple[int, int]
    m = month + delta
    y = year
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return (y, m)


def _seq_label(days):
    # type: (int) -> str
    if 5 <= days <= 9:
        return "WoW"
    if 25 <= days <= 35:
        return "MoM"
    if 85 <= days <= 95:
        return "QoQ"
    if 175 <= days <= 190:
        return "HoH"
    return "vs Prior"


def _date_label(start, end):
    # type: (date, date) -> str
    if start.year == end.year:
        return "{} - {}".format(start.strftime("%b %d"), end.strftime("%b %d, %Y"))
    return "{} - {}".format(start.strftime("%b %d, %Y"), end.strftime("%b %d, %Y"))


def _parse_range(range_str):
    # type: (str) -> Tuple[int, str]
    """Parse 'l4w', 'l2m', 'week', 'month', '3m', '6m' into (count, unit).
    Returns (N, 'w'|'m').
    """
    import re
    s = range_str.lower().strip()
    aliases = {"week": "l1w", "month": "l1m"}
    s = aliases.get(s, s)
    old_style = re.match(r'^(\d+)m$', s)
    if old_style:
        s = "l{}m".format(old_style.group(1))
    m = re.match(r'^l(\d+)(w|m)$', s)
    if not m:
        raise ValueError("Invalid range '{}'. Use l<N>w (weeks) or l<N>m (months). Examples: l4w, l2m, l1w".format(range_str))
    return int(m.group(1)), m.group(2)


def _build_result(cur_s, cur_e, pri_s, pri_e, ly_cur_s, ly_cur_e, ly_pri_s, ly_pri_e,
                  col_cur, col_pri, seq, range_str):
    # type: (date, date, date, date, date, date, date, date, str, str, str, str) -> Dict[str, Any]
    return {
        "current": (cur_s, cur_e),
        "prior": (pri_s, pri_e),
        "ly_current": (ly_cur_s, ly_cur_e),
        "ly_prior": (ly_pri_s, ly_pri_e),
        "cur_label": _date_label(cur_s, cur_e),
        "pri_label": _date_label(pri_s, pri_e),
        "ly_cur_label": _date_label(ly_cur_s, ly_cur_e),
        "ly_pri_label": _date_label(ly_pri_s, ly_pri_e),
        "col_cur": col_cur,
        "col_pri": col_pri,
        "col_ly_cur": "LY " + col_cur,
        "col_ly_pri": "LY " + col_pri,
        "seq_label": seq,
        "range": range_str,
    }


def compute_windows(range_str=None, start=None, end=None):
    # type: (Optional[str], Optional[date], Optional[date]) -> Dict[str, Any]
    """Compute 4 comparison windows from a range spec or custom dates.

    Supports:
      l<N>w  — last N complete weeks (Mon-Sun). E.g. l1w, l4w, l8w
      l<N>m  — last N complete months. E.g. l1m, l3m, l6m
      week   — alias for l1w
      month  — alias for l1m
      3m/6m  — aliases for l3m/l6m
      --start/--end — custom date range
    """
    today = date.today()

    # Custom date range
    if start and end:
        cur_start, cur_end = start, end
        span = (cur_end - cur_start).days + 1
        prior_end = cur_start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=span - 1)
        ly_cur_start = date(cur_start.year - 1, cur_start.month, cur_start.day)
        ly_cur_end = date(cur_end.year - 1, cur_end.month, cur_end.day)
        ly_prior_end = ly_cur_start - timedelta(days=1)
        ly_prior_start = ly_prior_end - timedelta(days=span - 1)
        seq = _seq_label(span)
        prefix_cur = "{}-{}".format(cur_start.strftime("%b%d"), cur_end.strftime("%b%d"))
        prefix_pri = "{}-{}".format(prior_start.strftime("%b%d"), prior_end.strftime("%b%d"))
        return _build_result(
            cur_start, cur_end, prior_start, prior_end,
            ly_cur_start, ly_cur_end, ly_prior_start, ly_prior_end,
            prefix_cur, prefix_pri, seq, "custom")

    n, unit = _parse_range(range_str)

    if unit == "w":
        # Last N complete Mon-Sun weeks
        cur_end = today - timedelta(days=today.weekday() + 1)  # last Sunday
        cur_start = cur_end - timedelta(days=n * 7 - 1)
        prior_end = cur_start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=n * 7 - 1)
        ly_cur_start = cur_start - timedelta(days=364)
        ly_cur_end = cur_end - timedelta(days=364)
        ly_prior_start = prior_start - timedelta(days=364)
        ly_prior_end = prior_end - timedelta(days=364)
        if n == 1:
            col_cur, col_pri, seq = "TW", "LW", "WoW"
        else:
            col_cur = "L{}W".format(n)
            col_pri = "P{}W".format(n)
            seq = "WoW" if n <= 2 else "vs Prior"
        return _build_result(
            cur_start, cur_end, prior_start, prior_end,
            ly_cur_start, ly_cur_end, ly_prior_start, ly_prior_end,
            col_cur, col_pri, seq, range_str)

    # unit == "m"
    cur_end = date(today.year, today.month, 1) - timedelta(days=1)
    cy, cm = _month_offset(cur_end.year, cur_end.month, -(n - 1))
    cur_start = date(cy, cm, 1)
    prior_end = cur_start - timedelta(days=1)
    py, pm = _month_offset(prior_end.year, prior_end.month, -(n - 1))
    prior_start = date(py, pm, 1)
    lysy, lysm = _month_offset(cur_start.year, cur_start.month, -12)
    ly_cur_start = date(lysy, lysm, 1)
    lyey, lyem = _month_offset(cur_end.year, cur_end.month, -12)
    ly_cur_end = _last_day_of_month(lyey, lyem)
    lypsy, lypsm = _month_offset(prior_start.year, prior_start.month, -12)
    ly_prior_start = date(lypsy, lypsm, 1)
    lypey, lypem = _month_offset(prior_end.year, prior_end.month, -12)
    ly_prior_end = _last_day_of_month(lypey, lypem)
    if n == 1:
        col_cur, col_pri, seq = "TM", "LM", "MoM"
    elif n == 3:
        col_cur, col_pri, seq = "L3M", "P3M", "QoQ"
    elif n == 6:
        col_cur, col_pri, seq = "L6M", "P6M", "HoH"
    else:
        col_cur = "L{}M".format(n)
        col_pri = "P{}M".format(n)
        seq = "MoM" if n <= 2 else "vs Prior"
    return _build_result(
        cur_start, cur_end, prior_start, prior_end,
        ly_cur_start, ly_cur_end, ly_prior_start, ly_prior_end,
        col_cur, col_pri, seq, range_str)


# ============================================================================
# BQ QUERIES (NEW)
# ============================================================================

def fetch_ce_metadata(ce_id):
    # type: (int) -> Dict[str, Any]
    query = """
    SELECT
        combined_entity_id,
        combined_entity_name,
        market,
        country,
        region,
        combined_entity_category,
        combined_entity_subcategory,
        evolution_bucket,
        management_type,
        is_existing,
        headout_status
    FROM `{project}.{dataset}.dim_combined_entities`
    WHERE combined_entity_id = '{ce_id}'
    LIMIT 1
    """.format(project=PROJECT_ID, dataset=DATASET, ce_id=ce_id)
    rows = run_bq_query(query)
    if not rows:
        return {}
    return rows[0]


def fetch_ce_funnel(ce_id, start, end):
    # type: (int, date, date) -> Dict[str, Any]
    query = """
    SELECT
        COUNT(DISTINCT user_id) AS lp_viewers,
        COUNT(DISTINCT IF(has_select_page_viewed, user_id, NULL)) AS select_viewers,
        COUNT(DISTINCT IF(has_checkout_started, user_id, NULL)) AS checkout_starters,
        COUNT(DISTINCT IF(has_order_completed, user_id, NULL)) AS order_completers
    FROM `{project}.{dataset}.mixpanel_user_funnel_progression`
    WHERE combined_entity_id = '{ce_id}'
        AND session_date BETWEEN '{start}' AND '{end}'
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
    )
    rows = run_bq_query(query)
    if not rows or not rows[0].get("lp_viewers"):
        return {}
    r = rows[0]
    lp = int(r.get("lp_viewers") or 0)
    sel = int(r.get("select_viewers") or 0)
    chk = int(r.get("checkout_starters") or 0)
    ord_ = int(r.get("order_completers") or 0)
    return {
        "lp_viewers": lp,
        "select_viewers": sel,
        "checkout_starters": chk,
        "order_completers": ord_,
        "lp2s": sel / lp * 100 if lp else None,
        "s2c": chk / sel * 100 if sel else None,
        "c2o": ord_ / chk * 100 if chk else None,
    }


def fetch_top_tgids(ce_id, cur, pri, ly_cur, ly_pri, top_n=10):
    # type: (int, Tuple[date,date], Tuple[date,date], Tuple[date,date], Tuple[date,date], int) -> List[Dict[str, Any]]
    query = """
    WITH tgid_data AS (
        SELECT
            ord.experience_id,
            dex.experience_name,
            -- Current window
            SUM(CASE WHEN DATE(ord.created_at) BETWEEN '{c_s}' AND '{c_e}'
                THEN ord.amount_revenue_usd ELSE 0 END) AS rev_cur,
            COUNT(DISTINCT CASE WHEN DATE(ord.created_at) BETWEEN '{c_s}' AND '{c_e}'
                THEN ord.order_id END) AS orders_cur,
            SUM(CASE WHEN DATE(ord.created_at) BETWEEN '{c_s}' AND '{c_e}'
                THEN ord.order_value_usd ELSE 0 END) AS gbv_cur,
            SUM(CASE WHEN DATE(ord.created_at) BETWEEN '{c_s}' AND '{c_e}'
                AND ord.order_status = 'Completed'
                THEN ord.order_value_usd ELSE 0 END) AS completed_gbv_cur,
            -- Prior window
            SUM(CASE WHEN DATE(ord.created_at) BETWEEN '{p_s}' AND '{p_e}'
                THEN ord.amount_revenue_usd ELSE 0 END) AS rev_pri,
            COUNT(DISTINCT CASE WHEN DATE(ord.created_at) BETWEEN '{p_s}' AND '{p_e}'
                THEN ord.order_id END) AS orders_pri,
            -- LY window
            SUM(CASE WHEN DATE(ord.created_at) BETWEEN '{ly_s}' AND '{ly_e}'
                THEN ord.amount_revenue_usd ELSE 0 END) AS rev_ly,
            COUNT(DISTINCT CASE WHEN DATE(ord.created_at) BETWEEN '{ly_s}' AND '{ly_e}'
                THEN ord.order_id END) AS orders_ly,
            SUM(CASE WHEN DATE(ord.created_at) BETWEEN '{ly_s}' AND '{ly_e}'
                THEN ord.order_value_usd ELSE 0 END) AS gbv_ly,
            SUM(CASE WHEN DATE(ord.created_at) BETWEEN '{ly_s}' AND '{ly_e}'
                AND ord.order_status = 'Completed'
                THEN ord.order_value_usd ELSE 0 END) AS completed_gbv_ly,
            -- LY Prior window
            SUM(CASE WHEN DATE(ord.created_at) BETWEEN '{lyp_s}' AND '{lyp_e}'
                THEN ord.amount_revenue_usd ELSE 0 END) AS rev_ly_pri
        FROM `{project}.{dataset}.fct_orders` ord
        JOIN `{project}.{dataset}.dim_experiences` dex
            ON ord.experience_id = dex.experience_id
        WHERE ord.combined_entity_id = '{ce_id}'
            AND DATE(ord.created_at) >= '{lyp_s}'
            AND DATE(ord.created_at) <= '{c_e}'
            AND ord.order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
            AND ord.user_type = 'Customer'
        GROUP BY 1, 2
    ),
    ce_total AS (
        SELECT SUM(rev_cur) AS total_rev_cur FROM tgid_data
    ),
    ranked AS (
        SELECT
            t.*,
            -- RPC = net revenue per order (amount_revenue_usd / orders)
            SAFE_DIVIDE(t.rev_cur, t.orders_cur) AS rpc_cur,
            SAFE_DIVIDE(t.rev_ly, t.orders_ly) AS rpc_ly,
            -- AOV = gross order value per order (order_value_usd / orders)
            SAFE_DIVIDE(t.gbv_cur, t.orders_cur) AS aov_cur,
            SAFE_DIVIDE(t.gbv_ly, t.orders_ly) AS aov_ly,
            -- TR = net revenue / completed gross bookings
            SAFE_DIVIDE(t.rev_cur, NULLIF(t.completed_gbv_cur, 0)) AS tr_cur,
            SAFE_DIVIDE(t.rev_ly, NULLIF(t.completed_gbv_ly, 0)) AS tr_ly,
            -- CR = completed gross bookings / total gross bookings
            SAFE_DIVIDE(t.completed_gbv_cur, NULLIF(t.gbv_cur, 0)) AS cr_cur,
            SAFE_DIVIDE(t.completed_gbv_ly, NULLIF(t.gbv_ly, 0)) AS cr_ly,
            ROUND(SAFE_DIVIDE(t.rev_cur, ct.total_rev_cur) * 100, 1) AS rev_share_pct,
            ROW_NUMBER() OVER (ORDER BY t.rev_cur DESC) AS rn
        FROM tgid_data t
        CROSS JOIN ce_total ct
        WHERE t.rev_cur > 0 OR t.rev_ly > 0
    )
    SELECT * FROM ranked WHERE rn <= {top_n}
    ORDER BY rev_cur DESC
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
        c_s=cur[0].strftime("%Y-%m-%d"), c_e=cur[1].strftime("%Y-%m-%d"),
        p_s=pri[0].strftime("%Y-%m-%d"), p_e=pri[1].strftime("%Y-%m-%d"),
        ly_s=ly_cur[0].strftime("%Y-%m-%d"), ly_e=ly_cur[1].strftime("%Y-%m-%d"),
        lyp_s=ly_pri[0].strftime("%Y-%m-%d"), lyp_e=ly_pri[1].strftime("%Y-%m-%d"),
        top_n=top_n,
    )
    return run_bq_query(query)


# ============================================================================
# TGID FUNNEL (per-experience funnel from mixpanel)
# ============================================================================

def fetch_tgid_funnel(ce_id, cur, ly_cur):
    # type: (int, Tuple[date,date], Tuple[date,date]) -> List[Dict[str, Any]]
    query = """
    SELECT
        experience_id,
        COUNT(DISTINCT CASE WHEN session_date BETWEEN '{c_s}' AND '{c_e}'
            AND has_select_page_viewed THEN user_id END) AS select_users_cur,
        COUNT(DISTINCT CASE WHEN session_date BETWEEN '{c_s}' AND '{c_e}'
            THEN user_id END) AS total_users_cur,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN session_date BETWEEN '{c_s}' AND '{c_e}'
                AND has_checkout_started THEN user_id END),
            NULLIF(COUNT(DISTINCT CASE WHEN session_date BETWEEN '{c_s}' AND '{c_e}'
                AND has_select_page_viewed THEN user_id END), 0)
        ) AS s2c_cur,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN session_date BETWEEN '{c_s}' AND '{c_e}'
                AND has_order_completed THEN user_id END),
            NULLIF(COUNT(DISTINCT CASE WHEN session_date BETWEEN '{c_s}' AND '{c_e}'
                AND has_checkout_started THEN user_id END), 0)
        ) AS c2o_cur,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN session_date BETWEEN '{c_s}' AND '{c_e}'
                AND has_checkout_started THEN user_id END),
            NULLIF(COUNT(DISTINCT CASE WHEN session_date BETWEEN '{c_s}' AND '{c_e}'
                THEN user_id END), 0)
        ) AS s2o_cur,
        COUNT(DISTINCT CASE WHEN session_date BETWEEN '{ly_s}' AND '{ly_e}'
            AND has_select_page_viewed THEN user_id END) AS select_users_ly,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN session_date BETWEEN '{ly_s}' AND '{ly_e}'
                AND has_checkout_started THEN user_id END),
            NULLIF(COUNT(DISTINCT CASE WHEN session_date BETWEEN '{ly_s}' AND '{ly_e}'
                AND has_select_page_viewed THEN user_id END), 0)
        ) AS s2c_ly,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN session_date BETWEEN '{ly_s}' AND '{ly_e}'
                AND has_order_completed THEN user_id END),
            NULLIF(COUNT(DISTINCT CASE WHEN session_date BETWEEN '{ly_s}' AND '{ly_e}'
                AND has_checkout_started THEN user_id END), 0)
        ) AS c2o_ly
    FROM `{project}.{dataset}.mixpanel_user_funnel_progression`
    WHERE combined_entity_id = '{ce_id}'
        AND (session_date BETWEEN '{c_s}' AND '{c_e}'
             OR session_date BETWEEN '{ly_s}' AND '{ly_e}')
    GROUP BY 1
    HAVING COUNT(DISTINCT CASE WHEN session_date BETWEEN '{c_s}' AND '{c_e}'
        AND has_select_page_viewed THEN user_id END) > 0
    ORDER BY select_users_cur DESC
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
        c_s=cur[0].strftime("%Y-%m-%d"), c_e=cur[1].strftime("%Y-%m-%d"),
        ly_s=ly_cur[0].strftime("%Y-%m-%d"), ly_e=ly_cur[1].strftime("%Y-%m-%d"),
    )
    return run_bq_query(query)


# ============================================================================
# LEAD TIME COHORTS
# ============================================================================

def fetch_tgid_lead_time(ce_id, cur, ly_cur):
    # type: (int, Tuple[date,date], Tuple[date,date]) -> List[Dict[str, Any]]
    query = """
    WITH bookings AS (
        SELECT
            CAST(b.experience_id AS STRING) AS experience_id,
            CASE
                WHEN b.lead_time_days BETWEEN 0 AND 2 THEN '0-2D'
                WHEN b.lead_time_days BETWEEN 3 AND 7 THEN '3-7D'
                WHEN b.lead_time_days > 7 THEN '7D+'
                ELSE 'unknown'
            END AS lt_band,
            b.booking_id
        FROM `{project}.{dataset}.fct_bookings` b
        JOIN `{project}.{dataset}.dim_experiences` dex
            ON CAST(b.experience_id AS STRING) = CAST(dex.experience_id AS STRING)
        WHERE dex.combined_entity_id = '{ce_id}'
            AND DATE(b.date_created_at_et) BETWEEN '{c_s}' AND '{c_e}'
            AND b.lead_time_days IS NOT NULL AND b.lead_time_days >= 0
    ),
    tgid_totals AS (
        SELECT experience_id, COUNT(DISTINCT booking_id) AS total FROM bookings GROUP BY 1
    ),
    banded AS (
        SELECT experience_id, lt_band, COUNT(DISTINCT booking_id) AS cnt
        FROM bookings WHERE lt_band != 'unknown' GROUP BY 1, 2
    )
    SELECT b.experience_id, b.lt_band,
        SAFE_DIVIDE(b.cnt, t.total) AS pct
    FROM banded b JOIN tgid_totals t USING (experience_id)
    ORDER BY t.total DESC, b.experience_id, b.lt_band
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
        c_s=cur[0].strftime("%Y-%m-%d"), c_e=cur[1].strftime("%Y-%m-%d"),
    )
    return run_bq_query(query)


def fetch_lead_time_cohorts(ce_id, cur, ly_cur):
    # type: (int, Tuple[date,date], Tuple[date,date]) -> List[Dict[str, Any]]
    query = """
    WITH bookings AS (
        SELECT
            CASE
                WHEN b.lead_time_days BETWEEN 0 AND 2 THEN '0-2D'
                WHEN b.lead_time_days BETWEEN 3 AND 4 THEN '3-4D'
                WHEN b.lead_time_days BETWEEN 5 AND 7 THEN '5-7D'
                WHEN b.lead_time_days > 7 THEN '7D+'
                ELSE 'unknown'
            END AS lead_time_band,
            CASE
                WHEN DATE(b.date_created_at_et) BETWEEN '{c_s}' AND '{c_e}' THEN 'cur'
                WHEN DATE(b.date_created_at_et) BETWEEN '{ly_s}' AND '{ly_e}' THEN 'ly'
            END AS period,
            b.booking_id,
            b.price_net_usd AS revenue,
            b.price_payable_usd AS order_value
        FROM `{project}.{dataset}.fct_bookings` b
        JOIN `{project}.{dataset}.dim_experiences` dex
            ON CAST(b.experience_id AS STRING) = CAST(dex.experience_id AS STRING)
        WHERE dex.combined_entity_id = '{ce_id}'
            AND (DATE(b.date_created_at_et) BETWEEN '{c_s}' AND '{c_e}'
                 OR DATE(b.date_created_at_et) BETWEEN '{ly_s}' AND '{ly_e}')
            AND b.lead_time_days IS NOT NULL
            AND b.lead_time_days >= 0
    )
    SELECT
        lead_time_band,
        COUNT(DISTINCT CASE WHEN period = 'cur' THEN booking_id END) AS bookings_cur,
        SUM(CASE WHEN period = 'cur' THEN revenue ELSE 0 END) AS rev_cur,
        SAFE_DIVIDE(SUM(CASE WHEN period = 'cur' THEN order_value ELSE 0 END),
            NULLIF(COUNT(DISTINCT CASE WHEN period = 'cur' THEN booking_id END), 0)) AS aov_cur,
        COUNT(DISTINCT CASE WHEN period = 'ly' THEN booking_id END) AS bookings_ly,
        SUM(CASE WHEN period = 'ly' THEN revenue ELSE 0 END) AS rev_ly,
        SAFE_DIVIDE(SUM(CASE WHEN period = 'ly' THEN order_value ELSE 0 END),
            NULLIF(COUNT(DISTINCT CASE WHEN period = 'ly' THEN booking_id END), 0)) AS aov_ly
    FROM bookings
    WHERE lead_time_band != 'unknown'
    GROUP BY 1
    ORDER BY CASE lead_time_band
        WHEN '0-2D' THEN 1 WHEN '3-4D' THEN 2 WHEN '5-7D' THEN 3 WHEN '7D+' THEN 4
    END
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
        c_s=cur[0].strftime("%Y-%m-%d"), c_e=cur[1].strftime("%Y-%m-%d"),
        ly_s=ly_cur[0].strftime("%Y-%m-%d"), ly_e=ly_cur[1].strftime("%Y-%m-%d"),
    )
    return run_bq_query(query)


# ============================================================================
# SHAPLEY DECOMPOSITION
# ============================================================================

def calc_shapley_decomposition(current, prior):
    # type: (Dict[str, float], Dict[str, float]) -> Dict[str, float]
    """Exact Shapley values for multiplicative revenue decomposition.
    Revenue = Traffic x CVR x AOV (x CR x TR if available).
    Copied from market_weekly_review_v5.py:2419-2454.
    """
    factor_names = [k for k in ['traffic', 'cvr', 'aov', 'cr', 'tr'] if k in current and k in prior]
    n = len(factor_names)

    def _revenue(vals):
        r = 1.0
        for v in vals.values():
            r *= v
        return r

    prior_rev = _revenue({k: prior[k] for k in factor_names})
    current_rev = _revenue({k: current[k] for k in factor_names})

    shapley = {k: 0.0 for k in factor_names}

    for perm in itertools.permutations(factor_names):
        vals = {k: prior[k] for k in factor_names}
        prev_rev = _revenue(vals)
        for factor in perm:
            vals[factor] = current[factor]
            new_rev = _revenue(vals)
            shapley[factor] += new_rev - prev_rev
            prev_rev = new_rev

    n_perms = math.factorial(n)
    for k in shapley:
        shapley[k] /= n_perms

    shapley['total'] = current_rev - prior_rev
    return shapley


def compute_shapley_for_ce(cur_health, pri_health, cur_channels, pri_channels):
    # type: (Dict, Dict, List, List) -> Dict[str, float]
    cur_clicks = sum(float(c.get("clicks") or 0) for c in cur_channels if c.get("clicks"))
    pri_clicks = sum(float(c.get("clicks") or 0) for c in pri_channels if c.get("clicks"))

    cur_orders = int(cur_health.get("orders") or 0)
    pri_orders = int(pri_health.get("orders") or 0)
    cur_rev = float(cur_health.get("revenue") or 0)
    pri_rev = float(pri_health.get("revenue") or 0)

    if cur_clicks == 0 and pri_clicks == 0:
        return {"traffic": 0, "cvr": 0, "aov": 0, "tr": 0, "cr": 0, "total": 0}

    cur_cvr = cur_orders / cur_clicks if cur_clicks > 0 else 0
    pri_cvr = pri_orders / pri_clicks if pri_clicks > 0 else 0
    cur_aov = cur_rev / cur_orders if cur_orders > 0 else 0
    pri_aov = pri_rev / pri_orders if pri_orders > 0 else 0

    cur_tr = float(cur_health.get("tr") or 100) / 100.0
    pri_tr = float(pri_health.get("tr") or 100) / 100.0
    cur_cr = float(cur_health.get("cr") or 100) / 100.0
    pri_cr = float(pri_health.get("cr") or 100) / 100.0

    current = {"traffic": max(cur_clicks, 0.001), "cvr": max(cur_cvr, 0.00001), "aov": max(cur_aov, 0.01)}
    prior = {"traffic": max(pri_clicks, 0.001), "cvr": max(pri_cvr, 0.00001), "aov": max(pri_aov, 0.01)}

    if abs(cur_tr - pri_tr) > 0.001:
        current["tr"] = cur_tr
        prior["tr"] = pri_tr
    if abs(cur_cr - pri_cr) > 0.001:
        current["cr"] = cur_cr
        prior["cr"] = pri_cr

    return calc_shapley_decomposition(current, prior)


# ============================================================================
# HISTORICAL CONTEXT (filesystem only — Slack is handled by SKILL.md)
# ============================================================================

def find_historical_context(ce_name):
    # type: (str) -> Dict[str, List[str]]
    slug = ce_name.lower().replace(" ", "-").replace("'", "").replace("&", "and")
    results = {"perf_audits": [], "weekly_reviews": []}  # type: Dict[str, List[str]]

    pattern = os.path.join(_repo_root, "thoughts/shared/perf-audits/perf-audit-*{}*".format(slug))
    results["perf_audits"] = sorted(glob_mod.glob(pattern))[-5:]

    review_dir = os.path.join(_repo_root, "thoughts/shared/weekly-reviews")
    if os.path.isdir(review_dir):
        all_reviews = sorted(glob_mod.glob(os.path.join(review_dir, "**/*.md"), recursive=True))
        results["weekly_reviews"] = all_reviews[-10:]

    return results


# ============================================================================
# RENDERERS
# ============================================================================

def render_header(ce_name, ce_id, w):
    # type: (str, int, Dict) -> str
    lines = [
        "# CE Health: {} (ID: {})".format(ce_name, ce_id),
        "**Range:** {} | {}".format(w["range"], w["cur_label"]),
        "**Generated:** {}".format(date.today().isoformat()),
        "",
        "---",
    ]
    return "\n".join(lines)


def render_metadata(meta):
    # type: (Dict) -> str
    lines = [
        "## 1. CE Metadata",
        "",
        "| Field | Value |",
        "|-------|-------|",
    ]
    field_map = [
        ("CE Name", "combined_entity_name"),
        ("CE ID", "combined_entity_id"),
        ("Market", "market"),
        ("Country", "country"),
        ("Region", "region"),
        ("Category", "combined_entity_category"),
        ("Subcategory", "combined_entity_subcategory"),
        ("Evolution Bucket", "evolution_bucket"),
        ("Management Type", "management_type"),
        ("Status", "headout_status"),
        ("Landing Page", "top_page_url"),
    ]
    for label, key in field_map:
        val = meta.get(key, "\u2014") or "\u2014"
        lines.append("| {} | {} |".format(label, val))
    return "\n".join(lines)


def render_vitals(data, w):
    # type: (Dict[str, Dict], Dict) -> str
    c = data.get("current") or {}
    p = data.get("prior") or {}
    ly = data.get("ly_current") or {}
    lyp = data.get("ly_prior") or {}
    sl = w["seq_label"]
    cc, cp, clc, clp = w["col_cur"], w["col_pri"], w["col_ly_cur"], w["col_ly_pri"]

    lines = [
        "## 2. CE Vitals",
        "",
        "| Metric | {} | {} | \u0394 {} ({}) | {} | {} | \u0394 {} ({} LY) | \u0394 LY (YoY) |".format(
            cc, cp, cp, sl, clc, clp, clp, sl),
        "|--------|---|---|---|---|---|---|---|",
    ]
    metrics = [
        ("Revenue", "revenue", fm, dp, da),
        ("ROI(1)", "roi_1", fp, dpp, None),
        ("TR", "tr", fp, dpp, None),
        ("CR", "cr", fp, dpp, None),
        ("AOV", "aov", fd, dp, None),
        ("Orders", "orders", fi, dp, None),
    ]
    for label, key, fmt_fn, delta_fn, abs_fn in metrics:
        cv, pv, lyv, lypv = _g(c, key), _g(p, key), _g(ly, key), _g(lyp, key)
        d_pri = delta_fn(cv, pv)
        d_ly_pri = delta_fn(lyv, lypv)
        d_yoy = delta_fn(cv, lyv)
        if abs_fn and cv is not None and lyv is not None:
            d_yoy = "{} ({})".format(delta_fn(cv, lyv), abs_fn(cv, lyv))
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
            label, fmt_fn(cv), fmt_fn(pv), d_pri, fmt_fn(lyv), fmt_fn(lypv), d_ly_pri, d_yoy))
    return "\n".join(lines)


def render_channels(data, w):
    # type: (Dict[str, List], Dict) -> str
    cur = data.get("current") or []
    pri_list = data.get("prior") or []
    ly_list = data.get("ly_current") or []
    if not cur:
        return "## 3. Channel Breakdown\n\n*No channel data available.*"

    pri_map = {r["channel"]: r for r in pri_list}
    ly_map = {r["channel"]: r for r in ly_list}
    cur_total = sum(_g(r, "revenue", 0) for r in cur)
    cur_sorted = sorted(cur, key=lambda r: _g(r, "revenue", 0), reverse=True)
    cc, cp, sl = w["col_cur"], w["col_pri"], w["seq_label"]

    lines = [
        "## 3. Channel Breakdown",
        "",
        "| Channel | {} Rev | \u0394 {} ({}) | \u0394 LY (YoY) | TR | CR | AOV | Orders | Share |".format(cc, cp, sl),
        "|---------|---|---|---|---|---|---|---|---|",
    ]
    for ch in cur_sorted:
        name = ch["channel"]
        rev = _g(ch, "revenue", 0)
        pri_ch = pri_map.get(name, {})
        ly_ch = ly_map.get(name, {})
        share = rev / cur_total * 100 if cur_total else 0
        share_str = "<1%" if 0 < share < 1 else "{:.0f}%".format(share)
        d_pri = dp(rev, _g(pri_ch, "revenue")) if pri_ch else "\u2014"
        d_ly = dp(rev, _g(ly_ch, "revenue")) if ly_ch else "\u2014"
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            name, fm(rev), d_pri, d_ly,
            fp(_g(ch, "tr")), fp(_g(ch, "cr")),
            fd(_g(ch, "aov")), fi(_g(ch, "orders")), share_str))

    cur_total_orders = sum(_g(r, "orders", 0) for r in cur)
    lines.append("| **TOTAL** | **{}** | | | | | | **{}** | **100%** |".format(
        fm(cur_total), fi(cur_total_orders)))
    return "\n".join(lines)


def render_funnel(data, w):
    # type: (Dict[str, Dict], Dict) -> str
    c = data.get("current") or {}
    p = data.get("prior") or {}
    ly = data.get("ly_current") or {}
    lyp = data.get("ly_prior") or {}
    sl = w["seq_label"]
    cc, cp, clc, clp = w["col_cur"], w["col_pri"], w["col_ly_cur"], w["col_ly_pri"]

    lines = [
        "## 4. Funnel",
        "",
        "| Stage | {} | {} | \u0394 {} ({}) | {} | {} | \u0394 {} ({} LY) | \u0394 LY (YoY) |".format(
            cc, cp, cp, sl, clc, clp, clp, sl),
        "|-------|---|---|---|---|---|---|---|",
    ]
    stages = [
        ("LP Users", "lp_viewers", fi, dp),
        ("LP2S", "lp2s", fp1, dpp),
        ("S2C", "s2c", fp1, dpp),
        ("C2O", "c2o", fp1, dpp),
    ]
    for label, key, fmt_fn, delta_fn in stages:
        cv, pv, lyv, lypv = _g(c, key), _g(p, key), _g(ly, key), _g(lyp, key)
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
            label, fmt_fn(cv), fmt_fn(pv), delta_fn(cv, pv),
            fmt_fn(lyv), fmt_fn(lypv), delta_fn(lyv, lypv), delta_fn(cv, lyv)))
    return "\n".join(lines)


def render_l12m(monthly):
    # type: (List[Dict]) -> str
    if not monthly:
        return "## 5. L12M Trajectory\n\n*L12M data unavailable.*"

    lines = [
        "## 5. L12M Trajectory",
        "",
        "### CE Health (Monthly)",
        "",
        "| Month | Revenue | Orders | ROI(1) | TR | CR | AOV |",
        "|-------|---------|--------|--------|----|----|-----|",
    ]
    for m in monthly:
        roi = _g(m, "roi_1")
        tr = _g(m, "tr")
        cr = _g(m, "cr")
        lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            m.get("month", "\u2014"), fm(_g(m, "revenue")), fi(_g(m, "orders")),
            fp1(roi * 100 if roi else None),
            fp1(tr * 100 if tr else None),
            fp1(cr * 100 if cr else None),
            fd(_g(m, "aov"))))

    lines.extend(["", "### Paid Performance (Monthly)", "",
        "| Month | Ad Spend | CPC | Clicks | CVR | CM1 | Paid ROI |",
        "|-------|----------|-----|--------|-----|-----|----------|"])
    for m in monthly:
        paid_roi = _g(m, "paid_roi")
        paid_cvr = _g(m, "paid_cvr")
        lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            m.get("month", "\u2014"), fm(_g(m, "paid_spend")),
            fd(_g(m, "paid_cpc")), fi(_g(m, "paid_clicks")),
            fp1(paid_cvr * 100 if paid_cvr else None),
            fm(_g(m, "paid_cm1")),
            fp1(paid_roi * 100 if paid_roi else None)))
    return "\n".join(lines)


def render_tgids(tgid_data, w):
    # type: (List[Dict], Dict) -> str
    if not tgid_data:
        return "## 6. Top TGIDs\n\n*No TGID data available.*"
    cc, cp, sl = w["col_cur"], w["col_pri"], w["seq_label"]

    lines = [
        "## 6. Top TGIDs",
        "",
        "| TGID | Experience | {} Rev | \u0394 {} ({}) | \u0394 LY (YoY) | Share | AOV | TR |".format(cc, cp, sl),
        "|------|-----------|---|---|---|---|---|---|",
    ]
    for t in tgid_data:
        name = str(t.get("experience_name") or "\u2014")
        if len(name) > 40:
            name = name[:37] + "..."
        rev_cur = _g(t, "rev_cur", 0)
        d_pri = dp(rev_cur, _g(t, "rev_pri"))
        d_ly = dp(rev_cur, _g(t, "rev_ly"))
        share = _g(t, "rev_share_pct")
        share_str = "{:.1f}%".format(share) if share is not None else "\u2014"
        aov = _g(t, "aov_cur")
        tr = _g(t, "tr_cur")
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
            t.get("experience_id", "\u2014"), name, fm(rev_cur), d_pri, d_ly,
            share_str, fd(aov), fp1(tr * 100 if tr else None)))
    return "\n".join(lines)


def render_shapley(shapley, w):
    # type: (Dict[str, float], Dict) -> str
    total = shapley.get("total", 0)
    abs_total = abs(total) if total else 1

    lines = [
        "## 7. Driver Diagnosis (Shapley)",
        "",
        "Revenue \u0394 {}: **{}**".format(w["col_pri"], fm(total)),
        "",
        "| Factor | $ Impact | % of Total | Direction |",
        "|--------|----------|-----------|-----------|",
    ]
    factor_labels = {
        "traffic": ("Traffic (Clicks)", "\u2191 More clicks" if shapley.get("traffic", 0) >= 0 else "\u2193 Fewer clicks"),
        "cvr": ("CVR", "\u2191 Better conversion" if shapley.get("cvr", 0) >= 0 else "\u2193 Lower conversion"),
        "aov": ("AOV", "\u2191 Higher ticket value" if shapley.get("aov", 0) >= 0 else "\u2193 Lower ticket value"),
        "tr": ("Take Rate", "\u2191 TR improved" if shapley.get("tr", 0) >= 0 else "\u2193 TR compression"),
        "cr": ("Completion Rate", "\u2191 CR improved" if shapley.get("cr", 0) >= 0 else "\u2193 CR declined"),
    }
    sorted_factors = sorted(
        [(k, v) for k, v in shapley.items() if k != "total"],
        key=lambda x: abs(x[1]), reverse=True)

    primary = sorted_factors[0][0] if sorted_factors else None
    for k, v in sorted_factors:
        label, direction = factor_labels.get(k, (k, ""))
        pct = abs(v) / abs_total * 100 if abs_total else 0
        bold = "**" if k == primary else ""
        lines.append("| {b}{label}{b} | {b}{val}{b} | {b}{pct:.0f}%{b} | {b}{dir}{b} |".format(
            b=bold, label=label, val=fm(v), pct=pct, dir=direction))

    if primary:
        label, direction = factor_labels.get(primary, (primary, ""))
        lines.append("")
        lines.append("**Primary driver:** {} ({})".format(label, fm(shapley.get(primary, 0))))
    return "\n".join(lines)


def render_historical(context):
    # type: (Dict[str, List[str]]) -> str
    lines = [
        "## 8. Historical Context",
        "",
    ]
    audits = context.get("perf_audits") or []
    if audits:
        lines.append("**Past perf audits:**")
        for a in audits:
            rel = os.path.relpath(a, _repo_root)
            lines.append("- `{}`".format(rel))
    else:
        lines.append("**Past perf audits:** None found.")

    lines.append("")
    reviews = context.get("weekly_reviews") or []
    if reviews:
        lines.append("**Recent weekly reviews:** {} files in `thoughts/shared/weekly-reviews/`".format(len(reviews)))
    else:
        lines.append("**Recent weekly reviews:** None found.")

    lines.extend([
        "",
        "*Slack context: searched by SKILL.md after script renders.*",
        "",
        "> **Add your context:** Any thoughts, links, Slack threads, or hypotheses before we go deeper?",
    ])
    return "\n".join(lines)


def render_tgids_enriched(tgid_data, tgid_funnel, tgid_lt, w):
    # type: (List[Dict], List[Dict], List[Dict], Dict) -> str
    if not tgid_data:
        return "## 6. Top TGIDs\n\n*No TGID data available.*"
    cc = w["col_cur"]

    funnel_map = {}  # type: Dict[str, Dict]
    if tgid_funnel:
        for f in tgid_funnel:
            funnel_map[str(f.get("experience_id", ""))] = f

    lt_map = {}  # type: Dict[str, Dict[str, float]]
    if tgid_lt:
        for r in tgid_lt:
            eid = str(r.get("experience_id", ""))
            if eid not in lt_map:
                lt_map[eid] = {}
            lt_map[eid][r.get("lt_band", "")] = float(r.get("pct") or 0)

    total_select = sum(float(funnel_map.get(str(t.get("experience_id", "")), {}).get("select_users_cur") or 0) for t in tgid_data)

    lines = [
        "## 6. Top TGIDs",
        "",
        "| TGID | Experience | {} Rev | Share | RPC | AOV | CR | TR | Sel Users | %Traffic | S2C | C2O | %0-2D | %3-7D | %7D+ |".format(cc),
        "|------|-----------|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t in tgid_data:
        name = str(t.get("experience_name") or "\u2014")
        if len(name) > 30:
            name = name[:27] + "..."
        eid = str(t.get("experience_id") or "")
        rev_cur = _g(t, "rev_cur", 0)
        share = _g(t, "rev_share_pct")
        share_str = "{:.0f}%".format(share) if share is not None else "\u2014"

        rpc_cur, rpc_ly = _g(t, "rpc_cur"), _g(t, "rpc_ly")
        aov_cur, aov_ly = _g(t, "aov_cur"), _g(t, "aov_ly")
        cr_cur, cr_ly = _g(t, "cr_cur"), _g(t, "cr_ly")
        tr_cur, tr_ly = _g(t, "tr_cur"), _g(t, "tr_ly")

        d_rev = dp(rev_cur, _g(t, "rev_ly"))
        d_rpc = dp(rpc_cur, rpc_ly) if rpc_ly else "\u2014"
        d_aov = dp(aov_cur, aov_ly) if aov_ly else "\u2014"
        d_cr = dpp(cr_cur * 100 if cr_cur else None, cr_ly * 100 if cr_ly else None)
        d_tr = dpp(tr_cur * 100 if tr_cur else None, tr_ly * 100 if tr_ly else None)

        f = funnel_map.get(eid, {})
        sel = _g(f, "select_users_cur", 0)
        sel_str = "{:.1f}K".format(sel / 1000) if sel >= 1000 else fi(sel)
        sel_pct = sel / total_select * 100 if total_select else None
        pct_str = "{:.0f}%".format(sel_pct) if sel_pct is not None else "\u2014"
        s2c = _g(f, "s2c_cur")
        c2o = _g(f, "c2o_cur")
        s2c_ly = _g(f, "s2c_ly")
        c2o_ly = _g(f, "c2o_ly")
        d_s2c = dpp(s2c * 100 if s2c else None, s2c_ly * 100 if s2c_ly else None)
        d_c2o = dpp(c2o * 100 if c2o else None, c2o_ly * 100 if c2o_ly else None)

        lt = lt_map.get(eid, {})
        lt_02d = lt.get("0-2D")
        lt_37d = lt.get("3-7D")
        lt_7p = lt.get("7D+")

        lines.append("| {} | {} | {} {} | {} | {} {} | {} {} | {} {} | {} {} | {} | {} | {} {} | {} {} | {} | {} | {} |".format(
            eid, name,
            fm(rev_cur), d_rev, share_str,
            fd(rpc_cur), d_rpc,
            fd(aov_cur), d_aov,
            fp1(cr_cur * 100 if cr_cur else None), d_cr,
            fp1(tr_cur * 100 if tr_cur else None), d_tr,
            sel_str, pct_str,
            fp1(s2c * 100 if s2c else None), d_s2c,
            fp1(c2o * 100 if c2o else None), d_c2o,
            fp1(lt_02d * 100 if lt_02d else None),
            fp1(lt_37d * 100 if lt_37d else None),
            fp1(lt_7p * 100 if lt_7p else None)))

    return "\n".join(lines)


def render_lead_time(lt_data, w):
    # type: (List[Dict], Dict) -> str
    if not lt_data:
        return "## 9. Lead Time Cohorts\n\n*No lead time data available.*"
    cc = w["col_cur"]
    total_cur = sum(_g(r, "bookings_cur", 0) for r in lt_data)

    lines = [
        "## 9. Lead Time Cohorts",
        "",
        "| Band | {} Bookings | Share | {} Rev | AOV | LY Bookings | \u0394 LY | LY AOV |".format(cc, cc),
        "|------|---|---|---|---|---|---|---|",
    ]
    for r in lt_data:
        band = r.get("lead_time_band", "\u2014")
        bk_cur = _g(r, "bookings_cur", 0)
        share = bk_cur / total_cur * 100 if total_cur else 0
        bk_ly = _g(r, "bookings_ly", 0)
        lines.append("| {} | {} | {:.0f}% | {} | {} | {} | {} | {} |".format(
            band, fi(bk_cur), share, fm(_g(r, "rev_cur")),
            fd(_g(r, "aov_cur")),
            fi(bk_ly), dp(bk_cur, bk_ly), fd(_g(r, "aov_ly"))))

    total_ly = sum(_g(r, "bookings_ly", 0) for r in lt_data)
    lines.append("| **TOTAL** | **{}** | **100%** | | | **{}** | **{}** | |".format(
        fi(total_cur), fi(total_ly), dp(total_cur, total_ly)))
    return "\n".join(lines)


def render_landing_pages(lp_data, w):
    # type: (List[Dict], Dict) -> str
    if not lp_data:
        return "## 10. Landing Pages\n\n*No LP funnel data available.*"

    top_lps = [r for r in lp_data if r.get("l4w_users", 0) >= 100][:15]
    if not top_lps:
        top_lps = lp_data[:10]

    lines = [
        "## 10. Landing Pages",
        "",
        "| Page URL | Users | CVR | LP2S | S2C | C2O | \u0394 LP2S LY | \u0394 S2C LY | \u0394 C2O LY |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in top_lps:
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
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            url, u_str, fp1(cvr), fp1(lp2s), fp1(s2c), fp1(c2o),
            dpp(lp2s, ly_lp2s), dpp(s2c, ly_s2c), dpp(c2o, ly_c2o)))
    return "\n".join(lines)


def render_customer_country(cur_data, ly_data, w):
    # type: (List[Dict], List[Dict], Dict) -> str
    if not cur_data:
        return "## 11. Customer Countries\n\n*No customer country data available.*"
    cc = w["col_cur"]

    ly_map = {r.get("customer_country"): r for r in (ly_data or [])}
    total_cur_orders = sum(_g(r, "orders", 0) for r in cur_data)
    total_cur_rev = sum(_g(r, "revenue", 0) for r in cur_data)

    lines = [
        "## 11. Customer Countries",
        "",
        "| Country | {} Orders | Order Share | {} Rev | Rev Share | AOV | \u0394 LY Orders |".format(cc, cc),
        "|---------|---|---|---|---|---|---|",
    ]
    for r in cur_data[:10]:
        country = r.get("customer_country") or "\u2014"
        orders = _g(r, "orders", 0)
        rev = _g(r, "revenue", 0)
        o_share = orders / total_cur_orders * 100 if total_cur_orders else 0
        r_share = rev / total_cur_rev * 100 if total_cur_rev else 0
        aov = rev / orders if orders else None
        ly_r = ly_map.get(country, {})
        ly_orders = _g(ly_r, "orders")
        lines.append("| {} | {} | {:.0f}% | {} | {:.0f}% | {} | {} |".format(
            country, fi(orders), o_share, fm(rev), r_share, fd(aov),
            dp(orders, ly_orders) if ly_orders else "\u2014"))
    return "\n".join(lines)


# ============================================================================
# ORCHESTRATOR
# ============================================================================

def run_ce_health(ce_id, range_str=None, start=None, end=None, output_path=None):
    # type: (int, Optional[str], Optional[date], Optional[date], Optional[str]) -> None
    w = compute_windows(range_str=range_str, start=start, end=end)

    cur = w["current"]
    pri = w["prior"]
    ly_cur = w["ly_current"]
    ly_pri = w["ly_prior"]

    sys.stderr.write("1. Resolving CE metadata...\n")
    sys.stderr.flush()
    meta = fetch_ce_metadata(ce_id)
    ce_name = meta.get("combined_entity_name", "CE {}".format(ce_id))

    sys.stderr.write("2. Fetching CE vitals (4 windows)...\n")
    sys.stderr.flush()
    vitals = {
        "current": fetch_ce_health(ce_id, cur[0], cur[1]),
        "prior": fetch_ce_health(ce_id, pri[0], pri[1]),
        "ly_current": fetch_ce_health(ce_id, ly_cur[0], ly_cur[1]),
        "ly_prior": fetch_ce_health(ce_id, ly_pri[0], ly_pri[1]),
    }

    sys.stderr.write("3. Fetching channel breakdown (4 windows)...\n")
    sys.stderr.flush()
    channels = {
        "current": _fetch_channel_window_v2(ce_id, cur[0], cur[1]),
        "prior": _fetch_channel_window_v2(ce_id, pri[0], pri[1]),
        "ly_current": _fetch_channel_window_v2(ce_id, ly_cur[0], ly_cur[1]),
        "ly_prior": _fetch_channel_window_v2(ce_id, ly_pri[0], ly_pri[1]),
    }

    sys.stderr.write("4. Fetching funnel (4 windows)...\n")
    sys.stderr.flush()
    funnel = {
        "current": fetch_ce_funnel(ce_id, cur[0], cur[1]),
        "prior": fetch_ce_funnel(ce_id, pri[0], pri[1]),
        "ly_current": fetch_ce_funnel(ce_id, ly_cur[0], ly_cur[1]),
        "ly_prior": fetch_ce_funnel(ce_id, ly_pri[0], ly_pri[1]),
    }

    sys.stderr.write("5. Fetching L12M trajectory...\n")
    sys.stderr.flush()
    monthly = _fetch_monthly_summary(ce_id)

    sys.stderr.write("6. Fetching top TGIDs...\n")
    sys.stderr.flush()
    tgids = fetch_top_tgids(ce_id, cur, pri, ly_cur, ly_pri)

    sys.stderr.write("6b. Fetching TGID funnel...\n")
    sys.stderr.flush()
    tgid_funnel = fetch_tgid_funnel(ce_id, cur, ly_cur)

    sys.stderr.write("6c. Fetching TGID lead time...\n")
    sys.stderr.flush()
    tgid_lt = fetch_tgid_lead_time(ce_id, cur, ly_cur)

    sys.stderr.write("7. Computing Shapley decomposition...\n")
    sys.stderr.flush()
    shapley = compute_shapley_for_ce(
        vitals.get("current", {}), vitals.get("prior", {}),
        channels.get("current", []), channels.get("prior", []))

    sys.stderr.write("8. Searching historical context...\n")
    sys.stderr.flush()
    history = find_historical_context(ce_name)

    sys.stderr.write("9. Fetching lead time cohorts...\n")
    sys.stderr.flush()
    lead_time = fetch_lead_time_cohorts(ce_id, cur, ly_cur)

    sys.stderr.write("10. Fetching landing page funnel...\n")
    sys.stderr.flush()
    lp_funnel = fetch_lp_funnel(ce_id, cur[0], cur[1], ly_cur[0], ly_cur[1])

    # Most-visited landing page URL in the current window. Mirrors CVR-RCA's
    # Q0 top_page_url so the CE-RCA composite header can render the clickable
    # CE link (🔗) — the master reads this from the JSON sidecar's metadata.
    # Reuses the lp_funnel data already fetched; no extra BQ query.
    if lp_funnel:
        top_lp = max(lp_funnel, key=lambda r: r.get("l4w_users", 0) or 0)
        top_url = top_lp.get("page_url")
        if top_url:
            meta["top_page_url"] = top_url

    sys.stderr.write("11. Fetching customer countries...\n")
    sys.stderr.flush()
    customers_cur = fetch_customer_country_distribution(ce_id, cur[0], cur[1])
    customers_ly = fetch_customer_country_distribution(ce_id, ly_cur[0], ly_cur[1])

    # Render
    sys.stderr.write("12. Rendering report...\n")
    sys.stderr.flush()
    sections = [
        render_header(ce_name, ce_id, w),
        "",
        render_metadata(meta),
        "",
        render_vitals(vitals, w),
        "",
        render_channels(channels, w),
        "",
        render_funnel(funnel, w),
        "",
        render_l12m(monthly),
        "",
        render_tgids_enriched(tgids, tgid_funnel, tgid_lt, w),
        "",
        render_shapley(shapley, w),
        "",
        render_historical(history),
        "",
        render_lead_time(lead_time, w),
        "",
        render_landing_pages(lp_funnel, w),
        "",
        render_customer_country(customers_cur, customers_ly, w),
        "",
        "---",
        "*CE Health v2.0 | {} | {} windows*".format(date.today().isoformat(), w["range"]),
    ]
    report = "\n".join(sections)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)
        sys.stderr.write("Report -> {}\n".format(output_path))

        json_path = output_path.rsplit(".", 1)[0] + ".json"
        sidecar = {
            "ce_id": ce_id,
            "ce_name": ce_name,
            "range": w["range"],
            "generated_at": date.today().isoformat(),
            "windows": {
                "current": [cur[0].isoformat(), cur[1].isoformat()],
                "prior": [pri[0].isoformat(), pri[1].isoformat()],
                "ly_current": [ly_cur[0].isoformat(), ly_cur[1].isoformat()],
                "ly_prior": [ly_pri[0].isoformat(), ly_pri[1].isoformat()],
            },
            "metadata": {k: str(v) for k, v in meta.items()} if meta else {},
            "vitals": vitals,
            "shapley": shapley,
        }
        with open(json_path, "w") as f:
            json.dump(sidecar, f, default=str, indent=2)
        sys.stderr.write("JSON -> {}\n".format(json_path))
    else:
        sys.stdout.write(report)
        if not report.endswith("\n"):
            sys.stdout.write("\n")

    sys.stderr.write("Done.\n")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog="ce_health",
        description="CE Health Briefing Packet",
    )
    parser.add_argument("--ce-id", required=True, help="Combined entity ID")
    parser.add_argument("--range", default=None,
                        help="Time period: l<N>w (weeks) or l<N>m (months). E.g. l4w, l2m, week, month")
    parser.add_argument("--start", default=None, help="Custom start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="Custom end date (YYYY-MM-DD)")
    parser.add_argument("--output", default=None, help="Output file path (.md)")
    args = parser.parse_args()

    if not args.range and not (args.start and args.end):
        parser.error("Either --range or both --start and --end are required")

    start_date = date.fromisoformat(args.start) if args.start else None
    end_date = date.fromisoformat(args.end) if args.end else None

    run_ce_health(
        ce_id=int(args.ce_id),
        range_str=args.range,
        start=start_date,
        end=end_date,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
