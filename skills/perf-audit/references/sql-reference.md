# Perf Audit SQL Reference

All SQL queries extracted from `engine/sources/bq.py` for standalone use (running queries directly in BigQuery console without the Python engine).

**Extraction date:** 2026-05-21
**Authoritative source:** `engine/sources/bq.py` -- if queries diverge, the Python engine is correct.

**Project/Dataset:** `headout-analytics.analytics_reporting` (except campaign targeting which uses `analytics_staging`)

---

## Critical Data Notes

### Sep 2025 CM1/CVR Boundary
- **Post 2025-09-01:** Use `sum_conversion_value_offline_contribution_margin` for CM1, `count_conversions_offline_contribution_margin` for conversions
- **Pre 2025-09-01:** Fall back to `sum_conversion_value_calculated_contribution_margin` / `count_conversions_online`
- The engine uses a CASE statement on `report_date > '2025-09-01'` to switch between them
- Same boundary applies to revenue: `sum_conversion_value_offline_revenue` vs `sum_conversion_value_calculated_revenue`

### Attribution Semantics
- `fct_orders.touchpoints` is an `ARRAY<STRUCT<campaign_id STRING, touchpoint_rank INT64, touchpoint_rank_reversed INT64, ...>>`
- `touchpoint_rank = 1` = **first touch** (earliest attribution_timestamp)
- `touchpoint_rank_reversed = 1` = **last touch** (the one this engine uses)
- `touchpoint.campaign_id` is formatted as `"1 - <numeric_id>"` -- strip the prefix with `REGEXP_EXTRACT(r'\d+$')` before casting to INT64

### PMax Lives in a Separate Table
- PMax data is in `google_ads_pmax_asset_stats`, NOT in `ads_campaign_stats`
- The engine queries both and merges in Python
- `sum_conversion_value` in pmax_asset_stats = CM1 (post-Sep 2025)
- `sum_cost` in pmax_asset_stats = spend (not `sum_spend`)
- Date column is `date`, not `report_date`

### campaign_page_stats Cost is in Micros
- `google_ads_campaign_page_stats.sum_cost` is in **micros** -- divide by 1,000,000 to get USD
- Date column is `date`, not `report_date`

### CE ID Column Name Varies by Table
| Table | CE ID Column |
|-------|-------------|
| `fct_orders` | `combined_entity_id` |
| `combined_entity_stats` | `combined_entity_id` |
| `ads_campaign_stats` | `campaign_target_combined_entity_id` |
| `google_ads_campaign_stats` | `campaign_target_combined_entity_id` |
| `google_ads_ad_group_stats` | `campaign_target_combined_entity_id` |
| `google_ads_ad_group_geo_stats` | `campaign_target_combined_entity_id` |
| `google_ads_pmax_asset_stats` | `combined_entity_id` |
| `google_ads_keyword_device_stats` | `campaign_combined_entity_id` (uses `STARTS_WITH`, not `=`) |
| `campaign_device_stats` | `campaign_combined_entity_id` |
| `competitor_weekly_stats` | `combined_entity_id` (STRING column) |
| `stg_google_ads_new__campaigns` | `campaign_combined_entity_id` |
| `google_ads_campaign_budget_stats` | joined via `campaign_id` + `report_date` |
| `google_ads_campaign_page_stats` | no CE ID -- join via campaign_id subquery |
| `dim_combined_entities` | `combined_entity_id` |

### Channel Taxonomy (v6.1)
The engine classifies `fct_orders` rows into channels using `channel_name`, `campaign_name`, and `channel_grouping`:

