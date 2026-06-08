-- Q2: Dimension cuts — language, page_type, device
-- Pre-filtered to {{PRIMARY_MBHO}} to keep result focused on the primary segment.
-- Each dimension is its own subquery with its own COUNT DISTINCT so users
-- are never double-counted across cuts (a user can appear on multiple page types).
--
-- Placeholders: {{CE_ID}}, {{PRE_START}}, {{PRE_END}},
--               {{POST_START}}, {{POST_END}}, {{PRIMARY_MBHO}}
--
-- Schema notes: combined_entity_id, is_microbrand_page, has_* flags, device_type

WITH base AS (

  SELECT
    user_id,
    language,
    page_type,
    device_type                                                            AS device,

    MAX(CASE WHEN page_type IN (
      'Collection', 'ShoulderPage', 'Cruises Landing Page', 'Hop-On Hop-Off',
      'Airport Transfers', 'Content Page', 'Theme', 'Collection Page', 'Experience Page'
    ) THEN 1 ELSE 0 END)                                                  AS visited_lp,
    MAX(CASE WHEN has_select_page_viewed THEN 1 ELSE 0 END)               AS visited_select,
    MAX(CASE WHEN has_checkout_started   THEN 1 ELSE 0 END)               AS checkout_started,
    MAX(CASE WHEN has_order_completed    THEN 1 ELSE 0 END)               AS order_completed,

    CASE
      WHEN event_date BETWEEN '{{PRE_START}}'  AND '{{PRE_END}}'  THEN 'pre'
      WHEN event_date BETWEEN '{{POST_START}}' AND '{{POST_END}}' THEN 'post'
    END AS period

  FROM `analytics_reporting.mixpanel_user_page_funnel_progression`

  WHERE combined_entity_id = '{{CE_ID}}'
    AND event_date BETWEEN '{{PRE_START}}' AND '{{POST_END}}'
    AND CASE WHEN is_microbrand_page THEN 'MB' ELSE 'HO' END = '{{PRIMARY_MBHO}}'
    AND (
      advertising_channel_type IS NULL
      OR advertising_channel_type != 'PERFORMANCE_MAX'
    )

  GROUP BY 1, 2, 3, 4, 9

),

-- ── Language cut ──────────────────────────────────────────────────────────────
lang AS (

  SELECT
    'language'  AS dimension,
    language    AS dimension_value,
    period,
    COUNT(DISTINCT user_id)                                              AS users_lp,
    COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END)    AS users_select,
    COUNT(DISTINCT CASE WHEN checkout_started = 1 THEN user_id END)    AS users_checkout,
    COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END)    AS users_order_completed

  FROM base
  WHERE period IS NOT NULL
  GROUP BY 1, 2, 3

),

-- ── Page-type cut ─────────────────────────────────────────────────────────────
ptype AS (

  SELECT
    'page_type' AS dimension,
    page_type   AS dimension_value,
    period,
    COUNT(DISTINCT user_id)                                              AS users_lp,
    COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END)    AS users_select,
    COUNT(DISTINCT CASE WHEN checkout_started = 1 THEN user_id END)    AS users_checkout,
    COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END)    AS users_order_completed

  FROM base
  WHERE period IS NOT NULL
    AND page_type IN (
      'Collection', 'ShoulderPage', 'Cruises Landing Page', 'Hop-On Hop-Off',
      'Airport Transfers', 'Content Page', 'Theme', 'Collection Page', 'Experience Page'
    )
  GROUP BY 1, 2, 3

),

-- ── Device cut ────────────────────────────────────────────────────────────────
dev AS (

  SELECT
    'device'    AS dimension,
    device      AS dimension_value,
    period,
    COUNT(DISTINCT user_id)                                              AS users_lp,
    COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END)    AS users_select,
    COUNT(DISTINCT CASE WHEN checkout_started = 1 THEN user_id END)    AS users_checkout,
    COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END)    AS users_order_completed

  FROM base
  WHERE period IS NOT NULL
  GROUP BY 1, 2, 3

)

SELECT * FROM lang
UNION ALL
SELECT * FROM ptype
UNION ALL
SELECT * FROM dev

ORDER BY dimension, dimension_value, period
