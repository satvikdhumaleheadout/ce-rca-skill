"""
BigQuery source module for perf_audit_v3.

Phase 1 adds per-campaign CM1/ROI by joining spend from google_ads_campaign_stats
with last-touch attributed revenue from fct_orders.touchpoints.

Column-name reconciliation (departs from plan's SQL to match live schema):
    The plan's SQL used `o.sum_revenue`, `o.sum_direct_costs`, `o.sum_coupon_discount`,
    `o.sum_wallet_credits`, `o.completed_date`. The live fct_orders table uses:
        amount_revenue_usd, amount_direct_costs_usd, amount_coupon_discount_usd,
        wallet_credits_usd, created_at (timestamp, not a date)
    These match the columns combined_entity_stats.sql aggregates from (verified
    at dbt/models/marts/reports/combined_entity_stats.sql:68) so using them keeps
    the CE-level vs campaign-level reconciliation well-defined.

Attribution semantics:
    `touchpoints` is an ARRAY<STRUCT<campaign_id STRING, touchpoint_rank INT64,
    touchpoint_rank_reversed INT64, ...>>. Verified via live probe 2026-04-19:
        touchpoint_rank = 1           -> FIRST touch (earliest attribution_timestamp)
        touchpoint_rank_reversed = 1  -> LAST touch
    The plan calls for last-touch attribution, so this module filters on
    `touchpoint_rank_reversed = 1`. (Plan's `touchpoint_rank = 1` was
    first-touch — known correction, noted in the Phase 1 handoff.)

    touchpoint.campaign_id is formatted as "1 - <numeric_id>". The "1 - "
    prefix MUST be stripped before casting to INT64 (we extract the trailing
    digit run via REGEXP_EXTRACT(r'\\d+$')).

Reconciliation note (documented here because it's load-bearing for future QA):

    `combined_entity_stats` (CE-level CM1 in v2) sums FULL CE-level spend
    across all ad_platforms minus FULL CE-level direct costs -- it is a
    pre-attributed, CE-anchored aggregation.

    `fct_orders.touchpoints` is PER-ORDER last-touch: each order contributes
    its revenue/direct_costs/coupons/wallet to the touchpoint with
    touchpoint_rank_reversed = 1. Orders with no paid touchpoint (organic /
    offline) are excluded entirely. Spend comes from google_ads_campaign_stats
    regardless of whether any attributed order exists.

    Consequence: campaign-level CM1 SUM != CE-level CM1 exactly.
    Target tolerance is 20%, not 5%. A gap >30% usually means heavy organic
    or offline orders (no paid touchpoint) or tracking drift.

Aggregation invariant (critical):
    All JOINs and GROUP BYs use the numeric `campaign_id`. Cleaned display names
    must NEVER be used as aggregation keys -- Harshita's suffix cleaning merges
    distinct campaigns when used upstream of GROUP BY.

"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

logger = logging.getLogger(__name__)

PROJECT_ID = "headout-analytics"
DATASET = "analytics_reporting"

_bq_client = None


def run_bq_query(query, _max_retries=4, _base_delay=10.0):
    # type: (str, int, float) -> list[dict]
    """Run a BigQuery query and return rows as dicts.

    Retries transient **NotFound (404)** errors. The `analytics_reporting` tables are
    zero-copy CLONE tables that are dropped + recreated during refresh; a query landing
    mid-refresh raises "Table ... not found in location EU" for a few seconds. The
    BigQuery client does NOT retry NotFound by default (it treats 404 as permanent), so
    without this a single mid-refresh query would crash the whole run. NotFound fails
    fast (no data scanned), so retrying is cheap. Linear backoff; re-raise after the last
    attempt so a genuinely-missing table still surfaces (just ~a minute later).
    """
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=PROJECT_ID, location="EU")
    last_exc = None
    for attempt in range(1, _max_retries + 1):
        try:
            rows = _bq_client.query(query).result()
            return [dict(row) for row in rows]
        except NotFound as exc:
            last_exc = exc
            if attempt == _max_retries:
                break
            delay = _base_delay * attempt
            logger.warning(
                "run_bq_query: transient NotFound (likely a clone-refresh window) on "
                "attempt %d/%d; retrying in %.0fs. Detail: %s",
                attempt, _max_retries, delay, exc,
            )
            time.sleep(delay)
    raise last_exc


def _fetch_pmax_value(ce_id, start, end):
    # type: (int, date, date) -> Dict[str, float]
    """PMax revenue + CM1 for a CE from fct_orders (CE-attributed ground truth).

    google_ads_pmax_asset_stats.sum_conversion_value is unreliable at CE grain —
    post-Sep-2025 it's already ~net, so `× revenue_percentage` understates CM1 ~4×.
    Per the perf-team rule ("PMax is city/country-level; use fct_orders for per-CE
    PMax metrics"), value comes from fct_orders PMax-channel orders. PMax *spend*
    stays from asset-stats (valid via the dedicated asset group / CID filter).
    """
    query = """
    SELECT
        ROUND(SUM(amount_revenue_usd), 2) AS revenue,
        ROUND(SUM(amount_revenue_usd - amount_direct_costs_usd), 2) AS cm1,
        COUNT(*) AS orders
    FROM `{project}.{dataset}.fct_orders`
    WHERE combined_entity_id = '{ce_id}'
        AND DATE(created_at) BETWEEN '{start}' AND '{end}'
        AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
        AND user_type = 'Customer'
        AND channel_name = 'Google Ads'
        AND REGEXP_CONTAINS(LOWER(COALESCE(campaign_name, '')), r'pmax|performance.max')
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )
    rows = run_bq_query(query) or []
    r = rows[0] if rows else {}
    return {
        "revenue": float(r.get("revenue") or 0.0),
        "cm1": float(r.get("cm1") or 0.0),
        "orders": int(r.get("orders") or 0),
    }


def fetch_campaign_level_cm1_roi(
    ce_id,    # type: int
    tw,       # type: Tuple[date, date]
    ly,       # type: Tuple[date, date]
):
    # type: (...) -> Dict[str, List[Dict[str, Any]]]
    """Per-campaign CM1 and ROI for TW and LY windows.

    Computes, per campaign_id in this CE's scope:
        - spend, clicks, impressions, online_conv (from google_ads_campaign_stats)
        - revenue, direct_costs, coupons, wallet_credits (from fct_orders via
          last-touch touchpoint attribution)
        - cm1 = offline_contribution_margin (post-2025-09-01) or calculated_contribution_margin (fallback), from google_ads_campaign_stats — matches Omni definition
        - roi = cm1 / spend
        - troas_target, bid_strategy_name (latest values in window)

    Args:
        ce_id: Combined entity ID (int). Cast to string inside SQL filter.
        tw: (start, end) for this-window. Inclusive.
        ly: (start, end) for last-year (364 days back). Inclusive.

    Returns:
        Dict with keys 'tw' and 'ly'. Each maps to a list of campaign dicts.
        Empty list when no campaigns have spend in that window.
    """
    tw_start, tw_end = tw
    ly_start, ly_end = ly

    return {
        "tw": _fetch_window(ce_id, tw_start, tw_end),
        "ly": _fetch_window(ce_id, ly_start, ly_end),
    }


def _fetch_window(ce_id, start, end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Single-window campaign-level CM1/ROI pull.

    See module docstring for attribution semantics and column-name reconciliation.
    """

    query = """
    WITH orders_attr AS (
        SELECT
            CAST(REGEXP_EXTRACT(t.campaign_id, r'\\d+$') AS INT64) AS campaign_id,
            SUM(o.amount_revenue_usd) AS revenue,
            SUM(o.amount_direct_costs_usd) AS direct_costs,
            SUM(COALESCE(o.amount_coupon_discount_usd, 0)) AS coupons,
            SUM(COALESCE(o.wallet_credits_usd, 0)) AS wallet_credits
        FROM `{project}.{dataset}.fct_orders` o,
             UNNEST(o.touchpoints) t
        WHERE t.touchpoint_rank_reversed = 1
            AND DATE(o.created_at) BETWEEN '{start}' AND '{end}'
            AND t.campaign_id IS NOT NULL
        GROUP BY 1
    ),
    spend_agg AS (
        SELECT
            SAFE_CAST(g.campaign_id AS INT64) AS campaign_id,
            ANY_VALUE(g.campaign_name) AS campaign_name,
            ANY_VALUE(g.current_campaign_target_roas) AS troas_target,
            ANY_VALUE(g.current_campaign_bidding_strategy) AS bid_strategy,
            ANY_VALUE(g.current_bidding_strategy_name) AS bid_strategy_name,
            ANY_VALUE(g.campaign_city) AS campaign_city,
            ANY_VALUE(g.campaign_targeting_location) AS campaign_targeting_location,
            ANY_VALUE(g.campaign_language) AS campaign_language,
            ANY_VALUE(g.campaign_status) AS campaign_status,
            ANY_VALUE(g.current_campaign_budget) AS campaign_budget,
            ANY_VALUE(g.current_campaign_labels) AS campaign_labels,
            ANY_VALUE(g.campaign_target_ce_label) AS ce_label,
            SUM(g.sum_spend) AS spend,
            SUM(g.count_clicks) AS clicks,
            SUM(g.count_impressions) AS impressions,
            SUM(COALESCE(g.count_conversions_online, 0)) AS online_conv,
            SUM(CASE
                WHEN g.report_date > '2025-09-01'
                    AND COALESCE(g.sum_conversion_value_offline_contribution_margin, 0) > 0
                THEN g.sum_conversion_value_offline_contribution_margin
                ELSE g.sum_conversion_value_calculated_contribution_margin
            END) AS cm1
        FROM `{project}.{dataset}.google_ads_campaign_stats` g
        WHERE g.campaign_target_combined_entity_id = '{ce_id}'
            AND g.report_date BETWEEN '{start}' AND '{end}'
        GROUP BY 1
    )
    SELECT
        s.campaign_id,
        s.campaign_name,
        s.troas_target,
        s.bid_strategy,
        s.bid_strategy_name,
        s.campaign_city,
        s.campaign_targeting_location,
        s.campaign_language,
        s.campaign_status,
        s.campaign_budget,
        s.campaign_labels,
        s.ce_label,
        s.spend,
        s.clicks,
        s.impressions,
        s.online_conv,
        COALESCE(o.revenue, 0) AS revenue,
        COALESCE(o.direct_costs, 0) AS direct_costs,
        COALESCE(o.coupons, 0) AS coupons,
        COALESCE(o.wallet_credits, 0) AS wallet_credits,
        s.cm1,
        SAFE_DIVIDE(s.cm1, s.spend) AS roi
    FROM spend_agg s
    LEFT JOIN orders_attr o USING (campaign_id)
    WHERE s.spend > 0
    ORDER BY s.spend DESC
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
    )

    results = run_bq_query(query)
    if not results:
        logger.info(
            "fetch_campaign_level_cm1_roi: no rows for ce_id=%s window %s..%s",
            ce_id, start, end,
        )
        return []
    return results


# ============================================================================
# PHASE 2: COMPETITOR BQ FALLBACK
# ============================================================================

def fetch_competitors_bq(ce_id, tw_start, tw_end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Return top-10 competitors from `competitor_weekly_stats` for this CE.

    This is the BQ-fallback tier for competitor naming. Coverage is thin —
    `competitor_weekly_stats` only surfaces COMPETITORS MAPPED TO HEADOUT
    (Louvre returned only "Get Your Guide" across a 4-week window in probe
    2026-04-20). Still useful as a floor when the primary sheet-cache isn't
    populated for a market.

    Aggregates over a 4-week-ish window (caller passes tw_start/tw_end — we
    SUM weekly_gbv / weekly_bookings across the range and take ANY_VALUE of
    trailing_4_week_gbv as a freshness proxy).

    Args:
        ce_id: Combined entity ID (int). Cast to string inside SQL filter
            (combined_entity_id is a STRING column on competitor_weekly_stats).
        tw_start, tw_end: Inclusive window boundaries.

    Returns:
        List of dicts with keys:
            competitor_name, is_mapped_to_headout, gbv_4w, bookings_4w, trailing_gbv
        Sorted by gbv_4w DESC, at most 10 rows. Empty list on no data
        (caller returns None from the unified fetcher only if upstream
        tiers also returned nothing).
    """
    query = """
    SELECT
        competitor_name,
        ANY_VALUE(is_mapped_to_headout) AS is_mapped_to_headout,
        SUM(COALESCE(weekly_gbv, 0)) AS gbv_4w,
        SUM(COALESCE(weekly_bookings, 0)) AS bookings_4w,
        ANY_VALUE(trailing_4_week_gbv) AS trailing_gbv
    FROM `{project}.{dataset}.competitor_weekly_stats`
    WHERE combined_entity_id = '{ce_id}'
        AND week BETWEEN '{start}' AND '{end}'
    GROUP BY competitor_name
    ORDER BY gbv_4w DESC
    LIMIT 10
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        ce_id=ce_id,
        start=tw_start.strftime("%Y-%m-%d"),
        end=tw_end.strftime("%Y-%m-%d"),
    )

    results = run_bq_query(query)
    if not results:
        logger.info(
            "fetch_competitors_bq: no rows for ce_id=%s window %s..%s",
            ce_id, tw_start, tw_end,
        )
        return []
    return results


# ============================================================================
# PHASE 7.5a: DEVICE SPLIT
# ============================================================================