| Channel | Classification Logic |
|---------|---------------------|
| Google Search | `channel_name = 'Google Ads'` AND campaign_name contains `cid{ce_id}` |
| Bing | `channel_name = 'Bing Ads'` AND campaign_name contains `cid{ce_id}`, OR `channel_name = 'Google Ads'` AND `campaign_name LIKE '1 - %'` (Bing misclassification) |
| Google PMax | `channel_name = 'Google Ads'` AND campaign_name matches `pmax\|performance.max` |
| Google Cross-sell | `channel_name = 'Google Ads'` (remaining) |
| Bing Cross-sell | `channel_name = 'Bing Ads'` (remaining) |
| TTD (Paid) | `channel_name = 'Things to Do (Ads)'` |
| TTD (Organic) | `channel_name = 'Things to Do (Organic)'` |
| CPR | `channel_name = 'Confirmation Page Recommendations'` |
| Organic | `channel_name = 'Organic Search'` |
| Direct (App) | `channel_grouping = 'Direct (App)'` |
| Direct | `channel_grouping = 'Direct'` |
| Affiliates | `channel_grouping = 'Affiliates'` |
| Email | `channel_grouping = 'Email'` |
| Referral | `channel_grouping = 'Referral'` |
| Other | Everything else |

### ROI / Marketing Cost Formulas
- **ROI(1)** (Table 1, combined_entity_stats): `(revenue - direct_costs) / gross_marketing_cost`
  - `gross_marketing_cost` = sum of ALL spend columns + coupon + wallet + affiliate commission
- **Paid ROI** (Table 2, ads_campaign_stats): `CM1 / (ad_spend + coupon_wallet)`
  - Denominator includes `sum_coupon_and_wallet_credits`
- **Paid TR** (Table 2): `revenue / (offline_gb * paid_cr)` where `paid_cr = attr_completed / attr_val`

### Reconciliation Warning
Campaign-level CM1 sum != CE-level CM1 exactly. Target tolerance is ~20%, not 5%. Gaps >30% usually indicate heavy organic/offline orders (no paid touchpoint) or tracking drift.

---

## Section 2: CE Health -- `fetch_ce_health`

**Table:** `combined_entity_stats`
**Purpose:** Table 1 in the CE Snapshot. Returns CE-level revenue, orders, ROI(1), TR, CR, AOV.
**Windows:** Called 3x (L4W, P4W, LY) via `fetch_ce_health_3w`.

```sql
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
FROM `headout-analytics.analytics_reporting.combined_entity_stats`
WHERE combined_entity_id = '{ce_id}'
    AND report_date BETWEEN '{start}' AND '{end}'
```

**Post-processing:**
- `cm1 = revenue - direct_costs`
- `roi_1 = cm1 / gross_marketing_cost * 100`
- `tr = revenue_actual / gross_bookings_completed * 100`
- `cr = gross_bookings_completed / gross_bookings * 100`
- `aov = gross_bookings / orders`

---

## Section 3: Channel Breakdown -- `fetch_channel_breakdown`

Called via `_fetch_channel_window_v2` for 3 windows (TW, LY, Prior 4W) + `_fetch_monthly_summary` for L12M trajectory.

### Sub-query 1: Revenue from fct_orders

**Table:** `fct_orders`
**Purpose:** Revenue side of channel breakdown. Classifies orders into channels using the taxonomy above.

```sql
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
    FROM `headout-analytics.analytics_reporting.fct_orders`
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
```

**Gotcha:** The `%%` in `LIKE '1 - %%'` is Python string escaping -- in raw SQL use `LIKE '1 - %'`.

### Sub-query 2: Paid metrics from ads_campaign_stats

**Table:** `ads_campaign_stats`
**Purpose:** Paid metrics (spend, clicks, CVR, CM1, ROI) for Google Search, Google PMax, Google Cross-sell, Bing.

```sql
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
FROM `headout-analytics.analytics_reporting.ads_campaign_stats`
WHERE campaign_target_combined_entity_id = '{ce_id}'
    AND report_date BETWEEN '{start}' AND '{end}'
    AND ad_platform IN ('Google Ads', 'Microsoft Ads')
GROUP BY 1
```

**Gotcha:** Sep 2025 boundary -- three separate CASE blocks for conversions, revenue, and CM1.

### Sub-query 3: PMax from google_ads_pmax_asset_stats

**Table:** `google_ads_pmax_asset_stats`
**Purpose:** PMax paid metrics (NOT in ads_campaign_stats). Merged into channel="Google PMax".

```sql
SELECT
    SUM(sum_cost) AS spend,
    SUM(count_clicks) AS clicks,
    SUM(count_conversions) AS conversions,
    SUM(sum_conversion_value) AS cm1
FROM `headout-analytics.analytics_reporting.google_ads_pmax_asset_stats`
WHERE combined_entity_id = '{ce_id}'
    AND date BETWEEN '{start}' AND '{end}'
```

