"""
Metric definitions — single source of truth for perf audit v6.1.

Every derived metric is defined here as a function. bq.py imports these
instead of computing inline. If a formula needs to change, change it here
once — every table updates.

Validated against Omni dashboard (May 18, 2026).
All percentage metrics return as percentages (148.5 = 148.5%), not ratios.
"""

from __future__ import annotations


# ============================================================================
# CORE METRICS
# ============================================================================

def aov(order_value, orders):
    """Average Order Value = gross ticket value / orders.
    Source: Omni `sum_order_value / count_orders`.
    NOT revenue/orders (that would be revenue per order, ~27% of AOV).
    """
    if not orders:
        return None
    return order_value / orders


def tr(revenue, order_value_completed):
    """Take Rate = revenue / completed gross bookings.
    Source: Omni `sum_revenue / sum_order_value_completed`.
    """
    if not order_value_completed:
        return None
    return revenue / order_value_completed * 100


def cr(order_value_completed, order_value):
    """Completion Rate = completed gross bookings / total gross bookings.
    Source: Omni `sum_order_value_completed / sum_order_value`.
    """
    if not order_value:
        return None
    return order_value_completed / order_value * 100


# ============================================================================
# PAID METRICS
# ============================================================================

def cpc(spend, clicks):
    """Cost Per Click = spend / clicks."""
    if not clicks:
        return None
    return spend / clicks


def ctr(clicks, impressions):
    """Click-Through Rate = clicks / impressions."""
    if not impressions:
        return None
    return clicks / impressions * 100


def cvr(conversions, clicks):
    """Conversion Rate = conversions / clicks.
    Source: Omni `count_conversions_offline_contribution_margin / count_clicks`.
    Post-Sep 2025 uses offline. Pre-Sep uses online. Boundary handled in bq.py queries.
    """
    if not clicks:
        return None
    return conversions / clicks * 100


def rpc(revenue, clicks):
    """Revenue Per Click = revenue / clicks.
    Revenue source depends on context: fct_orders for channel/cohort,
    ads_campaign_stats offline/calculated for Table 2.
    """
    if not clicks:
        return None
    return revenue / clicks


def roi(cm1, spend, coupon_wallet=0):
    """Paid ROI = CM1 / marketing cost.
    Source: Omni `contribution_margin_one / marketing_cost`.
    marketing_cost = spend + coupon_wallet.
    CM1 = offline CM1 post-Sep 2025, calculated CM1 pre-Sep.
    """
    mkt = spend + (coupon_wallet or 0)
    if not mkt:
        return None
    return cm1 / mkt * 100


def roi_1(revenue_predicted, direct_costs, gross_marketing_cost):
    """ROI(1) = (revenue_predicted - direct_costs) / gross_marketing_cost.
    Source: combined_entity_stats. Different from paid ROI.
    gross_marketing_cost includes all 13 spend cols + coupon + wallet + affiliate.
    """
    if not gross_marketing_cost:
        return None
    return (revenue_predicted - direct_costs) / gross_marketing_cost * 100


def paid_tr(paid_rev, offline_gross_bookings, paid_cr_ratio):
    """Paid Take Rate = paid_rev / (offline_gross_bookings * completion_rate).
    paid_cr_ratio is a ratio (0-1), not percentage.
    """
    if not offline_gross_bookings or not paid_cr_ratio:
        return None
    return paid_rev / (offline_gross_bookings * paid_cr_ratio) * 100


def paid_cr(attr_completed, attr_value):
    """Paid Completion Rate = attributed_value_completed / attributed_value.
    Returns percentage (multiply by 100).
    """
    if not attr_value:
        return None
    return attr_completed / attr_value * 100


# ============================================================================
# SIS METRICS
# ============================================================================

def sis(impressions, eligible_searches):
    """Search Impression Share = impressions / eligible_searches.
    Source: SUM(count_impressions) / SUM(count_eligible_searches).
    NOT AVG(search_impression_share) — that gives wrong results.
    """
    if not eligible_searches:
        return None
    return impressions / eligible_searches * 100