def fetch_device_split(ce_id, tw_start, tw_end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Device-segmented stats from campaign_device_stats.

    Returns rows: {device, spend, clicks, impressions, conversions, conversion_value}.

    Source: campaign_device_stats (Google Ads portion, filtered by
    advertising_channel_source = 'Google Ads' and campaign_combined_entity_id).

    Note: campaign_device_stats uses 'date' column (not 'report_date') and
    'campaign_combined_entity_id' (not 'campaign_target_combined_entity_id').

    Args:
        ce_id: Combined entity ID.
        tw_start: Window start date (inclusive).
        tw_end: Window end date (inclusive).

    Returns:
        List of device dicts, one row per device. Empty list on no data.
    """
    query = """
    SELECT
        device,
        SUM(sum_spend) AS spend,
        SUM(count_clicks) AS clicks,
        SUM(count_impressions) AS impressions,
        SUM(COALESCE(count_conversions, 0)) AS conversions,
        SUM(COALESCE(sum_conversion_value, 0)) AS conversion_value
    FROM `{project}.{dataset}.campaign_device_stats`
    WHERE campaign_combined_entity_id = '{ce_id}'
        AND date BETWEEN '{start}' AND '{end}'
        AND advertising_channel_source = 'Google Ads'
    GROUP BY device
    ORDER BY spend DESC
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        ce_id=ce_id,
        start=tw_start.strftime("%Y-%m-%d"),
        end=tw_end.strftime("%Y-%m-%d"),
    )

    results = run_bq_query(query)
    if not results:
        logger.info(
            "fetch_device_split: no rows for ce_id=%s window %s..%s",
            ce_id, tw_start, tw_end,
        )
        return []
    return results


# ============================================================================
# V6: CHANNEL BREAKDOWN (BQ attribution — zoom-out-first)
# ============================================================================

def fetch_channel_breakdown(
    ce_id,       # type: int
    tw_start,    # type: date
    tw_end,      # type: date
    ly_start,    # type: date
    ly_end,      # type: date
    prior_4w_start,  # type: date
    prior_4w_end,    # type: date
):
    # type: (...) -> Dict[str, List[Dict[str, Any]]]
    """Channel-level revenue + paid metrics for CE Snapshot Table 3.

    Revenue/orders from fct_orders (ground truth attribution).
    Paid metrics (spend, clicks, CVR, CM1, ROI) from ads_campaign_stats +
    google_ads_pmax_asset_stats. Merged by channel name.

    Channel taxonomy (v6.1):
        Google Search, Google Cross-sell, Google PMax,
        Bing, Bing Cross-sell, TTD (Paid), TTD (Organic),
        CPR, Organic, Direct, Direct (App), Affiliates, Email, Other.

    Returns dict with keys 'tw', 'ly', 'prior_4w', 'monthly'.
    First three map to channel dicts. 'monthly' maps to L12M aggregate
    monthly data (combined_entity_stats + ads_campaign_stats) for trajectory
    analysis in the snapshot narrative.
    """
    return {
        "tw": _fetch_channel_window_v2(ce_id, tw_start, tw_end),
        "ly": _fetch_channel_window_v2(ce_id, ly_start, ly_end),
        "prior_4w": _fetch_channel_window_v2(ce_id, prior_4w_start, prior_4w_end),
        "monthly": _fetch_monthly_summary(ce_id),
    }


def _fetch_monthly_summary(ce_id):
    # type: (int) -> List[Dict[str, Any]]
    """L12M monthly aggregate for snapshot trajectory analysis.

    Returns CE-level (Table 1) and paid-level (Table 2) metrics per month
    using the validated Omni-matched formulas. Feeds the snapshot analysis
    with trajectory context: "ROI declined from 185% (Nov) → 148% (now)."
    """
    query = """
    WITH ce_monthly AS (
        SELECT
            SUBSTR(CAST(report_date AS STRING), 1, 7) AS month,
            SUM(sum_revenue_predicted) AS revenue,
            SUM(sum_revenue) AS revenue_actual,
            SUM(sum_order_value) AS gross_bookings,
            SUM(sum_order_value_completed) AS gross_bookings_completed,
            SUM(count_orders) AS orders,
            SUM(sum_direct_costs) AS direct_costs,
            SUM(sum_google_ads_spend + sum_microsoft_ads_spend + sum_pmax_ads_spend
                + sum_travel_ads_spend + sum_facebook_ads_spend
                + sum_google_remarketing_ads_spend + sum_facebook_remarketing_ads_spend
                + sum_criteo_remarketing_ads_spend + sum_google_brand_ads_spend
                + sum_apple_ads_spend + sum_google_split_ads_spend
                + sum_microsoft_split_ads_spend + sum_facebook_split_ads_spend
                + sum_coupon_discount + sum_wallet_credits
                + sum_affiliate_commission) AS gross_marketing_cost
        FROM `{project}.{dataset}.combined_entity_stats`
        WHERE combined_entity_id = '{ce_id}'
            AND report_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)
                AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        GROUP BY 1
    ),
    paid_monthly AS (
        SELECT
            SUBSTR(CAST(report_date AS STRING), 1, 7) AS month,
            SUM(count_clicks) AS clicks,
            SUM(sum_spend) AS ad_spend,
            SUM(CASE
                WHEN report_date > '2025-09-01'
                    AND COALESCE(count_conversions_offline_contribution_margin, 0) > 0
                THEN count_conversions_offline_contribution_margin
                ELSE count_conversions_online
            END) AS conversions,
            SUM(CASE
                WHEN report_date > '2025-09-01'
                    AND COALESCE(sum_conversion_value_offline_contribution_margin, 0) > 0
                THEN sum_conversion_value_offline_contribution_margin
                ELSE sum_conversion_value_calculated_contribution_margin
            END) AS cm1,
            SUM(sum_coupon_and_wallet_credits) AS coupon_wallet
        FROM `{project}.{dataset}.ads_campaign_stats`
        WHERE campaign_target_combined_entity_id = '{ce_id}'
            AND report_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)
                AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
            AND ad_platform IN ('Google Ads', 'Microsoft Ads')
        GROUP BY 1
    ),
    pmax_monthly AS (
        -- PMax spend/clicks/conversions: asset-stats (Omni-validated, CID-gated).
        -- CM1 (value) is NOT taken here — sum_conversion_value × revenue_percentage
        -- understates ~4× post-Sep-2025 (see _fetch_pmax_value). Value comes from
        -- pmax_value_monthly (fct_orders) below.
        SELECT
            SUBSTR(CAST(date AS STRING), 1, 7) AS month,
            SUM(count_clicks) AS clicks,
            SUM(sum_cost) AS spend,
            SUM(count_conversions) AS conversions
        FROM `{project}.{dataset}.google_ads_pmax_asset_stats`
        WHERE combined_entity_id = '{ce_id}'
            AND date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)
                AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        GROUP BY 1
    ),
    pmax_value_monthly AS (
        -- PMax CM1 (value) from fct_orders PMax-channel orders, CE-attributed
        -- ground truth (mirrors _fetch_pmax_value). Gated downstream on PMax
        -- clicks existing so a CE without a dedicated asset group reads $0,
        -- consistent with the headline window paths.
        SELECT
            SUBSTR(CAST(DATE(created_at) AS STRING), 1, 7) AS month,
            SUM(amount_revenue_usd - amount_direct_costs_usd) AS cm1
        FROM `{project}.{dataset}.fct_orders`
        WHERE combined_entity_id = '{ce_id}'
            AND DATE(created_at) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)
                AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
            AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
            AND user_type = 'Customer'
            AND channel_name = 'Google Ads'
            AND REGEXP_CONTAINS(LOWER(COALESCE(campaign_name, '')), r'pmax|performance.max')
        GROUP BY 1
    )
    SELECT
        c.month,
        c.revenue,
        c.orders,
        SAFE_DIVIDE(c.revenue - c.direct_costs, c.gross_marketing_cost) AS roi_1,
        SAFE_DIVIDE(c.revenue_actual, c.gross_bookings_completed) AS tr,
        SAFE_DIVIDE(c.gross_bookings_completed, c.gross_bookings) AS cr,
        SAFE_DIVIDE(c.gross_bookings, c.orders) AS aov,
        COALESCE(p.clicks, 0) + COALESCE(pm.clicks, 0) AS paid_clicks,
        COALESCE(p.ad_spend, 0) + COALESCE(pm.spend, 0) AS paid_spend,
        COALESCE(p.cm1, 0)
            + (CASE WHEN COALESCE(pm.clicks, 0) > 0 THEN COALESCE(pv.cm1, 0) ELSE 0 END) AS paid_cm1,
        SAFE_DIVIDE(
            COALESCE(p.cm1, 0)
                + (CASE WHEN COALESCE(pm.clicks, 0) > 0 THEN COALESCE(pv.cm1, 0) ELSE 0 END),
            COALESCE(p.ad_spend, 0) + COALESCE(pm.spend, 0) + COALESCE(p.coupon_wallet, 0)
        ) AS paid_roi,
        SAFE_DIVIDE(
            COALESCE(p.ad_spend, 0) + COALESCE(pm.spend, 0),
            COALESCE(p.clicks, 0) + COALESCE(pm.clicks, 0)
        ) AS paid_cpc,
        SAFE_DIVIDE(
            COALESCE(p.conversions, 0) + COALESCE(pm.conversions, 0),
            COALESCE(p.clicks, 0) + COALESCE(pm.clicks, 0)
        ) AS paid_cvr
    FROM ce_monthly c
    LEFT JOIN paid_monthly p USING (month)
    LEFT JOIN pmax_monthly pm USING (month)
    LEFT JOIN pmax_value_monthly pv USING (month)
    ORDER BY c.month
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        ce_id=ce_id,
    )

    results = run_bq_query(query)
    if not results:
        logger.info(
            "_fetch_monthly_summary: no rows for ce_id=%s", ce_id,
        )
        return []
    return results


def _fetch_channel_window_v2(ce_id, start, end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Revenue (fct_orders) + paid metrics (ads_campaign_stats + pmax_asset_stats).

    Channel taxonomy v6.1 — clearer names than v6:
        Google Same Cat -> Google Search
        Google Others   -> Google Cross-sell
        Bing Same Cat   -> Bing
        Bing Others     -> Bing Cross-sell
    Handles Bing misclassification (channel_name='Google Ads' + campaign '1 - ').
    """
    # ── Part 1: Revenue from fct_orders ──
    rev_query = """
    WITH classified AS (
        SELECT
            CASE
                WHEN channel_name = 'Google Ads'
                    AND REGEXP_CONTAINS(campaign_name, CONCAT('cid', CAST(combined_entity_id AS STRING)))
                    THEN 'Google Search'
                WHEN channel_name = 'Google Ads'
                    AND campaign_name LIKE '1 - %%'
                    THEN 'Bing'
                WHEN channel_name = 'Bing Ads'
                    AND REGEXP_CONTAINS(campaign_name, CONCAT('cid', CAST(combined_entity_id AS STRING)))
                    THEN 'Bing'
                WHEN channel_name = 'Google Ads'
                    AND REGEXP_CONTAINS(LOWER(COALESCE(campaign_name, '')), r'pmax|performance.max')
                    THEN 'Google PMax'
                WHEN channel_name = 'Google Ads'
                    THEN 'Google Cross-sell'
                WHEN channel_name = 'Bing Ads'
                    THEN 'Bing Cross-sell'
                WHEN channel_name = 'Things to Do (Ads)'
                    THEN 'TTD (Paid)'
                WHEN channel_name = 'Things to Do (Organic)'
                    THEN 'TTD (Organic)'
                WHEN channel_name = 'Confirmation Page Recommendations'
                    THEN 'CPR'
                WHEN channel_name = 'Organic Search'
                    THEN 'Organic'
                WHEN channel_grouping = 'Direct (App)'
                    THEN 'Direct (App)'
                WHEN channel_grouping = 'Direct'
                    THEN 'Direct'
                WHEN channel_grouping = 'Affiliates'
                    THEN 'Affiliates'
                WHEN channel_grouping = 'Email'
                    THEN 'Email'
                WHEN channel_grouping = 'Referral'
                    THEN 'Referral'
                ELSE 'Other'
            END AS channel,
            amount_revenue_usd AS revenue,
            order_value_usd AS order_value,
            order_value_completed_usd AS order_value_completed,
            1 AS order_count
        FROM `{project}.{dataset}.fct_orders`
        WHERE combined_entity_id = '{ce_id}'
            AND DATE(created_at) BETWEEN '{start}' AND '{end}'
            AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
            AND user_type = 'Customer'
    )
    SELECT
        channel,
        ROUND(SUM(revenue), 2) AS revenue,
        SUM(order_count) AS orders,
        ROUND(SAFE_DIVIDE(SUM(order_value), SUM(order_count)), 2) AS aov,
        ROUND(SAFE_DIVIDE(SUM(revenue), NULLIF(SUM(order_value_completed), 0)) * 100, 2) AS tr,
        ROUND(SAFE_DIVIDE(SUM(order_value_completed), NULLIF(SUM(order_value), 0)) * 100, 2) AS cr
    FROM classified
    GROUP BY channel
    HAVING orders > 0
    ORDER BY revenue DESC
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
    )

    rev_rows = run_bq_query(rev_query)
    if not rev_rows:
        logger.info(
            "fetch_channel_breakdown: no revenue rows for ce_id=%s window %s..%s",
            ce_id, start, end,
        )
        return []

    # ── Part 2: Paid metrics from ads_campaign_stats (Google Search + Bing) ──
    paid_query = """
    SELECT
        CASE
            WHEN ad_platform = 'Google Ads' AND campaign_advertising_channel_type = 'SEARCH'
                THEN 'Google Search'
            WHEN ad_platform = 'Google Ads' AND campaign_advertising_channel_type = 'PERFORMANCE_MAX'
                THEN 'Google PMax'
            WHEN ad_platform = 'Google Ads'
                THEN 'Google Cross-sell'
            WHEN ad_platform = 'Microsoft Ads'
                THEN 'Bing'
            ELSE ad_platform
        END AS channel,
        SUM(count_clicks) AS clicks,
        SUM(count_impressions) AS impressions,
        SUM(sum_spend) AS spend,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(count_conversions_offline_contribution_margin, 0) > 0
            THEN count_conversions_offline_contribution_margin
            ELSE count_conversions_online
        END) AS conversions,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(sum_conversion_value_offline_revenue, 0) > 0
            THEN sum_conversion_value_offline_revenue
            ELSE sum_conversion_value_calculated_revenue
        END) AS paid_rev,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(sum_conversion_value_offline_contribution_margin, 0) > 0
            THEN sum_conversion_value_offline_contribution_margin
            ELSE sum_conversion_value_calculated_contribution_margin
        END) AS cm1,
        SUM(sum_coupon_and_wallet_credits) AS coupon_wallet
    FROM `{project}.{dataset}.ads_campaign_stats`
    WHERE campaign_target_combined_entity_id = '{ce_id}'
        AND report_date BETWEEN '{start}' AND '{end}'
        AND ad_platform IN ('Google Ads', 'Microsoft Ads')
    GROUP BY 1
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
    )

    paid_rows = run_bq_query(paid_query) or []
    paid_map = {}
    for row in paid_rows:
        ch = row["channel"]
        clicks = float(row.get("clicks") or 0)
        spend = float(row.get("spend") or 0)
        conv = float(row.get("conversions") or 0)
        cm1 = float(row.get("cm1") or 0)
        cw = float(row.get("coupon_wallet") or 0)
        paid_rev = float(row.get("paid_rev") or 0)
        mkt_cost = spend + cw
        paid_map[ch] = {
            "clicks": clicks,
            "spend": spend,
            "cpc": spend / clicks if clicks else None,
            "cvr": conv / clicks * 100 if clicks else None,
            "cm1": cm1,
            "roi": cm1 / mkt_cost * 100 if mkt_cost else None,
            "rpc": paid_rev / clicks if clicks else None,
        }

    # ── Part 3: PMax metrics ── spend/clicks/conversions from asset-stats; CM1 from
    # fct_orders (CE-attributed ground truth — asset-stats value unreliable at CE grain).
    pmax_query = """
    SELECT
        SUM(sum_cost) AS spend,
        SUM(count_clicks) AS clicks,
        SUM(count_conversions) AS conversions
    FROM `{project}.{dataset}.google_ads_pmax_asset_stats`
    WHERE combined_entity_id = '{ce_id}'
        AND date BETWEEN '{start}' AND '{end}'
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
    )

    pmax_rows = run_bq_query(pmax_query) or []
    if pmax_rows and pmax_rows[0].get("clicks"):
        p = pmax_rows[0]
        clicks = float(p.get("clicks") or 0)
        spend = float(p.get("spend") or 0)
        conv = float(p.get("conversions") or 0)
        cm1 = _fetch_pmax_value(ce_id, start, end)["cm1"]
        paid_map["Google PMax"] = {
            "clicks": clicks,
            "spend": spend,
            "cpc": spend / clicks if clicks else None,
            "cvr": conv / clicks * 100 if clicks else None,
            "cm1": cm1,
            "roi": cm1 / spend * 100 if spend else None,
            "rpc": None,  # RPC uses fct_orders revenue, set below
        }

    # ── Merge revenue + paid metrics ──
    merged = []
    for row in rev_rows:
        ch = row["channel"]
        entry = {
            "channel": ch,
            "revenue": float(row.get("revenue") or 0),
            "orders": int(row.get("orders") or 0),
            "aov": float(row.get("aov") or 0),
            "tr": float(row.get("tr") or 0) if row.get("tr") else None,
            "cr": float(row.get("cr") or 0) if row.get("cr") else None,
        }
        pm = paid_map.get(ch)
        if pm:
            entry.update({
                "clicks": pm["clicks"],
                "spend": pm["spend"],
                "cpc": pm["cpc"],
                "cvr": pm["cvr"],
                "cm1": pm["cm1"],
                "roi": pm["roi"],
                "rpc": pm.get("rpc") or (
                    entry["revenue"] / pm["clicks"] if pm["clicks"] else None
                ),
            })
        else:
            entry.update({
                "clicks": None, "spend": None, "cpc": None,
                "cvr": None, "cm1": None, "roi": None, "rpc": None,
            })
        merged.append(entry)

    return merged


# ============================================================================
# V6: CAMPAIGN COHORT TABLE (Channel x Language x Geo — the backbone)
# ============================================================================

def fetch_campaign_cohorts(
    ce_id,       # type: int
    tw_start,    # type: date
    tw_end,      # type: date
    ly_start,    # type: date
    ly_end,      # type: date
    prior_4w_start,  # type: date
    prior_4w_end,    # type: date
):
    # type: (...) -> Dict[str, List[Dict[str, Any]]]
    """Campaign-level metrics grouped by Channel x Language for 3 temporal windows.

    Uses google_ads_campaign_stats (primary paid channel) with campaign_language
    and campaign_name for cohort grouping. Includes tROAS, budget, status.

    Returns dict with keys 'tw', 'ly', 'prior_4w'. Each maps to a list of
    campaign-group dicts.
    """
    return {
        "tw": _fetch_cohort_window(ce_id, tw_start, tw_end),
        "ly": _fetch_cohort_window(ce_id, ly_start, ly_end),
        "prior_4w": _fetch_cohort_window(ce_id, prior_4w_start, prior_4w_end),
        "monthly": _fetch_cohort_monthly(ce_id),
    }


def _fetch_cohort_monthly(ce_id):
    # type: (int) -> List[Dict[str, Any]]
    """L12M monthly metrics per language cohort for trajectory analysis.

    Groups by campaign_language × month. Uses ads_campaign_stats with
    validated metric formulas (Sep 2025 boundary for CM1/CVR).
    Returns list of dicts with month, cohort, and key metrics.
    """
    query = """
    SELECT
        SUBSTR(CAST(report_date AS STRING), 1, 7) AS month,
        COALESCE(campaign_language, 'EN') AS cohort,
        SUM(sum_spend) AS spend,
        SUM(count_clicks) AS clicks,
        SUM(count_impressions) AS impressions,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(count_conversions_offline_contribution_margin, 0) > 0
            THEN count_conversions_offline_contribution_margin
            ELSE count_conversions_online
        END) AS conversions,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(sum_conversion_value_offline_contribution_margin, 0) > 0
            THEN sum_conversion_value_offline_contribution_margin
            ELSE sum_conversion_value_calculated_contribution_margin
        END) AS cm1,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(sum_conversion_value_offline_revenue, 0) > 0
            THEN sum_conversion_value_offline_revenue
            ELSE sum_conversion_value_calculated_revenue
        END) AS revenue,
        SUM(sum_coupon_and_wallet_credits) AS coupon_wallet,
        SAFE_DIVIDE(SUM(count_impressions), SUM(count_eligible_searches)) AS sis
    FROM `{project}.{dataset}.ads_campaign_stats`
    WHERE campaign_target_combined_entity_id = '{ce_id}'
        AND report_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)
            AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND ad_platform IN ('Google Ads', 'Microsoft Ads')
    GROUP BY 1, 2
    ORDER BY 1, 2
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        ce_id=ce_id,
    )

    results = run_bq_query(query)
    if not results:
        logger.info(
            "_fetch_cohort_monthly: no rows for ce_id=%s", ce_id,
        )
        return []

    # Derive metrics per row
    enriched = []
    for row in results:
        clicks = float(row.get("clicks") or 0)
        spend = float(row.get("spend") or 0)
        conv = float(row.get("conversions") or 0)
        cm1 = float(row.get("cm1") or 0)
        rev = float(row.get("revenue") or 0)
        cw = float(row.get("coupon_wallet") or 0)
        mkt = spend + cw
        enriched.append({
            "month": row["month"],
            "cohort": row["cohort"],
            "spend": spend,
            "clicks": clicks,
            "cm1": cm1,
            "revenue": rev,
            "cpc": spend / clicks if clicks else None,
            "cvr": conv / clicks * 100 if clicks else None,
            "roi": cm1 / mkt * 100 if mkt else None,
            "rpc": rev / clicks if clicks else None,
            "sis": float(row.get("sis") or 0) * 100 if row.get("sis") else None,
        })
    return enriched