**Gotchas:**
- Column is `sum_cost` not `sum_spend`
- Column is `date` not `report_date`
- `sum_conversion_value` = CM1 (post-Sep 2025)
- CE ID column is `combined_entity_id` (not `campaign_target_...`)

### Python Merge Logic (Channel Breakdown)

Revenue rows (fct_orders) are the primary set. For each revenue row, paid metrics are looked up by channel name and merged:
- `cpc = spend / clicks`
- `cvr = conversions / clicks * 100`
- `cm1 = cm1` (from paid query)
- `roi = cm1 / (spend + coupon_wallet) * 100`
- `rpc = paid_rev / clicks` (or `revenue / clicks` for PMax since PMax has no paid_rev)

If PMax data exists in the pmax query, it overwrites the `Google PMax` entry from the ads_campaign_stats query.

---

## Section 3 (continued): Monthly Summary -- `_fetch_monthly_summary`

**Tables:** `combined_entity_stats` + `ads_campaign_stats`
**Purpose:** L12M monthly trajectory for CE-level and paid-level metrics. Feeds snapshot narrative.

```sql
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
    FROM `headout-analytics.analytics_reporting.combined_entity_stats`
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
        SUM(count_conversions_offline_contribution_margin) AS conv_offline,
        SUM(count_conversions_online) AS conv_online,
        SUM(sum_conversion_value_offline_contribution_margin) AS cm1_offline,
        SUM(sum_conversion_value_calculated_contribution_margin) AS cm1_calc,
        SUM(sum_coupon_and_wallet_credits) AS coupon_wallet
    FROM `headout-analytics.analytics_reporting.ads_campaign_stats`
    WHERE campaign_target_combined_entity_id = '{ce_id}'
        AND report_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)
            AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND ad_platform IN ('Google Ads', 'Microsoft Ads')
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
    p.clicks AS paid_clicks,
    p.ad_spend AS paid_spend,
    CASE WHEN p.cm1_offline > 0 THEN p.cm1_offline ELSE p.cm1_calc END AS paid_cm1,
    SAFE_DIVIDE(
        CASE WHEN p.cm1_offline > 0 THEN p.cm1_offline ELSE p.cm1_calc END,
        p.ad_spend + p.coupon_wallet
    ) AS paid_roi,
    SAFE_DIVIDE(p.ad_spend, p.clicks) AS paid_cpc,
    SAFE_DIVIDE(
        CASE WHEN p.conv_offline > 0 THEN p.conv_offline ELSE p.conv_online END,
        p.clicks
    ) AS paid_cvr
FROM ce_monthly c
LEFT JOIN paid_monthly p USING (month)
ORDER BY c.month
```

**Gotcha:** The monthly summary does NOT use the Sep 2025 date-level boundary -- it uses a simpler "if offline > 0 then offline else calculated" fallback. This is because monthly aggregation spans across the boundary.

---

## Section 4: Paid Performance -- `fetch_paid_performance`

Called 3x (L4W, P4W, LY) via `fetch_paid_performance_3w`.

### Sub-query 1: ads_campaign_stats (Search + Bing)

**Table:** `ads_campaign_stats`
**Purpose:** Table 2 in CE Snapshot. All paid metrics except PMax.

```sql
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
FROM `headout-analytics.analytics_reporting.ads_campaign_stats`
WHERE campaign_target_combined_entity_id = '{ce_id}'
    AND report_date BETWEEN '{start}' AND '{end}'
    AND ad_platform IN ('Google Ads', 'Microsoft Ads')
```

### Sub-query 2: PMax from google_ads_pmax_asset_stats

Same query as Section 3 Sub-query 3 (see above).

```sql
SELECT
    SUM(count_clicks) AS clicks,
    SUM(count_impressions) AS impressions,
    SUM(sum_cost) AS spend,
    SUM(count_conversions) AS conversions,
    SUM(sum_conversion_value) AS cm1
FROM `headout-analytics.analytics_reporting.google_ads_pmax_asset_stats`
WHERE combined_entity_id = '{ce_id}'
    AND date BETWEEN '{start}' AND '{end}'
```

