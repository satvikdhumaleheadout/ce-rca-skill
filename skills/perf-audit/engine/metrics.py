"""
Metric definitions — single source of truth for perf audit v6.1.

Every derived metric is defined here as a function. bq.py imports these
instead of computing inline. If a formula needs to change, change it here
once — every table updates.

Validated against Omni dashboard (May 18, 2026).
All percentage metrics return as percentages (148.5 = 148.5%), not ratios.
"""

from __future__ import annotations

from itertools import permutations


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


def avg_cm1(cm1, conversions):
    """Average CM1 per conversion = CM1 / conversions.
    Equivalent to AOV × take_rate × completion_rate.
    This is what the bidding algorithm optimizes for — if avg CM1 drops,
    the algorithm can't hit tROAS targets and retreats from auctions.
    Not in any BQ table — derived from CM1 and conversion count.
    """
    if not conversions:
        return None
    return cm1 / conversions


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
# SHAPLEY DECOMPOSITION
# ============================================================================

def shapley_multiplicative(prior, current, factors):
    """Exact Shapley attribution for a multiplicative metric P = f1 * f2 * ... * fn.

    Decomposes the change (P_current - P_prior) into a per-factor contribution by
    averaging each factor's marginal effect over all n! orderings in which factors
    can flip from their prior to their current value. This is the same anchoring
    discipline CVR-RCA uses for its CVR funnel decomposition — the attribution is
    computed, not narrated.

    Args:
        prior:   dict factor_name -> value at the baseline period.
        current: dict factor_name -> value at the analysed period.
        factors: ordered list of factor names to decompose over.

    Returns:
        dict factor_name -> contribution ($ or unit of P). The contributions sum
        exactly to (P_current - P_prior) up to floating-point rounding.

    Notes:
        - Works for any n. For paid value we use 3 factors: clicks, cvr (conv/clicks),
          avg_cm1 (cm1/conv) — their product is paid CM1.
        - Handles zero/negative factor values correctly (it is pure arithmetic over
          marginal products, no logs).
    """
    names = list(factors)

    def product(state):
        p = 1.0
        for nm in names:
            p *= float(state[nm] or 0.0)
        return p

    contrib = {nm: 0.0 for nm in names}
    perms = list(permutations(names))
    for perm in perms:
        state = {nm: float(prior.get(nm) or 0.0) for nm in names}
        prev = product(state)
        for nm in perm:
            state[nm] = float(current.get(nm) or 0.0)
            cur = product(state)
            contrib[nm] += (cur - prev)
            prev = cur
    n_perms = len(perms)
    return {nm: contrib[nm] / n_perms for nm in names}


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