def _fetch_cohort_window(ce_id, start, end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Language cohort data from fct_orders (revenue) + google_ads_campaign_stats (paid metrics).

    v6.1: Uses fct_orders direct classification (campaign_name) instead of touchpoint
    attribution. This ensures Cohort TOTAL = Table 3 Google Search row (same source,
    same classification logic). Language extracted from campaign_name pattern.
    """
    # ── Revenue side: fct_orders direct, grouped by language ──
    rev_query = """
    SELECT
        CASE
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)english') THEN 'English'
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)spanish') THEN 'Spanish'
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)other.languages') THEN 'Other Languages'
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)french') THEN 'French'
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)german') THEN 'German'
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)italian') THEN 'Italian'
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)portuguese') THEN 'Portuguese'
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)dutch') THEN 'Dutch'
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)polish') THEN 'Polish'
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)russian') THEN 'Russian'
            WHEN REGEXP_CONTAINS(campaign_name, r'(?i)turkish') THEN 'Turkish'
            ELSE 'Other'
        END AS cohort,
        COUNT(DISTINCT order_id) AS orders,
        SUM(amount_revenue_usd) AS revenue,
        SUM(order_value_usd) AS order_value,
        SUM(order_value_completed_usd) AS order_value_completed,
        SUM(amount_direct_costs_usd) AS direct_costs
    FROM `{project}.{dataset}.fct_orders`
    WHERE combined_entity_id = '{ce_id}'
        AND DATE(created_at) BETWEEN '{start}' AND '{end}'
        AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
        AND user_type = 'Customer'
        AND channel_name = 'Google Ads'
        AND REGEXP_CONTAINS(campaign_name, CONCAT('cid', '{ce_id}'))
        AND NOT REGEXP_CONTAINS(LOWER(COALESCE(campaign_name, '')), r'pmax|performance.max')
    GROUP BY 1
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )

    # ── Paid side: google_ads_campaign_stats, grouped by campaign_language ──
    paid_query = """
    SELECT
        COALESCE(campaign_language, 'EN') AS cohort_key,
        SUM(sum_spend) AS spend,
        SUM(count_clicks) AS clicks,
        SUM(count_impressions) AS impressions,
        SUM(COALESCE(sum_coupon_and_wallet_credits, 0)) AS coupon_wallet,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(count_conversions_offline_contribution_margin, 0) > 0
            THEN count_conversions_offline_contribution_margin
            ELSE count_conversions_online
        END) AS conversions,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(sum_conversion_value_offline_contribution_margin, 0) > 0
            THEN sum_conversion_value_offline_contribution_margin
            ELSE sum_conversion_value_calculated_contribution_margin
        END) AS cm1,
        SAFE_DIVIDE(SUM(count_impressions), NULLIF(SUM(count_eligible_searches), 0)) AS true_sis,
        SAFE_DIVIDE(SUM(count_rank_lost_searches), NULLIF(SUM(count_eligible_searches), 0)) AS avg_rank_lost,
        SAFE_DIVIDE(SUM(count_budget_lost_searches), NULLIF(SUM(count_eligible_searches), 0)) AS avg_budget_lost
    FROM `{project}.{dataset}.google_ads_campaign_stats`
    WHERE campaign_target_combined_entity_id = '{ce_id}'
        AND report_date BETWEEN '{start}' AND '{end}'
    GROUP BY 1
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )

    rev_rows = run_bq_query(rev_query) or []
    paid_rows = run_bq_query(paid_query) or []

    if not rev_rows and not paid_rows:
        logger.info(
            "fetch_campaign_cohorts: no rows for ce_id=%s window %s..%s",
            ce_id, start, end,
        )
        return []

    # Map campaign_language codes to fct_orders language names
    lang_map = {
        "EN": "English", "ES": "Spanish", "OL": "Other Languages",
        "FR": "French", "DE": "German", "IT": "Italian",
        "PT": "Portuguese", "NL": "Dutch", "PL": "Polish",
        "RU": "Russian", "TR": "Turkish", "All": "Other",
    }

    # Build paid metrics lookup by cohort name
    paid_map = {}
    for row in paid_rows:
        key = row.get("cohort_key", "EN")
        cohort_name = lang_map.get(key, key)
        if cohort_name not in paid_map:
            paid_map[cohort_name] = {k: 0 for k in [
                "spend", "clicks", "impressions", "coupon_wallet",
                "conversions", "cm1", "impr_for_sis", "eligible_for_sis",
                "rank_lost", "budget_lost",
            ]}
        pm = paid_map[cohort_name]
        cl = float(row.get("clicks") or 0)
        pm["spend"] += float(row.get("spend") or 0)
        pm["clicks"] += cl
        pm["impressions"] += float(row.get("impressions") or 0)
        pm["coupon_wallet"] += float(row.get("coupon_wallet") or 0)
        pm["conversions"] += float(row.get("conversions") or 0)
        pm["cm1"] += float(row.get("cm1") or 0)
        # SIS = impressions / eligible_searches (true SIS, not AVG)
        sis = row.get("true_sis")
        if sis:
            pm["impr_for_sis"] = pm["impressions"]  # use total impressions
            pm["eligible_for_sis"] = pm["impressions"] / float(sis) if float(sis) > 0 else 0
        pm["rank_lost"] = float(row.get("avg_rank_lost") or 0)
        pm["budget_lost"] = float(row.get("avg_budget_lost") or 0)

    # Merge revenue + paid into cohort results
    merged = []
    for row in rev_rows:
        cohort = row["cohort"]
        rev = float(row.get("revenue") or 0)
        orders = int(row.get("orders") or 0)
        ov = float(row.get("order_value") or 0)
        ovc = float(row.get("order_value_completed") or 0)

        pm = paid_map.get(cohort, {})
        cl = pm.get("clicks", 0)
        sp = pm.get("spend", 0)
        cw = pm.get("coupon_wallet", 0)
        conv = pm.get("conversions", 0)
        cm1 = pm.get("cm1", 0)
        impr = pm.get("impressions", 0)
        mkt = sp + cw

        entry = {
            "cohort": cohort,
            "revenue": rev,
            "orders": orders,
            "order_value": ov,
            "order_value_completed": ovc,
            "spend": sp,
            "clicks": cl,
            "impressions": impr,
            "conversions": conv,
            "coupon_wallet": cw,
            "cm1": cm1,
            "avg_sis": pm["impr_for_sis"] / pm["eligible_for_sis"] * 100 if pm.get("eligible_for_sis") else None,
            "avg_rank_lost": pm.get("rank_lost"),
            "avg_budget_lost": pm.get("budget_lost"),
            # Derived metrics
            "rpc": rev / cl if cl else None,
            "cpc": sp / cl if cl else None,
            "ctr": cl / impr * 100 if impr else None,
            "cvr": conv / cl * 100 if cl else None,
            "aov": ov / orders if orders else None,
            "avg_cm1": cm1 / conv if conv else None,
            "tr": rev / ovc * 100 if ovc else None,
            "cr": ovc / ov * 100 if ov else None,
            "roi": cm1 / mkt * 100 if mkt else None,
        }
        merged.append(entry)

    merged.sort(key=lambda x: -x["revenue"])
    return merged


# ============================================================================
# V6: CUSTOMER COUNTRY DISTRIBUTION (for geo gap analysis)
# ============================================================================

def fetch_customer_country_distribution(ce_id, tw_start, tw_end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Customer country distribution from fct_orders.

    Used in Section 4a geo gap analysis: compare where customers come from
    vs where ads serve to flag under-served feeder markets.
    Uses the date window as passed (caller controls L4W vs L12M).
    """
    query = """
    SELECT
        card_issuing_country AS customer_country,
        COUNT(DISTINCT order_id) AS orders,
        SUM(amount_revenue_usd) AS revenue
    FROM `{project}.{dataset}.fct_orders`
    WHERE combined_entity_id = '{ce_id}'
        AND DATE(created_at) BETWEEN '{start}' AND '{end}'
        AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
        AND user_type = 'Customer'
        AND card_issuing_country IS NOT NULL
    GROUP BY 1
    ORDER BY orders DESC
    LIMIT 20
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        ce_id=ce_id,
        start=tw_start.strftime("%Y-%m-%d"),
        end=tw_end.strftime("%Y-%m-%d"),
    )

    results = run_bq_query(query)
    if not results:
        logger.info(
            "fetch_customer_country_distribution: no rows for ce_id=%s",
            ce_id,
        )
        return []
    return results


def fetch_customer_country_3w(ce_id, l4w, ly):
    # type: (int, Tuple[date,date], Tuple[date,date]) -> Dict[str, List]
    """Customer country for L4W and LY. Returns {l4w: [...], ly: [...]}."""
    return {
        "l4w": fetch_customer_country_distribution(ce_id, l4w[0], l4w[1]),
        "ly": fetch_customer_country_distribution(ce_id, ly[0], ly[1]),
    }


# ============================================================================
# ALL-PAID METRICS (CE Snapshot Table 1)
# ============================================================================

def fetch_all_paid_metrics(
    ce_id,     # type: int
    tw_start,  # type: date
    tw_end,    # type: date
    p4w_start, # type: date
    p4w_end,   # type: date
    ly_start,  # type: date
    ly_end,    # type: date
):
    # type: (...) -> Dict[str, Dict[str, Any]]
    """Fetch all-paid metrics across Google + Bing + PMax for CE Snapshot.

    Combines:
    - combined_entity_stats: count_ad_clicks, count_ad_impressions,
      sum_google_ads_spend + sum_microsoft_ads_spend + sum_pmax_ads_spend
    - fct_orders WHERE channel_grouping = 'Paid': paid orders + paid revenue

    Returns dict with keys 'tw', 'p4w', 'ly', each containing:
      paid_clicks, paid_impressions, paid_spend, paid_orders, paid_revenue,
      paid_cpc, paid_cvr
    """
    results = {}
    windows = [
        ("tw", tw_start, tw_end),
        ("p4w", p4w_start, p4w_end),
        ("ly", ly_start, ly_end),
    ]

    for label, start, end in windows:
        ads_query = """
        SELECT
            ROUND(SUM(count_ad_clicks), 0) AS paid_clicks,
            ROUND(SUM(count_ad_impressions), 0) AS paid_impressions,
            ROUND(SUM(
                COALESCE(sum_google_ads_spend, 0)
                + COALESCE(sum_microsoft_ads_spend, 0)
                + COALESCE(sum_pmax_ads_spend, 0)
            ), 0) AS paid_spend
        FROM `{project}.{dataset}.combined_entity_stats`
        WHERE combined_entity_id = '{ce_id}'
            AND report_date BETWEEN '{start}' AND '{end}'
        """.format(
            project=PROJECT_ID,
            dataset=DATASET,
            ce_id=ce_id,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
        )

        orders_query = """
        SELECT
            COUNT(*) AS paid_orders,
            ROUND(SUM(amount_revenue_usd), 0) AS paid_revenue
        FROM `{project}.{dataset}.fct_orders`
        WHERE combined_entity_id = '{ce_id}'
            AND order_status = 'Completed'
            AND channel_grouping = 'Paid'
            AND DATE(created_at) BETWEEN '{start}' AND '{end}'
        """.format(
            project=PROJECT_ID,
            dataset=DATASET,
            ce_id=ce_id,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
        )

        ads_rows = run_bq_query(ads_query)
        orders_rows = run_bq_query(orders_query)

        ads = ads_rows[0] if ads_rows else {}
        orders = orders_rows[0] if orders_rows else {}

        clicks = float(ads.get("paid_clicks", 0) or 0)
        spend = float(ads.get("paid_spend", 0) or 0)
        paid_orders = int(orders.get("paid_orders", 0) or 0)
        paid_revenue = float(orders.get("paid_revenue", 0) or 0)

        results[label] = {
            "paid_clicks": int(clicks),
            "paid_impressions": int(float(ads.get("paid_impressions", 0) or 0)),
            "paid_spend": spend,
            "paid_orders": paid_orders,
            "paid_revenue": paid_revenue,
            "paid_cpc": round(spend / clicks, 2) if clicks > 0 else 0,
            "paid_cvr": round(paid_orders / clicks, 4) if clicks > 0 else 0,
        }

    return results


# ============================================================================
# PHASE 7.5b: MARKET BENCHMARKS
# ============================================================================

def fetch_market_benchmarks(
    market,    # type: str
    ce_id,     # type: int
    tw_start,  # type: date
    tw_end,    # type: date
    ly_start,  # type: date
    ly_end,    # type: date
):
    # type: (...) -> Optional[Dict[str, Any]]
    """Fetch market-level medians for CEs in the same market (excluding this CE).

    Queries combined_entity_stats + ads_campaign_stats with APPROX_QUANTILES
    for market medians of SIS, CPC, CTR, CVR, ROAS.

    Returns None if the market has fewer than 3 other CEs with ads data.

    Args:
        market: Market name (e.g., "France").
        ce_id: Combined entity ID for this CE (excluded from medians).
        tw_start: This-window start date (inclusive).
        tw_end: This-window end date (inclusive).
        ly_start: Last-year window start date (inclusive).
        ly_end: Last-year window end date (inclusive).

    Returns:
        Dict with keys: median_sis, median_cpc, median_ctr, median_cvr,
        median_roas, market_rev_delta_pct, n_ces, this_ce_rank_by_rev.
        None if < 3 peer CEs in market or no data.
    """
    query = """
    WITH ce_stats AS (
        SELECT
            c.combined_entity_id,
            SUM(CASE WHEN c.report_date BETWEEN '{tw_start}' AND '{tw_end}' THEN c.sum_revenue ELSE 0 END) AS tw_revenue,
            SUM(CASE WHEN c.report_date BETWEEN '{ly_start}' AND '{ly_end}' THEN c.sum_revenue ELSE 0 END) AS ly_revenue
        FROM `{project}.{dataset}.combined_entity_stats` c
        JOIN `{project}.{dataset}.dim_combined_entities` d
            ON c.combined_entity_id = d.combined_entity_id
        WHERE d.market = '{market}'
            AND c.report_date BETWEEN '{ly_start}' AND '{tw_end}'
        GROUP BY 1
        HAVING tw_revenue > 0 OR ly_revenue > 0
    ),
    ads_stats AS (
        SELECT
            a.campaign_target_combined_entity_id AS ce_id,
            AVG(a.search_impression_share) AS avg_sis,
            SAFE_DIVIDE(SUM(a.sum_spend), SUM(a.count_clicks)) AS cpc,
            SAFE_DIVIDE(SUM(a.count_clicks), NULLIF(SUM(a.count_impressions), 0)) AS ctr,
            SAFE_DIVIDE(SUM(COALESCE(a.count_conversions_online, 0)), NULLIF(SUM(a.count_clicks), 0)) AS cvr,
            SAFE_DIVIDE(SUM(COALESCE(a.sum_conversion_value_online, 0)), NULLIF(SUM(a.sum_spend), 0)) AS roas
        FROM `{project}.{dataset}.ads_campaign_stats` a
        JOIN `{project}.{dataset}.dim_combined_entities` d
            ON a.campaign_target_combined_entity_id = d.combined_entity_id
        WHERE d.market = '{market}'
            AND a.report_date BETWEEN '{tw_start}' AND '{tw_end}'
            AND a.ad_platform = 'Google Ads'
            AND a.campaign_target_combined_entity_id != '{ce_id}'
        GROUP BY 1
        HAVING SUM(a.sum_spend) > 0
    ),
    market_agg AS (
        SELECT
            SUM(tw_revenue) AS market_tw_rev,
            SUM(ly_revenue) AS market_ly_rev
        FROM ce_stats
    ),
    medians AS (
        SELECT
            APPROX_QUANTILES(avg_sis, 100)[OFFSET(50)] AS median_sis,
            APPROX_QUANTILES(cpc, 100)[OFFSET(50)] AS median_cpc,
            APPROX_QUANTILES(ctr, 100)[OFFSET(50)] AS median_ctr,
            APPROX_QUANTILES(cvr, 100)[OFFSET(50)] AS median_cvr,
            APPROX_QUANTILES(roas, 100)[OFFSET(50)] AS median_roas,
            COUNT(*) AS n_ces
        FROM ads_stats
    ),
    ce_rank AS (
        SELECT
            RANK() OVER (ORDER BY tw_revenue DESC) AS rank_by_rev
        FROM ce_stats
        WHERE combined_entity_id = '{ce_id}'
    )
    SELECT
        m.median_sis,
        m.median_cpc,
        m.median_ctr,
        m.median_cvr,
        m.median_roas,
        m.n_ces,
        SAFE_DIVIDE(ma.market_tw_rev - ma.market_ly_rev, NULLIF(ma.market_ly_rev, 0)) AS market_rev_delta_pct,
        cr.rank_by_rev AS this_ce_rank_by_rev
    FROM medians m
    CROSS JOIN market_agg ma
    LEFT JOIN ce_rank cr ON TRUE
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        market=market,
        ce_id=ce_id,
        tw_start=tw_start.strftime("%Y-%m-%d"),
        tw_end=tw_end.strftime("%Y-%m-%d"),
        ly_start=ly_start.strftime("%Y-%m-%d"),
        ly_end=ly_end.strftime("%Y-%m-%d"),
    )

    results = run_bq_query(query)
    if not results:
        return None

    row = results[0]
    n_ces = int(row.get("n_ces", 0) or 0)
    if n_ces < 3:
        logger.warning(
            "Market '%s' has only %d other CEs with ads data -- skipping benchmarks",
            market, n_ces,
        )
        return None

    return row