**Post-processing (Python merge):**
1. Resolve Sep 2025 boundary: `ads_rev = rev_offline if rev_offline > 0 else rev_calc` (same for cm1, conv)
2. Add PMax clicks, impressions, spend, conversions, cm1 to the ads totals
3. Derive metrics:
   - `paid_roi = cm1 / (spend + coupon_wallet) * 100`
   - `rpc = paid_rev / clicks`
   - `cpc = spend / clicks`
   - `cvr = conversions / clicks * 100`
   - `paid_tr = paid_rev / (offline_gb * paid_cr) * 100` where `paid_cr = attr_completed / attr_val`

---

## Section 4: All-Paid Metrics (CE Snapshot Table 1 supplement) -- `fetch_all_paid_metrics`

**Tables:** `combined_entity_stats` + `fct_orders`
**Purpose:** Paid-specific metrics for the CE Snapshot. Uses combined_entity_stats for clicks/impressions/spend and fct_orders for paid orders/revenue.
**Windows:** Called 3x (TW, P4W, LY).

### Ads sub-query (from combined_entity_stats)

```sql
SELECT
    ROUND(SUM(count_ad_clicks), 0) AS paid_clicks,
    ROUND(SUM(count_ad_impressions), 0) AS paid_impressions,
    ROUND(SUM(
        COALESCE(sum_google_ads_spend, 0)
        + COALESCE(sum_microsoft_ads_spend, 0)
        + COALESCE(sum_pmax_ads_spend, 0)
    ), 0) AS paid_spend
FROM `headout-analytics.analytics_reporting.combined_entity_stats`
WHERE combined_entity_id = '{ce_id}'
    AND report_date BETWEEN '{start}' AND '{end}'
```

### Orders sub-query (from fct_orders)

```sql
SELECT
    COUNT(*) AS paid_orders,
    ROUND(SUM(amount_revenue_usd), 0) AS paid_revenue
FROM `headout-analytics.analytics_reporting.fct_orders`
WHERE combined_entity_id = '{ce_id}'
    AND order_status = 'Completed'
    AND channel_grouping = 'Paid'
    AND DATE(created_at) BETWEEN '{start}' AND '{end}'
```

**Post-processing:**
- `paid_cpc = spend / clicks`
- `paid_cvr = paid_orders / clicks`

**Gotcha:** This function filters fct_orders to `order_status = 'Completed'` AND `channel_grouping = 'Paid'`, which is stricter than the channel breakdown query.

---

## Section 5: Campaign Cohorts -- `fetch_campaign_cohorts`

Called for 3 windows (TW, LY, Prior 4W) via `_fetch_cohort_window` + L12M monthly via `_fetch_cohort_monthly`.

### Revenue sub-query (from fct_orders, grouped by language)

**Table:** `fct_orders`
**Purpose:** Revenue side of campaign cohorts. Classifies by language extracted from campaign_name.

```sql
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
FROM `headout-analytics.analytics_reporting.fct_orders`
WHERE combined_entity_id = '{ce_id}'
    AND DATE(created_at) BETWEEN '{start}' AND '{end}'
    AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
    AND user_type = 'Customer'
    AND channel_name = 'Google Ads'
    AND REGEXP_CONTAINS(campaign_name, CONCAT('cid', '{ce_id}'))
    AND NOT REGEXP_CONTAINS(LOWER(COALESCE(campaign_name, '')), r'pmax|performance.max')
GROUP BY 1
```

**Gotcha:** Filters to `channel_name = 'Google Ads'` + `cid{ce_id}` + NOT PMax -- so this is Google Search Same-Cat only. Bing and PMax are excluded from cohort revenue.

### Paid sub-query (from google_ads_campaign_stats, grouped by campaign_language)

**Table:** `google_ads_campaign_stats`
**Purpose:** Paid metrics for cohorts. Grouped by `campaign_language` code (EN, FR, DE, etc.).

