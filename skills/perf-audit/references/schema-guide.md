# BigQuery Schema Guide

Tables used by the perf audit engine. All in `headout-analytics.analytics_reporting` unless noted.

---

## Primary Tables

### combined_entity_stats
CE-level daily aggregates. Revenue, orders, marketing costs.
- **CE ID column**: `combined_entity_id` (STRING)
- **Date column**: `report_date` (DATE)
- **Key columns**: `sum_revenue_predicted`, `sum_revenue`, `sum_order_value`, `sum_order_value_completed`, `count_orders`, `sum_direct_costs`
- **Spend**: 13 individual spend columns (`sum_google_ads_spend`, `sum_microsoft_ads_spend`, `sum_pmax_ads_spend`, etc.) + `sum_coupon_discount` + `sum_wallet_credits` + `sum_affiliate_commission`
- **Used in**: Table 1 (CE Health), Appendix A1, Monthly summary

### ads_campaign_stats
Campaign-level daily paid metrics across Google Ads and Microsoft Ads.
- **CE ID column**: `campaign_target_combined_entity_id` (STRING) — NOT `combined_entity_id`
- **Date column**: `report_date` (DATE)
- **Platform filter**: `ad_platform IN ('Google Ads', 'Microsoft Ads')`
- **Key columns**: `sum_spend`, `count_clicks`, `count_impressions`, `campaign_name`, `campaign_language`
- **Sep 2025 columns**: `count_conversions_offline_contribution_margin`, `sum_conversion_value_offline_contribution_margin`, `sum_conversion_value_offline_revenue`
- **Pre-Sep columns**: `count_conversions_online`, `sum_conversion_value_calculated_contribution_margin`, `sum_conversion_value_calculated_revenue`
- **SIS columns**: `count_eligible_searches`, `count_rank_lost_searches`, `count_budget_lost_searches`
- **Used in**: Table 2 (Paid Performance), Table 3 (Channel paid metrics), Cohorts, Budget, Appendix A2-A3

### fct_orders
Order-level transaction data. Ground truth for revenue attribution.
- **CE ID column**: `combined_entity_id` (STRING)
- **Date column**: `created_at` (TIMESTAMP — use `DATE(created_at)`)
- **Filters**: `order_status NOT IN ('Dummy', 'Cancelled - Fraudulent')`, `user_type = 'Customer'`
- **Key columns**: `amount_revenue_usd`, `order_value_usd`, `order_value_completed_usd`, `channel_name`, `channel_grouping`, `campaign_name`, `card_issuing_country`
- **Attribution**: `touchpoints` ARRAY<STRUCT> with `touchpoint_rank_reversed = 1` for last-touch
- **Channel taxonomy**: `channel_name` values: 'Google Ads', 'Bing Ads', 'Things to Do (Ads)', 'Things to Do (Organic)', 'Confirmation Page Recommendations', 'Organic Search'
- **Used in**: Table 3 (Channel revenue), Cohort revenue, Customer country, Campaign-level CM1

### google_ads_campaign_stats
Google Ads campaign-level metrics. More granular than ads_campaign_stats for bid/budget.
- **CE ID column**: `campaign_target_combined_entity_id` (STRING)
- **Date column**: `report_date` (DATE)
- **Key columns**: `current_campaign_target_roas`, `current_campaign_bidding_strategy`, `bidding_strategy_name`, `campaign_budget`
- **Used in**: Budget/Bidding, Cohort paid metrics

---

## Secondary Tables

### google_ads_pmax_asset_stats
PMax campaign metrics. **NOT in ads_campaign_stats** — must be queried separately.
- **CE ID column**: `combined_entity_id` (STRING)
- **Date column**: `date` (DATE, not report_date)
- **Key columns**: `sum_cost` (spend), `count_clicks`, `count_conversions`, `sum_conversion_value` (= CM1 post-Sep 2025)
- **Used in**: Table 2 PMax portion, Table 3 Google PMax