# ============================================================================
# V6.1: CE HEALTH (Table 1) + PAID PERFORMANCE (Table 2)
# + GEO COVERAGE + BUDGET/BIDDING
# ============================================================================

def fetch_ce_health(ce_id, start, end):
    # type: (int, date, date) -> Dict[str, Any]
    """Table 1: CE Health from combined_entity_stats. Single window.

    Returns dict with: revenue, gross_bookings, gross_bookings_completed,
    orders, direct_costs, gross_marketing_cost. Caller derives: ROI(1), TR, CR, AOV.
    """
    query = """
    SELECT
        SUM(sum_revenue_predicted) AS revenue,
        SUM(sum_revenue) AS revenue_actual,
        SUM(sum_order_value) AS gross_bookings,
        SUM(sum_order_value_completed) AS gross_bookings_completed,
        SUM(count_orders) AS orders,
        SUM(sum_direct_costs) AS direct_costs,
        SUM(sum_google_ads_spend + sum_microsoft_ads_spend + sum_pmax_ads_spend
            + sum_travel_ads_spend + sum_facebook_ads_spend
            + sum_google_remarketing_ads_spend + sum_facebook_remarketing_ads_spend
            + sum_criteo_remarketing_ads_spend + sum_google_brand_ads_spend
            + sum_apple_ads_spend + sum_google_split_ads_spend
            + sum_microsoft_split_ads_spend + sum_facebook_split_ads_spend
            + sum_coupon_discount + sum_wallet_credits
            + sum_affiliate_commission) AS gross_marketing_cost
    FROM `{project}.{dataset}.combined_entity_stats`
    WHERE combined_entity_id = '{ce_id}'
        AND report_date BETWEEN '{start}' AND '{end}'
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )
    rows = run_bq_query(query)
    if not rows:
        return {}
    row = rows[0]
    rev = float(row.get("revenue") or 0)
    rev_actual = float(row.get("revenue_actual") or 0)
    gb = float(row.get("gross_bookings") or 0)
    gbc = float(row.get("gross_bookings_completed") or 0)
    orders = int(row.get("orders") or 0)
    dc = float(row.get("direct_costs") or 0)
    gmc = float(row.get("gross_marketing_cost") or 0)
    cm1 = rev - dc
    return {
        "revenue": rev,
        "revenue_actual": rev_actual,
        "orders": orders,
        "roi_1": cm1 / gmc * 100 if gmc else None,
        "tr": rev_actual / gbc * 100 if gbc else None,
        "cr": gbc / gb * 100 if gb else None,
        "aov": gb / orders if orders else None,
        "cm1": cm1,
        "gross_marketing_cost": gmc,
    }


def fetch_ce_health_3w(ce_id, l4w, p4w, ly):
    # type: (int, Tuple[date,date], Tuple[date,date], Tuple[date,date]) -> Dict[str, Dict]
    """Table 1 for all 3 windows. Returns {l4w: {...}, p4w: {...}, ly: {...}}."""
    return {
        "l4w": fetch_ce_health(ce_id, l4w[0], l4w[1]),
        "p4w": fetch_ce_health(ce_id, p4w[0], p4w[1]),
        "ly": fetch_ce_health(ce_id, ly[0], ly[1]),
    }


def fetch_paid_performance(ce_id, start, end):
    # type: (int, date, date) -> Dict[str, Any]
    """Table 2: All Paid Performance (Search + Bing + PMax).

    Merges ads_campaign_stats (Search + Bing) with google_ads_pmax_asset_stats.
    Uses validated Omni formulas (Sep 2025 boundary for CM1/CVR).
    """
    query = """
    SELECT
        SUM(count_clicks) AS clicks,
        SUM(count_impressions) AS impressions,
        SUM(sum_spend) AS ad_spend,
        SUM(count_conversions_online) AS conv_online,
        SUM(count_conversions_offline_contribution_margin) AS conv_offline_cm,
        SUM(sum_conversion_value_offline_revenue) AS rev_offline,
        SUM(sum_conversion_value_offline_contribution_margin) AS cm1_offline,
        SUM(sum_conversion_value_calculated_revenue) AS rev_calc,
        SUM(sum_conversion_value_calculated_contribution_margin) AS cm1_calc,
        SUM(sum_attributed_value) AS attr_val,
        SUM(sum_attributed_value_completed) AS attr_completed,
        SUM(sum_coupon_and_wallet_credits) AS coupon_wallet,
        SUM(sum_conversion_value_offline_gross_bookings) AS offline_gb
    FROM `{project}.{dataset}.ads_campaign_stats`
    WHERE campaign_target_combined_entity_id = '{ce_id}'
        AND report_date BETWEEN '{start}' AND '{end}'
        AND ad_platform IN ('Google Ads', 'Microsoft Ads')
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )
    rows = run_bq_query(query)
    if not rows:
        return {}
    r = rows[0]
    clicks = float(r.get("clicks") or 0)
    impr = float(r.get("impressions") or 0)
    spend = float(r.get("ad_spend") or 0)
    conv_off = float(r.get("conv_offline_cm") or 0)
    conv_on = float(r.get("conv_online") or 0)
    rev_off = float(r.get("rev_offline") or 0)
    cm1_off = float(r.get("cm1_offline") or 0)
    rev_c = float(r.get("rev_calc") or 0)
    cm1_c = float(r.get("cm1_calc") or 0)
    attr_val = float(r.get("attr_val") or 0)
    attr_comp = float(r.get("attr_completed") or 0)
    cw = float(r.get("coupon_wallet") or 0)
    off_gb = float(r.get("offline_gb") or 0)

    # Resolve Sep 2025 boundary for ads_campaign_stats BEFORE adding PMax
    ads_rev = rev_off if rev_off > 0 else rev_c
    ads_cm1 = cm1_off if cm1_off > 0 else cm1_c
    ads_conv = conv_off if conv_off > 0 else conv_on

    # PMax: spend/clicks/conversions from asset-stats (valid via the dedicated asset
    # group / CID filter). VALUE (revenue + CM1) from fct_orders — asset-stats
    # sum_conversion_value is unreliable at CE grain (see _fetch_pmax_value).
    pmax_query = """
    SELECT
        SUM(count_clicks) AS clicks,
        SUM(count_impressions) AS impressions,
        SUM(sum_cost) AS spend,
        SUM(count_conversions) AS conversions
    FROM `{project}.{dataset}.google_ads_pmax_asset_stats`
    WHERE combined_entity_id = '{ce_id}'
        AND date BETWEEN '{start}' AND '{end}'
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )
    pmax_rows = run_bq_query(pmax_query) or []
    pmax_net_rev = 0.0
    if pmax_rows and pmax_rows[0].get("clicks"):
        p = pmax_rows[0]
        clicks += float(p.get("clicks") or 0)
        impr += float(p.get("impressions") or 0)
        spend += float(p.get("spend") or 0)
        ads_conv += float(p.get("conversions") or 0)
        # Only attribute PMax value when a dedicated asset group exists (= asset-stats
        # has rows), so spend and value stay consistent (both present or both absent).
        pv = _fetch_pmax_value(ce_id, start, end)
        ads_cm1 += pv["cm1"]
        pmax_net_rev = pv["revenue"]

    paid_rev = ads_rev + pmax_net_rev
    cm1 = ads_cm1
    mkt_cost = spend + cw
    conversions = ads_conv
    paid_cr = attr_comp / attr_val if attr_val else None

    return {
        "paid_rev": paid_rev,
        "paid_roi": cm1 / mkt_cost * 100 if mkt_cost else None,
        "rpc": paid_rev / clicks if clicks else None,
        "cpc": spend / clicks if clicks else None,
        "ad_spend": spend,
        "clicks": clicks,
        "ctr": clicks / impr * 100 if impr else None,
        "cvr": conversions / clicks * 100 if clicks else None,
        "cm1": cm1,
        "avg_cm1": cm1 / conversions if conversions else None,
        # ads-only TR: off_gb (gross bookings) is ads-only, so pair it with ads_rev
        # (not paid_rev, which now includes PMax) to keep numerator/denominator consistent.
        "paid_tr": ads_rev / (off_gb * paid_cr) * 100 if off_gb and paid_cr else None,
        "paid_cr": paid_cr * 100 if paid_cr else None,
    }


def fetch_paid_performance_3w(ce_id, l4w, p4w, ly):
    # type: (int, Tuple[date,date], Tuple[date,date], Tuple[date,date]) -> Dict[str, Dict]
    """Table 2 for all 3 windows."""
    return {
        "l4w": fetch_paid_performance(ce_id, l4w[0], l4w[1]),
        "p4w": fetch_paid_performance(ce_id, p4w[0], p4w[1]),
        "ly": fetch_paid_performance(ce_id, ly[0], ly[1]),
    }


def fetch_geo_coverage(ce_id, start, end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Geographic ad coverage from google_ads_ad_group_geo_stats. Replaces Q5/Q5b MCP.

    Returns top 15 countries by clicks with performance metrics.
    """
    query = """
    SELECT
        user_country_name AS country,
        SUM(count_clicks) AS clicks,
        SUM(count_impressions) AS impressions,
        SUM(sum_spend) AS spend,
        SUM(count_conversions_online) AS conversions,
        SUM(sum_conversion_value_offline_contribution_margin) AS cm1
    FROM `{project}.{dataset}.google_ads_ad_group_geo_stats`
    WHERE campaign_target_combined_entity_id = '{ce_id}'
        AND report_date BETWEEN '{start}' AND '{end}'
    GROUP BY 1
    ORDER BY clicks DESC
    LIMIT 15
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )
    rows = run_bq_query(query)
    if not rows:
        return []
    result = []
    for row in rows:
        cl = float(row.get("clicks") or 0)
        sp = float(row.get("spend") or 0)
        conv = float(row.get("conversions") or 0)
        result.append({
            "country": row.get("country"),
            "clicks": cl,
            "impressions": float(row.get("impressions") or 0),
            "spend": sp,
            "conversions": conv,
            "cm1": float(row.get("cm1") or 0),
            "cpc": sp / cl if cl else None,
            "cvr": conv / cl * 100 if cl else None,
        })
    return result


def fetch_geo_coverage_3w(ce_id, l4w, ly):
    # type: (int, Tuple[date,date], Tuple[date,date]) -> Dict[str, List]
    """Geo coverage for L4W and LY. Returns {l4w: [...], ly: [...]}."""
    return {
        "l4w": fetch_geo_coverage(ce_id, l4w[0], l4w[1]),
        "ly": fetch_geo_coverage(ce_id, ly[0], ly[1]),
    }


def fetch_budget_bidding(ce_id, start, end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Budget + bidding status. Replaces Q7 MCP.

    Joins campaign_stats (SIS, tROAS, bid strategy) with
    campaign_budget_stats (daily budget, utilization).
    """
    query = """
    SELECT
        g.campaign_name,
        g.campaign_id,
        ARRAY_AGG(g.current_campaign_target_roas ORDER BY g.report_date DESC LIMIT 1)[OFFSET(0)] AS troas_target,
        ARRAY_AGG(g.current_campaign_bidding_strategy ORDER BY g.report_date DESC LIMIT 1)[OFFSET(0)] AS bid_strategy,
        ARRAY_AGG(g.bidding_strategy_name ORDER BY g.report_date DESC LIMIT 1)[OFFSET(0)] AS bidding_strategy_name,
        ARRAY_AGG(b.daily_budget ORDER BY g.report_date DESC LIMIT 1)[OFFSET(0)] AS daily_budget,
        SUM(g.sum_spend) AS spend,
        SUM(CASE
            WHEN g.report_date > '2025-09-01'
                AND COALESCE(g.sum_conversion_value_offline_contribution_margin, 0) > 0
            THEN g.sum_conversion_value_offline_contribution_margin
            ELSE g.sum_conversion_value_calculated_contribution_margin
        END) AS cm1,
        SUM(CASE
            WHEN g.report_date > '2025-09-01'
                AND COALESCE(g.count_conversions_offline_contribution_margin, 0) > 0
            THEN g.count_conversions_offline_contribution_margin
            ELSE g.count_conversions_online
        END) AS conversions,
        SUM(g.count_clicks) AS clicks,
        SAFE_DIVIDE(SUM(g.count_impressions), SUM(g.count_eligible_searches)) AS sis,
        SAFE_DIVIDE(SUM(g.count_budget_lost_searches),
            NULLIF(SUM(g.count_eligible_searches), 0)) AS budget_lost_is,
        SAFE_DIVIDE(SUM(g.count_rank_lost_searches),
            NULLIF(SUM(g.count_eligible_searches), 0)) AS rank_lost_is
    FROM `{project}.{dataset}.google_ads_campaign_stats` g
    LEFT JOIN `{project}.{dataset}.google_ads_campaign_budget_stats` b
        USING (campaign_id, report_date)
    WHERE g.campaign_target_combined_entity_id = '{ce_id}'
        AND g.report_date BETWEEN '{start}' AND '{end}'
    GROUP BY 1, 2
    ORDER BY spend DESC
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )
    rows = run_bq_query(query)
    if not rows:
        return []
    result = []
    for row in rows:
        result.append({
            "campaign_name": row.get("campaign_name"),
            "campaign_id": row.get("campaign_id"),
            "troas_target": float(row.get("troas_target") or 0) if row.get("troas_target") else None,
            "bid_strategy": row.get("bid_strategy"),
            "bidding_strategy_name": row.get("bidding_strategy_name"),
            "campaign_type": "Individual" if not row.get("bidding_strategy_name") else "Portfolio",
            "daily_budget": float(row.get("daily_budget") or 0) if row.get("daily_budget") else None,
            "spend": float(row.get("spend") or 0),
            "cm1": float(row.get("cm1") or 0),
            "conversions": float(row.get("conversions") or 0),
            "clicks": float(row.get("clicks") or 0),
            "roi": float(row.get("cm1") or 0) / float(row.get("spend") or 0) * 100 if float(row.get("spend") or 0) else None,
            "cvr": float(row.get("conversions") or 0) / float(row.get("clicks") or 0) * 100 if float(row.get("clicks") or 0) else None,
            "sis": float(row.get("sis") or 0) * 100 if row.get("sis") else None,
            "budget_lost_is": float(row.get("budget_lost_is") or 0) * 100 if row.get("budget_lost_is") else None,
            "rank_lost_is": float(row.get("rank_lost_is") or 0) * 100 if row.get("rank_lost_is") else None,
        })
    return result


def fetch_landing_page_performance(ce_id, tw_start, tw_end, ly_start=None, ly_end=None):
    # type: (int, date, date, Optional[date], Optional[date]) -> Dict[str, Any]
    """Landing page performance from google_ads_campaign_page_stats.

    Filters to CE campaigns via campaign_id subquery from google_ads_campaign_stats
    (campaign_page_stats doesn't have CE ID populated).
    """
    def _fetch_lp_window(start, end):
        query = """
        WITH ce_campaigns AS (
            SELECT DISTINCT campaign_id
            FROM `{project}.{dataset}.google_ads_campaign_stats`
            WHERE campaign_target_combined_entity_id = '{ce_id}'
                AND report_date BETWEEN '{start}' AND '{end}'
        )
        SELECT
            lp.final_url,
            SUM(lp.count_impressions) AS impressions,
            SUM(lp.count_clicks) AS clicks,
            SUM(lp.sum_cost) AS spend
        FROM `{project}.{dataset}.google_ads_campaign_page_stats` lp
        INNER JOIN ce_campaigns c USING (campaign_id)
        WHERE lp.date BETWEEN '{start}' AND '{end}'
        GROUP BY 1
        HAVING SUM(lp.count_clicks) >= 100
        ORDER BY clicks DESC
        LIMIT 10
        """.format(
            project=PROJECT_ID, dataset=DATASET,
            ce_id=ce_id,
            start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
        )
        rows = run_bq_query(query) or []
        result = []
        for r in rows:
            cl = float(r.get("clicks") or 0)
            imp = float(r.get("impressions") or 0)
            sp_micros = float(r.get("spend") or 0)
            sp = sp_micros / 1_000_000
            result.append({
                "final_url": r.get("final_url"),
                "impressions": imp,
                "clicks": cl,
                "spend": sp,
                "ctr": (cl / imp * 100) if imp else None,
                "cpc": (sp / cl) if cl else None,
            })
        return result

    data = {"l4w": _fetch_lp_window(tw_start, tw_end)}
    if ly_start and ly_end:
        data["ly"] = _fetch_lp_window(ly_start, ly_end)
    return data


def fetch_lp_funnel(ce_id, tw_start, tw_end, ly_start=None, ly_end=None):
    # type: (int, date, date, Optional[date], Optional[date]) -> List[Dict[str, Any]]
    """Per-LP funnel from mixpanel_user_page_funnel_progression.

    Uses COUNT(DISTINCT user_id) to match Omni Page URL Analysis.
    Mixpanel collapses language variants (/it/, /de/) into the root URL.
    """
    ly_clause = ""
    if ly_start and ly_end:
        ly_clause = "OR event_date BETWEEN '{ly_s}' AND '{ly_e}'".format(
            ly_s=ly_start.strftime("%Y-%m-%d"), ly_e=ly_end.strftime("%Y-%m-%d"))

    query = """
    SELECT
      page_url,
      COUNT(DISTINCT CASE WHEN event_date BETWEEN '{tw_s}' AND '{tw_e}' THEN user_id END) AS l4w_users,
      SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN event_date BETWEEN '{tw_s}' AND '{tw_e}' AND has_order_completed THEN user_id END),
                  COUNT(DISTINCT CASE WHEN event_date BETWEEN '{tw_s}' AND '{tw_e}' THEN user_id END)) * 100 AS l4w_cvr,
      SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN event_date BETWEEN '{tw_s}' AND '{tw_e}' AND has_select_page_viewed THEN user_id END),
                  COUNT(DISTINCT CASE WHEN event_date BETWEEN '{tw_s}' AND '{tw_e}' THEN user_id END)) * 100 AS l4w_lp2s,
      SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN event_date BETWEEN '{tw_s}' AND '{tw_e}' AND has_checkout_started THEN user_id END),
                  COUNT(DISTINCT CASE WHEN event_date BETWEEN '{tw_s}' AND '{tw_e}' AND has_select_page_viewed THEN user_id END)) * 100 AS l4w_s2c,
      SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN event_date BETWEEN '{tw_s}' AND '{tw_e}' AND has_order_completed THEN user_id END),
                  COUNT(DISTINCT CASE WHEN event_date BETWEEN '{tw_s}' AND '{tw_e}' AND has_checkout_started THEN user_id END)) * 100 AS l4w_c2o,
      COUNT(DISTINCT CASE WHEN event_date BETWEEN '{ly_s}' AND '{ly_e}' THEN user_id END) AS ly_users,
      SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN event_date BETWEEN '{ly_s}' AND '{ly_e}' AND has_select_page_viewed THEN user_id END),
                  COUNT(DISTINCT CASE WHEN event_date BETWEEN '{ly_s}' AND '{ly_e}' THEN user_id END)) * 100 AS ly_lp2s,
      SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN event_date BETWEEN '{ly_s}' AND '{ly_e}' AND has_checkout_started THEN user_id END),
                  COUNT(DISTINCT CASE WHEN event_date BETWEEN '{ly_s}' AND '{ly_e}' AND has_select_page_viewed THEN user_id END)) * 100 AS ly_s2c,
      SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN event_date BETWEEN '{ly_s}' AND '{ly_e}' AND has_order_completed THEN user_id END),
                  COUNT(DISTINCT CASE WHEN event_date BETWEEN '{ly_s}' AND '{ly_e}' AND has_checkout_started THEN user_id END)) * 100 AS ly_c2o
    FROM `{project}.{dataset}.mixpanel_user_page_funnel_progression`
    WHERE combined_entity_id = '{ce_id}'
      AND (event_date BETWEEN '{tw_s}' AND '{tw_e}' {ly_clause})
    GROUP BY 1
    HAVING COUNT(DISTINCT CASE WHEN event_date BETWEEN '{tw_s}' AND '{tw_e}' THEN user_id END) >= 1
    ORDER BY l4w_users DESC
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
        tw_s=tw_start.strftime("%Y-%m-%d"), tw_e=tw_end.strftime("%Y-%m-%d"),
        ly_s=(ly_start or tw_start).strftime("%Y-%m-%d"),
        ly_e=(ly_end or tw_end).strftime("%Y-%m-%d"),
        ly_clause=ly_clause,
    )
    rows = run_bq_query(query) or []
    result = []
    for r in rows:
        result.append({
            "page_url": r.get("page_url"),
            "l4w_users": int(r.get("l4w_users") or 0),
            "l4w_cvr": float(r.get("l4w_cvr") or 0),
            "l4w_lp2s": float(r.get("l4w_lp2s") or 0),
            "l4w_s2c": float(r.get("l4w_s2c") or 0),
            "l4w_c2o": float(r.get("l4w_c2o") or 0),
            "ly_users": int(r.get("ly_users") or 0),
            "ly_lp2s": float(r.get("ly_lp2s") or 0),
            "ly_s2c": float(r.get("ly_s2c") or 0),
            "ly_c2o": float(r.get("ly_c2o") or 0),
        })
    return result


