-- Q1: Base funnel by MB/HO × Channel × Period + CE-level ALL row
-- Placeholders substituted by run_analysis.sh before execution:
--   {{CE_ID}}      CE ID string (combined_entity_id)
--   {{PRE_START}}  date string, inserted inside single quotes in WHERE
--   {{PRE_END}}    date string
--   {{POST_START}} date string
--   {{POST_END}}   date string
--
-- Schema notes (as of 2026-04):
--   combined_entity_id — CE-level filter (not experience_id)
--   is_microbrand_page — BOOL, derives mb_ho: TRUE→'MB', FALSE→'HO'
--   has_select_page_viewed / has_checkout_started / has_order_attempted
--   has_order_completed  — pre-computed BOOL funnel flags (no event_name col)
--   device_type          — device dimension (not device_id)

WITH base AS (

  SELECT
    user_id,
    CASE WHEN is_microbrand_page THEN 'MB' ELSE 'HO' END           AS mb_ho,
    CASE
      WHEN advertising_channel_type IS NOT NULL
       AND advertising_channel_type != 'PERFORMANCE_MAX' THEN 'Paid'
      ELSE 'Organic'
    END AS channel,

    MAX(CASE WHEN has_select_page_viewed THEN 1 ELSE 0 END)         AS visited_select,
    MAX(CASE WHEN has_checkout_started   THEN 1 ELSE 0 END)         AS checkout_started,
    MAX(CASE WHEN has_order_attempted    THEN 1 ELSE 0 END)         AS order_attempted,
    MAX(CASE WHEN has_order_completed    THEN 1 ELSE 0 END)         AS order_completed,

    CASE
      WHEN event_date BETWEEN '{{PRE_START}}'  AND '{{PRE_END}}'  THEN 'pre'
      WHEN event_date BETWEEN '{{POST_START}}' AND '{{POST_END}}' THEN 'post'
    END AS period

  FROM `analytics_reporting.mixpanel_user_page_funnel_progression`

  WHERE combined_entity_id = '{{CE_ID}}'
    AND event_date BETWEEN '{{PRE_START}}' AND '{{POST_END}}'
    AND page_type IN (
      'Collection', 'ShoulderPage', 'Cruises Landing Page', 'Hop-On Hop-Off',
      'Airport Transfers', 'Content Page', 'Theme', 'Collection Page', 'Experience Page'
    )
    AND (
      advertising_channel_type IS NULL
      OR advertising_channel_type != 'PERFORMANCE_MAX'
    )

  GROUP BY 1, 2, 3, 8

),

segment_agg AS (

  SELECT
    mb_ho,
    channel,
    period,
    COUNT(DISTINCT user_id)                                              AS users_lp,
    COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END)     AS users_select,
    COUNT(DISTINCT CASE WHEN checkout_started = 1 THEN user_id END)     AS users_checkout,
    COUNT(DISTINCT CASE WHEN order_attempted  = 1 THEN user_id END)     AS users_order_attempted,
    COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END)     AS users_order_completed

  FROM base
  WHERE period IS NOT NULL
  GROUP BY 1, 2, 3

),

all_agg AS (

  SELECT
    'ALL' AS mb_ho,
    'ALL' AS channel,
    period,
    COUNT(DISTINCT user_id)                                              AS users_lp,
    COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END)     AS users_select,
    COUNT(DISTINCT CASE WHEN checkout_started = 1 THEN user_id END)     AS users_checkout,
    COUNT(DISTINCT CASE WHEN order_attempted  = 1 THEN user_id END)     AS users_order_attempted,
    COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END)     AS users_order_completed

  FROM base
  WHERE period IS NOT NULL
  GROUP BY 3

)

SELECT * FROM segment_agg
UNION ALL
SELECT * FROM all_agg
ORDER BY mb_ho, channel, period
