-- Q6: URL-level funnel breakdown — LP2S / S2C / C2O per page URL, pre vs post
--
-- Purpose: surface which specific URLs are dragging down conversion rates.
-- Groups users by the page_url they visited within the CE and computes how many
-- of those users went on to select / checkout / complete an order. The funnel
-- flags (has_select_page_viewed etc.) are pre-computed at the user × date × CE
-- grain, so a select page view is attributed to every URL the user visited that
-- day — acceptable as a diagnostic proxy, consistent with Q1–Q4 methodology.
--
-- Filtered to {{PRIMARY_MBHO}} so the URL analysis stays on-segment.
-- Top 20 URLs by pre-period LP traffic are returned (both periods).
-- URLs with fewer than 50 pre-period users are excluded to avoid noisy rates.
--
-- Placeholders: {{CE_ID}}, {{PRE_START}}, {{PRE_END}},
--               {{POST_START}}, {{POST_END}}, {{PRIMARY_MBHO}}

WITH base AS (

    SELECT
        user_id,
        page_url,
        page_type,
        page_sub_type,
        CASE WHEN has_select_page_viewed THEN 1 ELSE 0 END AS visited_select,
        CASE WHEN has_checkout_started   THEN 1 ELSE 0 END AS checkout_started,
        CASE WHEN has_order_completed    THEN 1 ELSE 0 END AS order_completed,

        CASE
            WHEN event_date BETWEEN '{{PRE_START}}'  AND '{{PRE_END}}'  THEN 'pre'
            WHEN event_date BETWEEN '{{POST_START}}' AND '{{POST_END}}' THEN 'post'
        END AS period

    FROM `analytics_reporting.mixpanel_user_page_funnel_progression`

    WHERE combined_entity_id = '{{CE_ID}}'
        AND event_date BETWEEN '{{PRE_START}}' AND '{{POST_END}}'
        AND CASE WHEN is_microbrand_page THEN 'MB' ELSE 'HO' END = '{{PRIMARY_MBHO}}'
        AND page_url IS NOT NULL
        AND page_url != ''
        AND (
            advertising_channel_type IS NULL
            OR advertising_channel_type != 'PERFORMANCE_MAX'
        )

),

url_agg AS (

    SELECT
        page_url,
        page_type,
        page_sub_type,
        period,

        COUNT(DISTINCT user_id)                                                   AS users_lp,
        COUNT(DISTINCT CASE WHEN visited_select  = 1 THEN user_id END)           AS users_select,
        COUNT(DISTINCT CASE WHEN checkout_started = 1 THEN user_id END)          AS users_checkout,
        COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END)          AS users_order_completed,

        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END),
            COUNT(DISTINCT user_id)
        ) AS lp2s_rate,

        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN checkout_started = 1 THEN user_id END),
            COUNT(DISTINCT CASE WHEN visited_select   = 1 THEN user_id END)
        ) AS s2c_rate,

        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN order_completed  = 1 THEN user_id END),
            COUNT(DISTINCT CASE WHEN checkout_started = 1 THEN user_id END)
        ) AS c2o_rate

    FROM base

    WHERE period IS NOT NULL

    GROUP BY 1, 2, 3, 4

    HAVING COUNT(DISTINCT user_id) >= 50

),

-- Identify the top 20 URLs by pre-period LP traffic to anchor the comparison.
-- Only pre-period volume is used for ranking so the sort is not biased by
-- post-period changes in URL traffic distribution.
top_urls AS (

    SELECT
        page_url,
        users_lp AS pre_users_lp

    FROM url_agg

    WHERE period = 'pre'

    ORDER BY users_lp DESC
    LIMIT 20

)

SELECT
    ua.page_url,
    ua.page_type,
    ua.page_sub_type,
    ua.period,
    ua.users_lp,
    ua.users_select,
    ua.users_checkout,
    ua.users_order_completed,
    ua.lp2s_rate,
    ua.s2c_rate,
    ua.c2o_rate,
    tu.pre_users_lp

FROM url_agg AS ua
INNER JOIN top_urls AS tu ON ua.page_url = tu.page_url

ORDER BY tu.pre_users_lp DESC, ua.period