def fetch_keyword_impression_share(ce_id, tw_start, tw_end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Keyword-level impression share from google_ads_keyword_device_stats.

    Aggregates across devices. Returns top keywords by clicks.
    """
    query = """
    SELECT
        keyword,
        keyword_match_type AS match_type,
        SUM(count_impressions) AS impressions,
        SUM(count_clicks) AS clicks,
        SUM(sum_spend) AS spend,
        SUM(count_conversions) AS conversions,
        SUM(sum_conversion_value) AS conversion_value,
        SAFE_DIVIDE(SUM(count_impressions), SUM(count_eligible_searches)) AS sis,
        SUM(count_eligible_searches) AS eligible_searches
    FROM `{project}.{dataset}.google_ads_keyword_device_stats`
    WHERE STARTS_WITH(campaign_combined_entity_id, '{ce_id}')
        AND date BETWEEN '{start}' AND '{end}'
        AND is_negative = FALSE
    GROUP BY 1, 2
    ORDER BY clicks DESC
    LIMIT 50
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id,
        start=tw_start.strftime("%Y-%m-%d"), end=tw_end.strftime("%Y-%m-%d"),
    )
    rows = run_bq_query(query) or []
    result = []
    for r in rows:
        cl = float(r.get("clicks") or 0)
        imp = float(r.get("impressions") or 0)
        sp = float(r.get("spend") or 0)
        conv = float(r.get("conversions") or 0)
        result.append({
            "keyword": r.get("keyword"),
            "match_type": r.get("match_type"),
            "impressions": imp,
            "clicks": cl,
            "spend": sp,
            "conversions": conv,
            "conversion_value": float(r.get("conversion_value") or 0),
            "sis": float(r.get("sis") or 0) * 100 if r.get("sis") else None,
            "eligible_searches": float(r.get("eligible_searches") or 0),
            "cpc": (sp / cl) if cl else None,
            "cvr": (conv / cl * 100) if cl else None,
            "ctr": (cl / imp * 100) if imp else None,
        })
    return result


