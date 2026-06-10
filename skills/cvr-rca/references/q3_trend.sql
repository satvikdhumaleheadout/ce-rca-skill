-- Q3: Daily funnel rates — pre and post period
-- Used by Claude to spot sudden drops vs gradual drift,
-- and by render.py to draw LP2S/S2C/C2O sparkline charts.
-- Pre-filtered to {{PRIMARY_MBHO}} to match the primary segment analysis.
--
-- Placeholders: {{CE_ID}}, {{PRE_START}}, {{PRE_END}},
--               {{POST_START}}, {{POST_END}}, {{PRIMARY_MBHO}}
--
-- Schema notes: combined_entity_id, is_microbrand_page, has_* flags

WITH base AS (

  SELECT
    event_date,
    CASE
      WHEN event_date BETWEEN '{{PRE_START}}'  AND '{{PRE_END}}'  THEN 'pre'
      WHEN event_date BETWEEN '{{POST_START}}' AND '{{POST_END}}' THEN 'post'
    END AS period,
    user_id,
    has_select_page_viewed,
    has_checkout_started,
    has_order_completed

  FROM `analytics_reporting.mixpanel_user_page_funnel_progression`

  WHERE combined_entity_id = '{{CE_ID}}'
    AND event_date BETWEEN '{{PRE_START}}' AND '{{POST_END}}'
    AND CASE WHEN is_microbrand_page THEN 'MB' ELSE 'HO' END = '{{PRIMARY_MBHO}}'
    -- No page_type whitelist: matches the Omni dashboard funnel (all landing page types).
    AND (
      advertising_channel_type IS NULL
      OR advertising_channel_type != 'PERFORMANCE_MAX'
    )

)

SELECT
  event_date,
  period,

  COUNT(DISTINCT user_id)                                                  AS users_lp,

  COUNT(DISTINCT CASE WHEN has_select_page_viewed THEN user_id END)        AS users_select,

  COUNT(DISTINCT CASE WHEN has_checkout_started   THEN user_id END)        AS users_checkout,

  COUNT(DISTINCT CASE WHEN has_order_completed    THEN user_id END)        AS users_order_completed,

  -- Pre-compute rates in BQ to save Python round-trips
  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN has_select_page_viewed THEN user_id END),
    COUNT(DISTINCT user_id)
  ) AS lp2s_rate,

  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN has_checkout_started THEN user_id END),
    COUNT(DISTINCT CASE WHEN has_select_page_viewed THEN user_id END)
  ) AS s2c_rate,

  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN has_order_completed THEN user_id END),
    COUNT(DISTINCT CASE WHEN has_checkout_started THEN user_id END)
  ) AS c2o_rate

FROM base
WHERE period IS NOT NULL
GROUP BY 1, 2
ORDER BY period, event_date