```sql
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
FROM `headout-analytics.analytics_reporting.google_ads_campaign_stats`
WHERE campaign_target_combined_entity_id = '{ce_id}'
    AND report_date BETWEEN '{start}' AND '{end}'
GROUP BY 1
```

**Post-processing (Python merge):**
- Language codes mapped: EN->English, ES->Spanish, OL->Other Languages, FR->French, DE->German, IT->Italian, PT->Portuguese, NL->Dutch, PL->Polish, RU->Russian, TR->Turkish, All->Other
- Paid map merged with revenue rows by cohort name
- Derived: `rpc`, `cpc`, `ctr`, `cvr`, `aov`, `tr`, `cr`, `roi`, `avg_sis`
- SIS = impressions / eligible_searches (true SIS, stored as fraction in BQ, multiplied by 100)
- Results sorted by revenue DESC

---

## Section 5 (continued): Monthly Cohort -- `_fetch_cohort_monthly`

**Table:** `ads_campaign_stats`
**Purpose:** L12M monthly metrics per language cohort for trajectory analysis.

```sql
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
FROM `headout-analytics.analytics_reporting.ads_campaign_stats`
WHERE campaign_target_combined_entity_id = '{ce_id}'
    AND report_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)
        AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    AND ad_platform IN ('Google Ads', 'Microsoft Ads')
GROUP BY 1, 2
ORDER BY 1, 2
```

**Post-processing:**
- Per row: `cpc`, `cvr` (conv/clicks*100), `roi` (cm1/(spend+cw)*100), `rpc` (rev/clicks), `sis` (*100)

---

## Section 5: Budget/Bidding -- `fetch_budget_bidding`

**Tables:** `google_ads_campaign_stats` LEFT JOIN `google_ads_campaign_budget_stats`
**Purpose:** Campaign-level budget utilization, SIS, tROAS, bidding strategy.

```sql
SELECT
    g.campaign_name,
    g.campaign_id,
    ANY_VALUE(g.current_campaign_target_roas) AS troas_target,
    ANY_VALUE(g.current_campaign_bidding_strategy) AS bid_strategy,
    ANY_VALUE(g.bidding_strategy_name) AS bidding_strategy_name,
    ANY_VALUE(b.daily_budget) AS daily_budget,
    SUM(g.sum_spend) AS spend,
    SAFE_DIVIDE(SUM(g.count_impressions), SUM(g.count_eligible_searches)) AS sis,
    SAFE_DIVIDE(SUM(g.count_budget_lost_searches),
        NULLIF(SUM(g.count_eligible_searches), 0)) AS budget_lost_is,
    SAFE_DIVIDE(SUM(g.count_rank_lost_searches),
        NULLIF(SUM(g.count_eligible_searches), 0)) AS rank_lost_is
FROM `headout-analytics.analytics_reporting.google_ads_campaign_stats` g
LEFT JOIN `headout-analytics.analytics_reporting.google_ads_campaign_budget_stats` b
    USING (campaign_id, report_date)
WHERE g.campaign_target_combined_entity_id = '{ce_id}'
    AND g.report_date BETWEEN '{start}' AND '{end}'
GROUP BY 1, 2
ORDER BY spend DESC
```

**Post-processing:**
- SIS, budget_lost_is, rank_lost_is all multiplied by 100 (stored as fractions)
- `campaign_type` = "Portfolio" if `bidding_strategy_name` is set, else "Individual"

---

## Section 5: Geo Coverage -- `fetch_geo_coverage`

**Table:** `google_ads_ad_group_geo_stats`
**Purpose:** Geographic ad coverage -- top 15 countries by clicks.
**Windows:** Called 2x (L4W, LY) via `fetch_geo_coverage_3w`.

```sql
SELECT
    user_country_name AS country,
    SUM(count_clicks) AS clicks,
    SUM(count_impressions) AS impressions,
    SUM(sum_spend) AS spend,
    SUM(count_conversions_online) AS conversions,
    SUM(sum_conversion_value_offline_contribution_margin) AS cm1
FROM `headout-analytics.analytics_reporting.google_ads_ad_group_geo_stats`
WHERE campaign_target_combined_entity_id = '{ce_id}'
    AND report_date BETWEEN '{start}' AND '{end}'
GROUP BY 1
ORDER BY clicks DESC
LIMIT 15
```