def fetch_campaign_targeting(ce_id):
    # type: (int,) -> List[Dict[str, Any]]
    """Campaign targeting config from stg_google_ads_new__campaigns.

    Returns active campaigns with geo × language targeting parsed from campaign names.
    """
    query = """
    SELECT
        campaign_name,
        campaign_city,
        campaign_language,
        campaign_targeting_location,
        campaign_budget_latest AS daily_budget,
        bidding_strategy_latest AS bidding_strategy,
        bid_strategy_name_latest AS bidding_strategy_name,
        target_roas_latest AS target_roas,
        campaign_status_latest AS status,
        advertising_channel_type AS channel_type
    FROM `{project}.analytics_staging.stg_google_ads_new__campaigns`
    WHERE campaign_combined_entity_id = '{ce_id}'
        AND campaign_status_latest = 'ENABLED'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY date DESC) = 1
    ORDER BY campaign_name
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id,
    )
    rows = run_bq_query(query) or []
    result = []
    for r in rows:
        result.append({
            "campaign_name": r.get("campaign_name"),
            "city": r.get("campaign_city"),
            "language": r.get("campaign_language"),
            "targeting_location": r.get("campaign_targeting_location"),
            "daily_budget": float(r.get("daily_budget") or 0) if r.get("daily_budget") else None,
            "bidding_strategy": r.get("bidding_strategy"),
            "bidding_strategy_name": r.get("bidding_strategy_name"),
            "target_roas": float(r.get("target_roas") or 0) if r.get("target_roas") else None,
            "channel_type": r.get("channel_type"),
        })
    return result


def fetch_ad_group_performance(ce_id, tw_start, tw_end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Ad group performance from google_ads_ad_group_stats.

    Aggregated ad group metrics for coverage analysis.
    """
    query = """
    SELECT
        ad_group_name,
        ad_group_id,
        SUM(count_impressions) AS impressions,
        SUM(count_clicks) AS clicks,
        SUM(sum_spend) AS spend,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(count_conversions_offline_contribution_margin, 0) > 0
            THEN count_conversions_offline_contribution_margin
            ELSE count_conversions_online
        END) AS conversions,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(sum_conversion_value_offline_contribution_margin, 0) > 0
            THEN sum_conversion_value_offline_contribution_margin
            ELSE sum_conversions_value
        END) AS cm1
    FROM `{project}.{dataset}.google_ads_ad_group_stats`
    WHERE campaign_target_combined_entity_id = '{ce_id}'
        AND report_date BETWEEN '{start}' AND '{end}'
    GROUP BY 1, 2
    ORDER BY clicks DESC
    """.format(
        project=PROJECT_ID, dataset=DATASET,
        ce_id=ce_id,
        start=tw_start.strftime("%Y-%m-%d"), end=tw_end.strftime("%Y-%m-%d"),
    )
    rows = run_bq_query(query) or []
    result = []
    for r in rows:
        cl = float(r.get("clicks") or 0)
        sp = float(r.get("spend") or 0)
        conv = float(r.get("conversions") or 0)
        imp = float(r.get("impressions") or 0)
        cm1 = float(r.get("cm1") or 0)
        result.append({
            "ad_group_name": r.get("ad_group_name"),
            "ad_group_id": r.get("ad_group_id"),
            "impressions": imp,
            "clicks": cl,
            "spend": sp,
            "conversions": conv,
            "cm1": cm1,
            "cpc": (sp / cl) if cl else None,
            "cvr": (conv / cl * 100) if cl else None,
            "ctr": (cl / imp * 100) if imp else None,
            "roi": (cm1 / sp * 100) if sp else None,
        })
    return result