### google_ads_campaign_budget_stats
Daily budget amounts per campaign.
- **Join**: `campaign_id` + `report_date`
- **Key column**: `daily_budget`
- **Used in**: Budget table

### google_ads_ad_group_geo_stats
Geographic performance by country.
- **CE ID column**: `campaign_target_combined_entity_id` (STRING)
- **Date column**: `report_date` (DATE)
- **Key columns**: `user_country_name`, `count_clicks`, `sum_spend`, `count_conversions_online`
- **Used in**: Geo coverage table

### google_ads_ad_group_stats
Ad group level metrics.
- **CE ID column**: `campaign_target_combined_entity_id` (STRING)
- **Date column**: `report_date` (DATE)
- **Key columns**: `ad_group_name`, `count_clicks`, `sum_spend`, CM1 columns (Sep 2025 boundary applies)
- **Ad group name format**: `{Type} - {Match} - {Language} - {Location}`
- **Used in**: Ad group coverage (Section 8)

### google_ads_campaign_page_stats
Landing page performance.
- **CE ID column**: None — join via `campaign_id` subquery from google_ads_campaign_stats
- **Date column**: `date` (DATE)
- **Key columns**: `final_url`, `count_impressions`, `count_clicks`, `sum_cost`
- **GOTCHA**: `sum_cost` is in **micros** (divide by 1,000,000)
- **Used in**: Landing page table (Section 4)

### google_ads_keyword_device_stats
Keyword-level metrics with device segmentation.
- **CE ID column**: `campaign_combined_entity_id` (STRING — uses STARTS_WITH)
- **Date column**: `date` (DATE)
- **Key columns**: `keyword`, `keyword_match_type`, `count_eligible_searches`, SIS
- **Known issue**: 45 of 56 accounts stopped refreshing after Feb 2026 consolidation
- **Used in**: Keyword impression share (Section 8)

### stg_google_ads_new__campaigns
Campaign configuration (staging table).
- **Dataset**: `analytics_staging` (not analytics_reporting)
- **CE ID column**: `campaign_combined_entity_id` (STRING)
- **Key columns**: `campaign_language`, `campaign_targeting_location`, `campaign_budget_latest`, `target_roas_latest`, `campaign_status_latest`
- **Used in**: Campaign targeting (Appendix A7)

### dim_combined_entities
CE master data.
- **Key columns**: `combined_entity_id`, `combined_entity_name`, `market`
- **Used in**: CE name resolution (Step 1)

### competitor_weekly_stats
Weekly competitor GBV data.
- **CE ID column**: `combined_entity_id` (STRING)
- **Date column**: `week` (DATE)
- **Key columns**: `competitor_name`, `weekly_gbv`, `weekly_bookings`
- **Coverage**: Thin — only surfaces competitors mapped to Headout
- **Used in**: Competitor fallback

### campaign_device_stats
Device-segmented campaign metrics.
- **CE ID column**: `campaign_combined_entity_id` (STRING — different from ads_campaign_stats)
- **Date column**: `date` (DATE, not report_date)
- **Filter**: `advertising_channel_source = 'Google Ads'`
- **Used in**: Device split analysis

---

## CE ID Column Reference

| Table | CE ID Column |
|-------|-------------|
| combined_entity_stats | `combined_entity_id` |
| ads_campaign_stats | `campaign_target_combined_entity_id` |
| fct_orders | `combined_entity_id` |
| google_ads_campaign_stats | `campaign_target_combined_entity_id` |
| google_ads_pmax_asset_stats | `combined_entity_id` |
| google_ads_ad_group_geo_stats | `campaign_target_combined_entity_id` |
| google_ads_ad_group_stats | `campaign_target_combined_entity_id` |
| google_ads_keyword_device_stats | `campaign_combined_entity_id` |
| campaign_device_stats | `campaign_combined_entity_id` |
| stg_google_ads_new__campaigns | `campaign_combined_entity_id` |
| competitor_weekly_stats | `combined_entity_id` |