**Post-processing:**
- `cpc = spend / clicks`
- `cvr = conversions / clicks * 100`

---

## Section 5: Customer Country Distribution -- `fetch_customer_country_distribution`

**Table:** `fct_orders`
**Purpose:** Where customers come from (card issuing country) for geo gap analysis.
**Windows:** Called 2x (L4W, LY) via `fetch_customer_country_3w`.

```sql
SELECT
    card_issuing_country AS customer_country,
    COUNT(DISTINCT order_id) AS orders,
    SUM(amount_revenue_usd) AS revenue
FROM `headout-analytics.analytics_reporting.fct_orders`
WHERE combined_entity_id = '{ce_id}'
    AND DATE(created_at) BETWEEN '{start}' AND '{end}'
    AND order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')
    AND user_type = 'Customer'
    AND card_issuing_country IS NOT NULL
GROUP BY 1
ORDER BY orders DESC
LIMIT 20
```

---

## Section 4: Landing Pages -- `fetch_landing_page_performance`

**Tables:** `google_ads_campaign_stats` (for CE campaign IDs) + `google_ads_campaign_page_stats`
**Purpose:** Landing page performance. Requires a subquery because campaign_page_stats has no CE ID.
**Windows:** L4W + optionally LY.

```sql
WITH ce_campaigns AS (
    SELECT DISTINCT campaign_id
    FROM `headout-analytics.analytics_reporting.google_ads_campaign_stats`
    WHERE campaign_target_combined_entity_id = '{ce_id}'
        AND report_date BETWEEN '{start}' AND '{end}'
)
SELECT
    lp.final_url,
    SUM(lp.count_impressions) AS impressions,
    SUM(lp.count_clicks) AS clicks,
    SUM(lp.sum_cost) AS spend
FROM `headout-analytics.analytics_reporting.google_ads_campaign_page_stats` lp
INNER JOIN ce_campaigns c USING (campaign_id)
WHERE lp.date BETWEEN '{start}' AND '{end}'
GROUP BY 1
HAVING SUM(lp.count_clicks) >= 100
ORDER BY clicks DESC
LIMIT 10
```

**Gotchas:**
- `sum_cost` is in **micros** -- divide by 1,000,000 for USD
- Date column is `date`, not `report_date`
- No CE ID on campaign_page_stats -- must join via campaign_id subquery
- HAVING filters to pages with >= 100 clicks

**Post-processing:**
- `spend = sum_cost / 1_000_000`
- `ctr = clicks / impressions * 100`
- `cpc = spend / clicks`

---

## Section 8: Ad Groups -- `fetch_ad_group_performance`

**Table:** `google_ads_ad_group_stats`
**Purpose:** Ad group level performance metrics.

```sql
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
FROM `headout-analytics.analytics_reporting.google_ads_ad_group_stats`
WHERE campaign_target_combined_entity_id = '{ce_id}'
    AND report_date BETWEEN '{start}' AND '{end}'
GROUP BY 1, 2
ORDER BY clicks DESC
```

**Gotcha:** CM1 fallback uses `sum_conversions_value` (not `sum_conversion_value_calculated_contribution_margin`) -- different from ads_campaign_stats.

**Post-processing:**
- `cpc`, `cvr` (conv/clicks*100), `ctr` (clicks/imp*100), `roi` (cm1/spend*100)

### Ad Groups by Type -- `fetch_ad_group_by_type`

No separate SQL. Calls `fetch_ad_group_performance` and then aggregates in Python:
- Parses ad group name: `{Type} - {Match} - {Language} - {Location}`
- Groups by Type (Tickets, Generic, Tour, DSA, etc.)
- Tracks which languages have clicks per type
- Aggregates clicks, spend, conversions, cm1, impressions, ad group count

---

## Section 8: Keyword Impression Share -- `fetch_keyword_impression_share`

**Table:** `google_ads_keyword_device_stats`
**Purpose:** Keyword-level impression share, aggregated across devices. Top 50 by clicks.