def fetch_ad_group_by_type(ce_id, tw_start, tw_end):
    # type: (int, date, date) -> Dict[str, Dict[str, Any]]
    """Ad group performance aggregated by type (parsed from name).

    Ad group names follow: {Type} - {Match} - {Language} - {Location}
    Returns dict keyed by type (Tickets, Generic, Tour, DSA, etc.) with
    aggregated metrics + list of languages covered.
    """
    raw = fetch_ad_group_performance(ce_id, tw_start, tw_end)
    if not raw:
        return {}

    types = {}  # type: Dict[str, Dict[str, Any]]
    for ag in raw:
        name = ag.get("ad_group_name") or ""
        parts = name.split(" - ")
        ag_type = parts[0].strip() if parts else "Unknown"
        lang = parts[2].strip() if len(parts) > 2 else "Unknown"

        if ag_type not in types:
            types[ag_type] = {
                "clicks": 0, "spend": 0, "conversions": 0, "cm1": 0,
                "impressions": 0, "ag_count": 0, "languages": set(),
            }
        t = types[ag_type]
        t["clicks"] += ag.get("clicks", 0)
        t["spend"] += ag.get("spend", 0)
        t["conversions"] += ag.get("conversions", 0)
        t["cm1"] += ag.get("cm1", 0)
        t["impressions"] += ag.get("impressions", 0)
        t["ag_count"] += 1
        if ag.get("clicks", 0) > 0:
            t["languages"].add(lang)

    result = {}
    for ag_type, t in types.items():
        cl = t["clicks"]
        sp = t["spend"]
        conv = t["conversions"]
        cm1 = t["cm1"]
        imp = t["impressions"]
        result[ag_type] = {
            "clicks": cl,
            "spend": sp,
            "conversions": conv,
            "cm1": cm1,
            "impressions": imp,
            "ag_count": t["ag_count"],
            "languages": sorted(t["languages"]),
            "cpc": (sp / cl) if cl else None,
            "cvr": (conv / cl * 100) if cl else None,
            "ctr": (cl / imp * 100) if imp else None,
            "roi": (cm1 / sp * 100) if sp else None,
        }
    return result


def fetch_ad_group_audit(ce_id, start, end, p4w_start=None, p4w_end=None,
                         top_n=15, material_spend=500.0):
    # type: (int, date, date, Optional[date], Optional[date], int, float) -> Dict[str, Any]
    """Per-ad-group performance + bid-headroom opportunity for the ad-group audit.

    google_ads_ad_group_stats has NO impression-share / rank-lost at ad-group grain
    (those are campaign-level), so opportunity is framed as **bid headroom vs the
    ad group's tROAS target**, not SIS gap:
      - Scale candidate: actual ROI ≥ target × 1.15 AND material spend — the
        algorithm is under-bidding a profitable ad group (volume left on the table).
      - Efficiency leak: actual ROI < 130% (breakeven risk) AND material spend —
        spend at risk; fix LP/quality/match or trim.
      - On-target / Long-tail otherwise.

    Note: ad group × product (experience_id) is NOT available — fct_orders carries
    no ad_group_id. The ad-group *type* (parsed from the name) is the product-intent
    proxy.

    Returns {rows (top_n by spend), all, scale_spend, leak_spend, scale_count,
             leak_count, n_total}.
    """
    query = """
    SELECT
        ad_group_name,
        ANY_VALUE(ad_group_status) AS status,
        ANY_VALUE(ad_group_target_roas) AS target_roas,
        SUM(count_impressions) AS impressions,
        SUM(count_clicks) AS clicks,
        SUM(sum_spend) AS spend,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(count_conversions_offline_contribution_margin, 0) > 0
            THEN count_conversions_offline_contribution_margin
            ELSE count_conversions_online
        END) AS conversions,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(sum_conversion_value_offline_contribution_margin, 0) > 0
            THEN sum_conversion_value_offline_contribution_margin
            ELSE sum_conversions_value
        END) AS cm1
    FROM `{project}.{dataset}.google_ads_ad_group_stats`
    WHERE campaign_target_combined_entity_id = '{ce_id}'
        AND report_date BETWEEN '{start}' AND '{end}'
    GROUP BY ad_group_name
    HAVING spend > 0
    ORDER BY spend DESC
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )
    rows = run_bq_query(query) or []

    # MoM: prior-4-week spend + ROI per ad group (join by name — stable within the
    # same consolidation era; YoY is NOT done — ad-group names churn across the year).
    mom_map = {}  # type: Dict[str, Dict[str, Any]]
    if p4w_start and p4w_end:
        p4w_query = """
        SELECT
            ad_group_name,
            SUM(sum_spend) AS spend,
            SUM(CASE
                WHEN report_date > '2025-09-01'
                    AND COALESCE(sum_conversion_value_offline_contribution_margin, 0) > 0
                THEN sum_conversion_value_offline_contribution_margin
                ELSE sum_conversions_value
            END) AS cm1
        FROM `{project}.{dataset}.google_ads_ad_group_stats`
        WHERE campaign_target_combined_entity_id = '{ce_id}'
            AND report_date BETWEEN '{start}' AND '{end}'
        GROUP BY 1
        HAVING spend > 0
        """.format(
            project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
            start=p4w_start.strftime("%Y-%m-%d"), end=p4w_end.strftime("%Y-%m-%d"),
        )
        for r in run_bq_query(p4w_query) or []:
            sp = float(r.get("spend") or 0)
            cm1 = float(r.get("cm1") or 0)
            mom_map[r.get("ad_group_name")] = {"spend": sp, "roi": (cm1 / sp * 100) if sp else None}

    out = []
    scale_spend = leak_spend = 0.0
    scale_count = leak_count = 0
    for r in rows:
        name = r.get("ad_group_name") or ""
        parts = name.split(" - ")
        cl = float(r.get("clicks") or 0)
        sp = float(r.get("spend") or 0)
        conv = float(r.get("conversions") or 0)
        imp = float(r.get("impressions") or 0)
        cm1 = float(r.get("cm1") or 0)
        roi = (cm1 / sp * 100) if sp else None
        tr = r.get("target_roas")
        target_pct = float(tr) * 100 if tr else None     # stored as ratio (1.65 → 165%)
        eff_target = target_pct or 145.0                  # Pro+ standard when unset
        if sp >= material_spend and roi is not None and roi >= eff_target * 1.15:
            flag = "Scale"
            scale_spend += sp
            scale_count += 1
        elif sp >= material_spend and roi is not None and roi < 130:
            flag = "Leak"
            leak_spend += sp
            leak_count += 1
        elif sp < material_spend:
            flag = "Long-tail"
        else:
            flag = "On-target"
        out.append({
            "ad_group_name": name,
            "ag_type": parts[0].strip() if parts else "Unknown",
            "language": parts[2].strip() if len(parts) > 2 else "Unknown",
            "status": r.get("status"),
            "impressions": imp,
            "clicks": cl,
            "spend": sp,
            "conversions": conv,
            "cm1": cm1,
            "cpc": (sp / cl) if cl else None,
            "cvr": (conv / cl * 100) if cl else None,
            "ctr": (cl / imp * 100) if imp else None,
            "roi": roi,
            "target_pct": target_pct,
            "vs_target": (roi - eff_target) if roi is not None else None,
            "flag": flag,
            "spend_mom_pct": (
                (sp - mom_map[name]["spend"]) / mom_map[name]["spend"] * 100
                if (name in mom_map and mom_map[name]["spend"]) else None),
            "roi_mom_pp": (
                roi - mom_map[name]["roi"]
                if (name in mom_map and mom_map[name].get("roi") is not None and roi is not None)
                else None),
        })
    return {
        "rows": out[:top_n],
        "all": out,
        "scale_spend": scale_spend,
        "leak_spend": leak_spend,
        "scale_count": scale_count,
        "leak_count": leak_count,
        "n_total": len(out),
    }


# ============================================================================
# V6.1: PRODUCT MIX — TGID / EXPERIENCE REVENUE (assortment shift detection)
# ============================================================================

def _fetch_tgid_window(ce_id, start, end):
    # type: (int, date, date) -> List[Dict[str, Any]]
    """Net-revenue + order economics per experience (TGID) for one window.

    Grain: `fct_orders.experience_id` (= Tour Group ID). Each order carries a
    primary `experience_id` / `experience_name`, so this is order-grain — no
    join to dim_experiences needed (the name is on the order).

    Per-TGID economics mirror the channel/cohort tables:
        AOV     = order_value_usd / orders
        TR              = revenue / order_value_completed_usd
        CR              = order_value_completed_usd / order_value_usd
        net_rev_per_order = net revenue / orders  (== AOV x TR x CR — Headout's take
                          per order; NOT contribution margin, no cost subtracted)
        cm1_per_order   = (net revenue − direct costs) / orders — true per-order
                          contribution margin (computed in fetch_tgid_revenue)

    Net revenue uses `amount_revenue_usd` (NOT GMV `order_value_completed_usd`).
    """
    query = """
    SELECT
        experience_id AS tgid,
        ANY_VALUE(experience_name) AS experience_name,
        ROUND(SUM(amount_revenue_usd), 2) AS revenue,
        ROUND(SUM(amount_direct_costs_usd), 2) AS direct_costs,
        COUNT(*) AS orders,
        ROUND(SAFE_DIVIDE(SUM(order_value_usd), COUNT(*)), 2) AS aov,
        ROUND(SAFE_DIVIDE(SUM(amount_revenue_usd), NULLIF(SUM(order_value_completed_usd), 0)) * 100, 2) AS tr,
        ROUND(SAFE_DIVIDE(SUM(order_value_completed_usd), NULLIF(SUM(order_value_usd), 0)) * 100, 2) AS cr,
        ROUND(SAFE_DIVIDE(SUM(amount_revenue_usd), COUNT(*)), 2) AS net_rev_per_order
    FROM `{project}.{dataset}.fct_orders`
    WHERE combined_entity_id = '{ce_id}'
        AND DATE(created_at) BETWEEN '{start}' AND '{end}'
        AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
        AND user_type = 'Customer'
    GROUP BY experience_id
    HAVING orders > 0
    ORDER BY revenue DESC
    """.format(
        project=PROJECT_ID,
        dataset=DATASET,
        ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
    )
    return run_bq_query(query) or []


def fetch_tgid_revenue(ce_id, l4w, ly, top_n=10):
    # type: (int, Tuple[date, date], Tuple[date, date], int) -> Dict[str, Any]
    """Top experiences (TGIDs) by L4W net revenue with LY assortment-shift deltas.

    Surfaces *what products paid traffic purchased* and how the product mix shifted
    YoY — the missing layer that let prior audits miss assortment-driven CVR/RPC
    moves. The load-bearing column is Δ Share (L4W revenue share − LY revenue share):
    a TGID going 0%->15% (new hero) or 20%->5% (decayed) is the assortment change.

    Returns:
        {
          "l4w_total": float, "ly_total": float,
          "rows": [ {tgid, experience_name, l4w_rev, l4w_share, ly_rev, ly_share,
                     delta_share, orders, aov, tr, cr, net_rev_per_order,
                     cm1_per_order, is_new, is_dropped}, ... ],
          "n_l4w": int, "n_ly": int,   # distinct TGID counts (catalogue breadth)
        }
        Rows are the union of the top_n L4W TGIDs and any LY TGID that was >5% of LY
        revenue but fell out of the L4W top_n (so decayed heroes still surface).
    """
    l4w_rows = _fetch_tgid_window(ce_id, l4w[0], l4w[1])
    ly_rows = _fetch_tgid_window(ce_id, ly[0], ly[1])

    l4w_total = sum(float(r.get("revenue") or 0) for r in l4w_rows)
    ly_total = sum(float(r.get("revenue") or 0) for r in ly_rows)
    ly_by_tgid = {r["tgid"]: r for r in ly_rows}
    l4w_by_tgid = {r["tgid"]: r for r in l4w_rows}

    # Selection: top_n by L4W revenue, plus any LY TGID >5% share now outside top_n.
    keep = [r["tgid"] for r in l4w_rows[:top_n]]
    keep_set = set(keep)
    for r in ly_rows:
        ly_share = (float(r.get("revenue") or 0) / ly_total * 100) if ly_total else 0
        if ly_share >= 5.0 and r["tgid"] not in keep_set:
            keep.append(r["tgid"])
            keep_set.add(r["tgid"])

    rows = []
    for tgid in keep:
        cur = l4w_by_tgid.get(tgid)
        prev = ly_by_tgid.get(tgid)
        l4w_rev = float(cur.get("revenue") or 0) if cur else 0.0
        ly_rev = float(prev.get("revenue") or 0) if prev else 0.0
        l4w_share = (l4w_rev / l4w_total * 100) if l4w_total else 0.0
        ly_share = (ly_rev / ly_total * 100) if ly_total else 0.0
        name = (cur or prev or {}).get("experience_name") or "(unknown)"
        cur_orders = int(cur.get("orders") or 0) if cur else 0
        cur_dc = float(cur.get("direct_costs") or 0) if cur else 0.0
        cm1_per_order = ((l4w_rev - cur_dc) / cur_orders) if cur_orders else None
        rows.append({
            "tgid": tgid,
            "experience_name": name,
            "l4w_rev": l4w_rev,
            "l4w_share": l4w_share,
            "ly_rev": ly_rev,
            "ly_share": ly_share,
            "delta_share": l4w_share - ly_share,
            "orders": cur_orders,
            "aov": float(cur["aov"]) if cur and cur.get("aov") is not None else None,
            "tr": float(cur["tr"]) if cur and cur.get("tr") is not None else None,
            "cr": float(cur["cr"]) if cur and cur.get("cr") is not None else None,
            "net_rev_per_order": float(cur["net_rev_per_order"]) if cur and cur.get("net_rev_per_order") is not None else None,
            "cm1_per_order": round(cm1_per_order, 2) if cm1_per_order is not None else None,
            "is_new": cur is not None and prev is None,
            "is_dropped": cur is None and prev is not None,
        })

    # Sort by current share desc, but push fully-dropped TGIDs (no L4W rev) to the end.
    rows.sort(key=lambda r: (r["l4w_rev"] > 0, r["l4w_share"]), reverse=True)

    monthly = _fetch_tgid_monthly(ce_id, [r["tgid"] for r in rows]) if rows else {}

    return {
        "l4w_total": l4w_total,
        "ly_total": ly_total,
        "rows": rows,
        "n_l4w": len(l4w_rows),
        "n_ly": len(ly_rows),
        "monthly": monthly,  # {tgid: [net_rev chronological]} — L12M, kept TGIDs only
    }


def _fetch_tgid_monthly(ce_id, tgids, months=13):
    # type: (int, List[str], int) -> Dict[str, List[float]]
    """L12M monthly net revenue for the given experience_ids (kept/enumerated TGIDs).

    One query bounded to the kept TGIDs (≤ ~12) so cost stays small. Returns
    {tgid: [revenue per month, chronological]} for trajectory tagging.
    """
    if not tgids:
        return {}
    id_list = ", ".join("'%s'" % str(t) for t in tgids if t is not None)
    if not id_list:
        return {}
    query = """
    SELECT
        experience_id AS tgid,
        SUBSTR(CAST(DATE(created_at) AS STRING), 1, 7) AS month,
        ROUND(SUM(amount_revenue_usd), 2) AS revenue
    FROM `{project}.{dataset}.fct_orders`
    WHERE combined_entity_id = '{ce_id}'
        AND experience_id IN ({ids})
        AND DATE(created_at) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL {months} MONTH)
            AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
        AND user_type = 'Customer'
    GROUP BY 1, 2
    ORDER BY 2
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id, ids=id_list, months=months,
    )
    rows = run_bq_query(query) or []
    out = {}  # type: Dict[str, List[float]]
    for r in rows:
        out.setdefault(str(r["tgid"]), []).append(float(r.get("revenue") or 0.0))
    return out


