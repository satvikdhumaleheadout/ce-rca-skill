-- Q4: Experience-level S2C and C2O breakdown — pre and post
-- Groups by individual experience within the CE (via combined_entity_id).
-- Joins dim_experiences for human-readable names.
-- Pre-filtered to {{PRIMARY_MBHO}} to match the primary segment analysis.
-- Used to surface which specific products drove step-level drops.
--
-- Note: LP2S is not meaningful at experience level because experience_id is only
-- set once a user is on an experience page — LP users are CE-level, not
-- experience-level. This query computes S2C and C2O per experience only.
--
-- Placeholders: {{CE_ID}}, {{PRE_START}}, {{PRE_END}},
--               {{POST_START}}, {{POST_END}}, {{PRIMARY_MBHO}}

SELECT
  f.experience_id,
  COALESCE(e.experience_name, CONCAT('Exp ', f.experience_id)) AS experience_name,

  CASE
    WHEN f.event_date BETWEEN '{{PRE_START}}' AND '{{PRE_END}}'   THEN 'pre'
    WHEN f.event_date BETWEEN '{{POST_START}}' AND '{{POST_END}}' THEN 'post'
  END AS period,

  COUNT(DISTINCT f.user_id)                                                AS users_select,
  COUNT(DISTINCT CASE WHEN f.has_checkout_started  THEN f.user_id END)    AS users_checkout,
  COUNT(DISTINCT CASE WHEN f.has_order_attempted   THEN f.user_id END)    AS users_order_attempted,
  COUNT(DISTINCT CASE WHEN f.has_order_completed   THEN f.user_id END)    AS users_order_completed,

  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN f.has_checkout_started THEN f.user_id END),
    COUNT(DISTINCT f.user_id)
  ) AS s2c_rate,

  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN f.has_order_completed THEN f.user_id END),
    COUNT(DISTINCT CASE WHEN f.has_checkout_started THEN f.user_id END)
  ) AS c2o_rate

FROM `analytics_reporting.mixpanel_user_page_funnel_progression` f
LEFT JOIN `analytics_reporting.dim_experiences` e
  ON e.experience_id = f.experience_id

WHERE f.combined_entity_id = '{{CE_ID}}'
  AND f.event_date BETWEEN '{{PRE_START}}' AND '{{POST_END}}'
  AND CASE WHEN f.is_microbrand_page THEN 'MB' ELSE 'HO' END = '{{PRIMARY_MBHO}}'
  AND f.experience_id IS NOT NULL
  AND f.has_select_page_viewed = TRUE
  AND (
    f.advertising_channel_type IS NULL
    OR f.advertising_channel_type != 'PERFORMANCE_MAX'
  )

GROUP BY 1, 2, 3

HAVING
  period IS NOT NULL
  AND users_select >= 50   -- filter out very small experiences

ORDER BY period, users_select DESC