```sql
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
FROM `headout-analytics.analytics_reporting.google_ads_keyword_device_stats`
WHERE STARTS_WITH(campaign_combined_entity_id, '{ce_id}')
    AND date BETWEEN '{start}' AND '{end}'
    AND is_negative = FALSE
GROUP BY 1, 2
ORDER BY clicks DESC
LIMIT 50
```

**Gotchas:**
- Uses `STARTS_WITH(campaign_combined_entity_id, ...)` not `= ...`
- CE ID column is `campaign_combined_entity_id`
- Date column is `date` not `report_date`
- `is_negative = FALSE` filters out negative keywords

**Post-processing:**
- `sis` multiplied by 100
- `cpc`, `cvr` (conv/clicks*100), `ctr` (clicks/imp*100)

---

## Campaign Targeting -- `fetch_campaign_targeting`

**Table:** `stg_google_ads_new__campaigns` (in `analytics_staging` schema, NOT `analytics_reporting`)
**Purpose:** Active campaign configuration -- geo, language, budget, bidding strategy.

```sql
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
FROM `headout-analytics.analytics_staging.stg_google_ads_new__campaigns`
WHERE campaign_combined_entity_id = '{ce_id}'
    AND campaign_status_latest = 'ENABLED'
QUALIFY ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY date DESC) = 1
ORDER BY campaign_name
```

**Gotchas:**
- Different schema: `analytics_staging`, not `analytics_reporting`
- CE ID column: `campaign_combined_entity_id`
- Uses QUALIFY (BigQuery feature) instead of subquery for deduplication
- Only returns ENABLED campaigns (latest row per campaign_id)

---

## Competitors -- `fetch_competitors_bq`

**Table:** `competitor_weekly_stats`
**Purpose:** Top 10 competitors for this CE. BQ fallback tier (coverage is thin).

```sql
SELECT
    competitor_name,
    ANY_VALUE(is_mapped_to_headout) AS is_mapped_to_headout,
    SUM(COALESCE(weekly_gbv, 0)) AS gbv_4w,
    SUM(COALESCE(weekly_bookings, 0)) AS bookings_4w,
    ANY_VALUE(trailing_4_week_gbv) AS trailing_gbv
FROM `headout-analytics.analytics_reporting.competitor_weekly_stats`
WHERE combined_entity_id = '{ce_id}'
    AND week BETWEEN '{start}' AND '{end}'
GROUP BY competitor_name
ORDER BY gbv_4w DESC
LIMIT 10
```

**Gotcha:** `combined_entity_id` is a STRING column on this table. Date column is `week`.

---

## Market Benchmarks -- `fetch_market_benchmarks`

**Tables:** `combined_entity_stats` + `ads_campaign_stats` + `dim_combined_entities`
**Purpose:** Market-level medians (SIS, CPC, CTR, CVR, ROAS) for peer CEs, excluding this CE.
**Returns None if < 3 peer CEs in market.**

```sql
WITH ce_stats AS (
    SELECT
        c.combined_entity_id,
        SUM(CASE WHEN c.report_date BETWEEN '{tw_start}' AND '{tw_end}' THEN c.sum_revenue ELSE 0 END) AS tw_revenue,
        SUM(CASE WHEN c.report_date BETWEEN '{ly_start}' AND '{ly_end}' THEN c.sum_revenue ELSE 0 END) AS ly_revenue
    FROM `headout-analytics.analytics_reporting.combined_entity_stats` c
    JOIN `headout-analytics.analytics_reporting.dim_combined_entities` d
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
    FROM `headout-analytics.analytics_reporting.ads_campaign_stats` a
    JOIN `headout-analytics.analytics_reporting.dim_combined_entities` d
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
```

**Gotcha:** Uses `search_impression_share` (pre-computed column on ads_campaign_stats) for SIS AVG, not the impressions/eligible_searches computation used elsewhere. Also uses `sum_conversion_value_online` for ROAS (not the offline/calculated boundary logic).

**Additional parameters:** `{market}` (e.g., "France"), `{tw_start}`, `{tw_end}`, `{ly_start}`, `{ly_end}`, `{ce_id}`.

---

## Device Split -- `fetch_device_split`

**Table:** `campaign_device_stats`
**Purpose:** Device-segmented stats (mobile, desktop, tablet).

