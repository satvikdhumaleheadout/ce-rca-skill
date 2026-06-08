-- Q7: 90-day rolling CVR trend — current year + last-year equivalent
--
-- Purpose: surface the time-series context invisible in a pre/post snapshot.
-- Two series in one query:
--
--   series = 'current' — daily funnel rates for the 90 days ending at POST_END.
--     The pre and post windows sit within this range as the final ~30 days.
--
--   series = 'ly' — same 90-day window shifted back 364 days (52 weeks),
--     then shifted FORWARD +364 days in the SELECT so LY dates align on the
--     same chart axis as current year. 364 = 52 × 7, which preserves weekday
--     alignment — a Monday in the current period matches a Monday in LY.
--
-- aggregate.py uses the LY-aligned dates and the CLI pre/post args to compute:
--   current_delta  = avg(post) − avg(pre) for current year
--   ly_delta       = avg(ly_post) − avg(ly_pre) using the same date window
--   structural_delta = current_delta − ly_delta
--     → positive (less negative) = the drop is partly seasonal
--     → more negative = genuine structural deterioration beyond seasonal
--
--   pre_period_healthy = TRUE if the pre-window CVR matches the prior 60-day
--     trend line; FALSE flags that the pre window itself was degraded, which
--     means Shapley understates the true change.
--
-- Deduplication pattern (mirrors Q1):
--   A base CTE collapses to one row per (user_id, event_date) using MAX() on
--   boolean funnel flags before any rate calculation. This prevents COUNTIF
--   overcounting when the table contains multiple rows per user per day
--   (e.g. one row per advertising_channel_type).
--
-- Placeholders: {{CE_ID}}, {{POST_END}}
-- POST_END is the only date input. The 90-day window is computed from it.
-- Pre/post split is applied in aggregate.py using the CLI date args.

-- ── Current year ─────────────────────────────────────────────────────────────

WITH current_base AS (

    SELECT
        event_date,
        user_id,
        MAX(CASE WHEN has_select_page_viewed   THEN 1 ELSE 0 END) AS visited_select,
        MAX(CASE WHEN has_checkout_started     THEN 1 ELSE 0 END) AS visited_checkout,
        MAX(CASE WHEN has_order_completed      THEN 1 ELSE 0 END) AS order_completed

    FROM `analytics_reporting.mixpanel_user_page_funnel_progression`

    WHERE combined_entity_id = '{{CE_ID}}'
        AND event_date BETWEEN DATE_SUB('{{POST_END}}', INTERVAL 89 DAY) AND '{{POST_END}}'
        AND (
            advertising_channel_type IS NULL
            OR advertising_channel_type != 'PERFORMANCE_MAX'
        )

    GROUP BY 1, 2

),

current_series AS (

    SELECT
        event_date,
        'current'                                                            AS series,
        COUNT(DISTINCT user_id)                                              AS users_lp,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END),
            COUNT(DISTINCT user_id))                                         AS lp2s_rate,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN visited_checkout = 1 THEN user_id END),
            COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END)) AS s2c_rate,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END),
            COUNT(DISTINCT CASE WHEN visited_checkout = 1 THEN user_id END)) AS c2o_rate,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END),
            COUNT(DISTINCT user_id))                                         AS cvr

    FROM current_base

    GROUP BY 1, 2

),

-- ── Last year (same 90-day window, shifted back 364 days) ────────────────────

ly_base AS (

    SELECT
        -- Shift dates forward 364 days so LY plots on the same x-axis as current year
        DATE_ADD(event_date, INTERVAL 364 DAY)                               AS event_date,
        user_id,
        MAX(CASE WHEN has_select_page_viewed   THEN 1 ELSE 0 END) AS visited_select,
        MAX(CASE WHEN has_checkout_started     THEN 1 ELSE 0 END) AS visited_checkout,
        MAX(CASE WHEN has_order_completed      THEN 1 ELSE 0 END) AS order_completed

    FROM `analytics_reporting.mixpanel_user_page_funnel_progression`

    WHERE combined_entity_id = '{{CE_ID}}'
        -- LY window: POST_END − 364 − 89  to  POST_END − 364
        AND event_date BETWEEN
            DATE_SUB('{{POST_END}}', INTERVAL 453 DAY)
            AND DATE_SUB('{{POST_END}}', INTERVAL 364 DAY)
        AND (
            advertising_channel_type IS NULL
            OR advertising_channel_type != 'PERFORMANCE_MAX'
        )

    GROUP BY 1, 2

),

ly_series AS (

    SELECT
        event_date,
        'ly'                                                                 AS series,
        COUNT(DISTINCT user_id)                                              AS users_lp,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END),
            COUNT(DISTINCT user_id))                                         AS lp2s_rate,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN visited_checkout = 1 THEN user_id END),
            COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END)) AS s2c_rate,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END),
            COUNT(DISTINCT CASE WHEN visited_checkout = 1 THEN user_id END)) AS c2o_rate,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END),
            COUNT(DISTINCT user_id))                                         AS cvr

    FROM ly_base

    GROUP BY 1, 2

)

SELECT * FROM current_series
UNION ALL
SELECT * FROM ly_series

ORDER BY event_date, series

-- Changelog
-- c001 2026-04-24 Initial version
-- c002 2026-04-24 Fix two bugs identified from CE 189 Vatican Museums run:
--                 (1) COUNTIF overcounting — replaced COUNTIF(has_*) with
--                     COUNT(DISTINCT CASE WHEN ... THEN user_id END) via a
--                     base CTE that collapses to one row per user per day
--                     using MAX(), mirroring Q1's deduplication pattern.
--                 (2) NULL organic traffic excluded — changed
--                     advertising_channel_type != 'PERFORMANCE_MAX' to
--                     (IS NULL OR != 'PERFORMANCE_MAX') to match Q1.
