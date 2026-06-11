# Metric Definitions

Validated against Omni dashboard (May 18, 2026). All percentage metrics are displayed as percentages (148.5 = 148.5%), not ratios.

Source: `engine/metrics.py`

---

## Core Metrics

### AOV (Average Order Value)
```
AOV = gross_order_value / orders
```
- Source: `sum_order_value / count_orders`
- **NOT** revenue/orders (that gives revenue per order, ~27% of AOV)

### TR (Take Rate)
```
TR = revenue / completed_gross_bookings * 100
```
- Source: `sum_revenue / sum_order_value_completed`

### CR (Completion Rate)
```
CR = completed_gross_bookings / total_gross_bookings * 100
```
- Source: `sum_order_value_completed / sum_order_value`

---

## Paid Metrics

### CPC (Cost Per Click)
```
CPC = spend / clicks
```

### CTR (Click-Through Rate)
```
CTR = clicks / impressions * 100
```

### Paid CVR (Conversion Rate)
```
Paid CVR = conversions / clicks * 100
```
- **Canonical name: "Paid CVR"** (paid-platform basis) — distinct from "Site CVR" (Mixpanel funnel,
  completed users / LP users) used in CVR-RCA / CE Health. See ce-rca `references/metric_glossary.md`.
- Source: `count_conversions_offline_contribution_margin / count_clicks`
- **Post-Sep 2025**: uses offline conversions
- **Pre-Sep 2025**: uses online conversions
- Boundary handled in SQL queries via CASE WHEN

### RPC (Revenue Per Click)
```
RPC = revenue / clicks
```
- Revenue source depends on context:
  - fct_orders for channel/cohort tables
  - ads_campaign_stats offline/calculated for Table 2

### Paid ROI
```
Paid ROI = CM1 / marketing_cost * 100
```
- Source: `contribution_margin_one / marketing_cost`
- `marketing_cost = spend + coupon_wallet`
- CM1 = offline CM1 post-Sep 2025, calculated CM1 pre-Sep

### ROI(1) — CE-Level
```
ROI(1) = (revenue_predicted - direct_costs) / gross_marketing_cost * 100
```
- Source: `combined_entity_stats`
- Different from Paid ROI (includes all 13 spend columns + coupon + wallet + affiliate)

### Paid TR (Paid Take Rate)
```
Paid TR = paid_rev / (offline_gross_bookings * completion_rate) * 100
```

### Paid CR (Paid Completion Rate)
```
Paid CR = attributed_value_completed / attributed_value * 100
```

---

## SIS (Search Impression Share)
```
SIS = SUM(impressions) / SUM(eligible_searches) * 100
```
- **NOT** `AVG(search_impression_share)` — averaging gives wrong results
- Must use SUM/SUM aggregation

---

## Key Distinctions

| Metric | Table 1 (CE) | Table 2 (Paid) | Table 3 (Channel) |
|--------|-------------|---------------|-------------------|
| Revenue | `sum_revenue_predicted` | Offline/calculated from ads_campaign_stats | `amount_revenue_usd` from fct_orders |
| ROI | ROI(1) = (rev - costs) / GMC | CM1 / (spend + coupon_wallet) | Same as Paid ROI per channel |
| Source | combined_entity_stats | ads_campaign_stats + pmax_asset_stats | fct_orders + ads_campaign_stats |

---

## Sep 2025 Boundary

All paid metrics that reference CM1 or CVR have a date boundary:

```sql
CASE
    WHEN report_date > '2025-09-01'
        AND COALESCE(offline_column, 0) > 0
    THEN offline_column
    ELSE calculated_column
END
```

This applies to:
- `sum_conversion_value_offline_contribution_margin` vs `sum_conversion_value_calculated_contribution_margin`
- `count_conversions_offline_contribution_margin` vs `count_conversions_online`
- `sum_conversion_value_offline_revenue` vs `sum_conversion_value_calculated_revenue`