```sql
SELECT
    device,
    SUM(sum_spend) AS spend,
    SUM(count_clicks) AS clicks,
    SUM(count_impressions) AS impressions,
    SUM(COALESCE(count_conversions, 0)) AS conversions,
    SUM(COALESCE(sum_conversion_value, 0)) AS conversion_value
FROM `headout-analytics.analytics_reporting.campaign_device_stats`
WHERE campaign_combined_entity_id = '{ce_id}'
    AND date BETWEEN '{start}' AND '{end}'
    AND advertising_channel_source = 'Google Ads'
GROUP BY device
ORDER BY spend DESC
```

**Gotchas:**
- CE ID column: `campaign_combined_entity_id`
- Date column: `date`, not `report_date`
- Filtered to `advertising_channel_source = 'Google Ads'` only

---

## Campaign-level CM1/ROI -- `fetch_campaign_level_cm1_roi`

**Tables:** `fct_orders` (touchpoint attribution) + `google_ads_campaign_stats`
**Purpose:** Per-campaign CM1 and ROI using last-touch attribution from fct_orders touchpoints. Called for TW and LY windows.

```sql
WITH orders_attr AS (
    SELECT
        CAST(REGEXP_EXTRACT(t.campaign_id, r'\d+$') AS INT64) AS campaign_id,
        SUM(o.amount_revenue_usd) AS revenue,
        SUM(o.amount_direct_costs_usd) AS direct_costs,
        SUM(COALESCE(o.amount_coupon_discount_usd, 0)) AS coupons,
        SUM(COALESCE(o.wallet_credits_usd, 0)) AS wallet_credits
    FROM `headout-analytics.analytics_reporting.fct_orders` o,
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
    FROM `headout-analytics.analytics_reporting.google_ads_campaign_stats` g
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
```

**Gotchas:**
- `touchpoint.campaign_id` format is `"1 - <numeric_id>"` -- `REGEXP_EXTRACT(r'\d+$')` strips the prefix
- `orders_attr` CTE is NOT filtered by CE -- it joins ALL orders with touchpoints. The CE filter is only on `spend_agg` via `campaign_target_combined_entity_id`. The LEFT JOIN restricts to campaigns belonging to this CE.
- `roi = cm1 / spend` (NOT `cm1 / (spend + coupon_wallet)` -- different from Table 2 formula)
- Campaigns with spend=0 are excluded (`WHERE s.spend > 0`)
- Campaign-level CM1 SUM will NOT match CE-level CM1. Target tolerance ~20%, >30% = tracking drift.

---

## Quick Reference: All BQ Tables Used

| Table | Schema | Used In |
|-------|--------|---------|
| `fct_orders` | analytics_reporting | Channel Breakdown, Campaign Cohorts, Customer Country, All-Paid Metrics, Campaign-level CM1 |
| `combined_entity_stats` | analytics_reporting | CE Health, Monthly Summary, All-Paid Metrics, Market Benchmarks |
| `ads_campaign_stats` | analytics_reporting | Channel Breakdown, Monthly Summary, Paid Performance, Monthly Cohort, Market Benchmarks |
| `google_ads_campaign_stats` | analytics_reporting | Campaign Cohorts, Budget/Bidding, Landing Pages (subquery), Campaign-level CM1 |
| `google_ads_pmax_asset_stats` | analytics_reporting | Channel Breakdown, Paid Performance |
| `google_ads_ad_group_geo_stats` | analytics_reporting | Geo Coverage |
| `google_ads_ad_group_stats` | analytics_reporting | Ad Group Performance |
| `google_ads_campaign_page_stats` | analytics_reporting | Landing Pages |
| `google_ads_campaign_budget_stats` | analytics_reporting | Budget/Bidding |
| `google_ads_keyword_device_stats` | analytics_reporting | Keyword IS |
| `campaign_device_stats` | analytics_reporting | Device Split |
| `competitor_weekly_stats` | analytics_reporting | Competitors |
| `dim_combined_entities` | analytics_reporting | Market Benchmarks |
| `stg_google_ads_new__campaigns` | analytics_staging | Campaign Targeting |