def fetch_channel_monthly(ce_id, months=13):
    # type: (int, int) -> Dict[str, List[float]]
    """L12M monthly net revenue per channel (taxonomy mirrors _fetch_channel_window_v2).

    Returns {channel: [net_rev per month, chronological]} for trajectory tagging of
    channel signals. The CASE is duplicated from _fetch_channel_window_v2 to keep
    that hot path untouched.
    """
    query = """
    WITH classified AS (
        SELECT
            CASE
                WHEN channel_name = 'Google Ads'
                    AND REGEXP_CONTAINS(campaign_name, CONCAT('cid', CAST(combined_entity_id AS STRING)))
                    THEN 'Google Search'
                WHEN channel_name = 'Google Ads'
                    AND campaign_name LIKE '1 - %'
                    THEN 'Bing'
                WHEN channel_name = 'Bing Ads'
                    AND REGEXP_CONTAINS(campaign_name, CONCAT('cid', CAST(combined_entity_id AS STRING)))
                    THEN 'Bing'
                WHEN channel_name = 'Google Ads'
                    AND REGEXP_CONTAINS(LOWER(COALESCE(campaign_name, '')), r'pmax|performance.max')
                    THEN 'Google PMax'
                WHEN channel_name = 'Google Ads' THEN 'Google Cross-sell'
                WHEN channel_name = 'Bing Ads' THEN 'Bing Cross-sell'
                WHEN channel_name = 'Things to Do (Ads)' THEN 'TTD (Paid)'
                WHEN channel_name = 'Things to Do (Organic)' THEN 'TTD (Organic)'
                WHEN channel_name = 'Confirmation Page Recommendations' THEN 'CPR'
                WHEN channel_name = 'Organic Search' THEN 'Organic'
                WHEN channel_grouping = 'Direct (App)' THEN 'Direct (App)'
                WHEN channel_grouping = 'Direct' THEN 'Direct'
                WHEN channel_grouping = 'Affiliates' THEN 'Affiliates'
                WHEN channel_grouping = 'Email' THEN 'Email'
                WHEN channel_grouping = 'Referral' THEN 'Referral'
                ELSE 'Other'
            END AS channel,
            SUBSTR(CAST(DATE(created_at) AS STRING), 1, 7) AS month,
            amount_revenue_usd AS revenue
        FROM `{project}.{dataset}.fct_orders`
        WHERE combined_entity_id = '{ce_id}'
            AND DATE(created_at) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL {months} MONTH)
                AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
            AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
            AND user_type = 'Customer'
    )
    SELECT channel, month, ROUND(SUM(revenue), 2) AS revenue
    FROM classified
    GROUP BY 1, 2
    ORDER BY 2
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id, months=months,
    )
    rows = run_bq_query(query) or []
    out = {}  # type: Dict[str, List[float]]
    for r in rows:
        out.setdefault(r["channel"], []).append(float(r.get("revenue") or 0.0))
    return out


def fetch_campaign_product_mix(ce_id, start, end, top_n=15):
    # type: (int, date, date, int) -> Dict[str, Any]
    """Paid campaign x product (TGID) revenue + margin for one window.

    Answers "which campaign sells which product at what margin" — the join that
    crosses the campaign backbone (Section 5) with the product mix (Section 4
    TGID table). Grain: (campaign_name, experience_id). Paid scope only
    (campaign-attributed Google/Bing orders, classified with the same channel
    CASE as `fetch_channel_monthly`).

    Margin comes straight from fct_orders (amount_revenue_usd −
    amount_direct_costs_usd): spend lives only at campaign level, so ROI can't be
    split by product, but TR and CM1/order can. Net revenue uses
    `amount_revenue_usd` (NOT GMV).

    Returns:
        {
          "rows": [...top_n pairs by net revenue — the report mini-table...],
          "all":  [...every pair, net-rev desc — the Google Sheet tab...],
          "total_rev": float,   # paid net rev across all pairs (share denominator)
        }
        Each row: {campaign_name, channel, tgid, experience_name, orders,
                   net_rev, share, aov, tr, cm1, cm1_per_order}.
    """
    query = """
    WITH classified AS (
        SELECT
            campaign_name,
            CASE
                WHEN channel_name = 'Google Ads'
                    AND REGEXP_CONTAINS(campaign_name, CONCAT('cid', CAST(combined_entity_id AS STRING)))
                    THEN 'Google Search'
                WHEN channel_name = 'Google Ads'
                    AND campaign_name LIKE '1 - %'
                    THEN 'Bing'
                WHEN channel_name = 'Bing Ads'
                    AND REGEXP_CONTAINS(campaign_name, CONCAT('cid', CAST(combined_entity_id AS STRING)))
                    THEN 'Bing'
                WHEN channel_name = 'Google Ads'
                    AND REGEXP_CONTAINS(LOWER(COALESCE(campaign_name, '')), r'pmax|performance.max')
                    THEN 'Google PMax'
                WHEN channel_name = 'Google Ads' THEN 'Google Cross-sell'
                WHEN channel_name = 'Bing Ads' THEN 'Bing Cross-sell'
                ELSE 'Other'
            END AS channel,
            experience_id AS tgid,
            experience_name,
            amount_revenue_usd AS revenue,
            amount_direct_costs_usd AS direct_costs,
            order_value_usd,
            order_value_completed_usd
        FROM `{project}.{dataset}.fct_orders`
        WHERE combined_entity_id = '{ce_id}'
            AND DATE(created_at) BETWEEN '{start}' AND '{end}'
            AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
            AND user_type = 'Customer'
            AND campaign_name IS NOT NULL
            AND experience_id IS NOT NULL
    )
    SELECT
        campaign_name,
        channel,
        tgid,
        ANY_VALUE(experience_name) AS experience_name,
        COUNT(*) AS orders,
        ROUND(SUM(revenue), 2) AS net_rev,
        ROUND(SAFE_DIVIDE(SUM(order_value_usd), COUNT(*)), 2) AS aov,
        ROUND(SAFE_DIVIDE(SUM(revenue), NULLIF(SUM(order_value_completed_usd), 0)) * 100, 2) AS tr,
        ROUND(SUM(revenue - direct_costs), 2) AS cm1,
        ROUND(SAFE_DIVIDE(SUM(revenue - direct_costs), COUNT(*)), 2) AS cm1_per_order
    FROM classified
    WHERE channel IN ('Google Search', 'Bing', 'Google PMax', 'Google Cross-sell', 'Bing Cross-sell')
    GROUP BY campaign_name, channel, tgid
    HAVING net_rev > 0
    ORDER BY net_rev DESC
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )
    rows = run_bq_query(query) or []
    total_rev = sum(float(r.get("net_rev") or 0.0) for r in rows)
    for r in rows:
        r["share"] = (float(r.get("net_rev") or 0.0) / total_rev * 100) if total_rev else 0.0
    return {
        "rows": rows[:top_n],
        "all": rows,
        "total_rev": total_rev,
    }


# ============================================================================
# V6.1: PAID VALUE SHAPLEY (Clicks x CVR x Avg CM1 -> paid CM1 change)
# ============================================================================

def _fetch_paid_value_window(ce_id, start, end):
    # type: (int, date, date) -> Dict[str, float]
    """Total paid clicks / conversions / CM1 for one window (Google + Bing + PMax).

    Same paid universe and offline-boundary logic as `_fetch_channel_window_v2`,
    aggregated to a single paid total so the Shapley factors tie to the paid
    figures shown in the Channel and Paid Deep Dive tables.
    """
    ads_query = """
    SELECT
        SUM(count_clicks) AS clicks,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(count_conversions_offline_contribution_margin, 0) > 0
            THEN count_conversions_offline_contribution_margin
            ELSE count_conversions_online
        END) AS conversions,
        SUM(CASE
            WHEN report_date > '2025-09-01'
                AND COALESCE(sum_conversion_value_offline_contribution_margin, 0) > 0
            THEN sum_conversion_value_offline_contribution_margin
            ELSE sum_conversion_value_calculated_contribution_margin
        END) AS cm1
    FROM `{project}.{dataset}.ads_campaign_stats`
    WHERE campaign_target_combined_entity_id = '{ce_id}'
        AND report_date BETWEEN '{start}' AND '{end}'
        AND ad_platform IN ('Google Ads', 'Microsoft Ads')
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )

    # PMax: clicks/conversions from asset-stats; CM1 from fct_orders (CE-attributed
    # ground truth — asset-stats sum_conversion_value is unreliable at CE grain).
    pmax_query = """
    SELECT
        SUM(count_clicks) AS clicks,
        SUM(count_conversions) AS conversions
    FROM `{project}.{dataset}.google_ads_pmax_asset_stats`
    WHERE combined_entity_id = '{ce_id}'
        AND date BETWEEN '{start}' AND '{end}'
    """.format(
        project=PROJECT_ID, dataset=DATASET, ce_id=ce_id,
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
    )

    ads = (run_bq_query(ads_query) or [{}])[0]
    pmax = (run_bq_query(pmax_query) or [{}])[0]
    # PMax value only when a dedicated asset group exists (asset-stats has clicks)
    pmax_cm1 = _fetch_pmax_value(ce_id, start, end)["cm1"] if (pmax.get("clicks") or 0) else 0.0

    clicks = float(ads.get("clicks") or 0) + float(pmax.get("clicks") or 0)
    conversions = float(ads.get("conversions") or 0) + float(pmax.get("conversions") or 0)
    cm1 = float(ads.get("cm1") or 0) + pmax_cm1

    return {
        "clicks": clicks,
        "conversions": conversions,
        "cm1": cm1,
        "cvr": (conversions / clicks) if clicks else 0.0,        # fraction (conv/click)
        "avg_cm1": (cm1 / conversions) if conversions else 0.0,  # CM1 per conversion
    }


def fetch_paid_value_shapley(ce_id, l4w, p4w, ly):
    # type: (int, Tuple[date, date], Tuple[date, date], Tuple[date, date]) -> Dict[str, Any]
    """Shapley decomposition of paid CM1 change into Clicks x CVR x Avg CM1.

    Paid CM1 = Clicks x (conv/clicks) x (CM1/conv). Decomposing into these three
    factors tells the analyst which driver moved the paid value — clicks (volume),
    CVR (conversion efficiency), or avg CM1 (value per conversion = AOV x TR x CR).
    This forces the driver-ordering verdict from computed attribution rather than
    letting the narrative pick the story from raw tables.

    Computes the decomposition for two comparisons:
        - mom: L4W vs P4W
        - yoy: L4W vs LY

    Returns:
        {
          "windows": {"l4w": {...}, "p4w": {...}, "ly": {...}},   # raw factor values
          "mom": { "total_delta": float, "clicks": {...}, "cvr": {...}, "avg_cm1": {...} },
          "yoy": { ... same shape ... },
        }
      Each driver dict: {"contribution": $, "share_pct": % of |total_delta|, "direction": "up"|"down"}.
    """
    from engine.metrics import shapley_multiplicative

    factors = ["clicks", "cvr", "avg_cm1"]
    cur = _fetch_paid_value_window(ce_id, l4w[0], l4w[1])
    pri = _fetch_paid_value_window(ce_id, p4w[0], p4w[1])
    lyw = _fetch_paid_value_window(ce_id, ly[0], ly[1])

    def decompose(prior, current):
        contrib = shapley_multiplicative(prior, current, factors)
        total = current["cm1"] - prior["cm1"]
        denom = abs(total) if total else 1.0
        out = {"total_delta": total}
        for nm in factors:
            c = contrib[nm]
            out[nm] = {
                "contribution": c,
                "share_pct": (c / denom * 100) if total else None,
                "direction": "up" if c >= 0 else "down",
            }
        return out

    return {
        "windows": {"l4w": cur, "p4w": pri, "ly": lyw},
        "mom": decompose(pri, cur),
        "yoy": decompose(lyw, cur),
    }
