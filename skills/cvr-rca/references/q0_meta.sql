-- Q0: CE metadata + most-visited page URL
--
-- Runs SERIALLY before Q1 — the CE name populates the report header and the
-- top_page_url becomes the clickable link on the CE name in the sidebar.
-- Fast single-row output.
--
-- CE name from: headout-analytics.analytics_reporting.dim_combined_entities
-- Top URL from: mixpanel_user_page_funnel_progression (post period, by traffic)
--
-- Placeholders: {{CE_ID}}, {{POST_START}}, {{POST_END}}

WITH top_url AS (

    SELECT
        page_url,
        COUNT(DISTINCT user_id) AS user_count

    FROM `headout-analytics.analytics_reporting.mixpanel_user_page_funnel_progression`

    WHERE CAST(combined_entity_id AS STRING) = '{{CE_ID}}'
        AND event_date BETWEEN '{{POST_START}}' AND '{{POST_END}}'
        AND page_url IS NOT NULL
        AND page_url != ''

    GROUP BY page_url
    ORDER BY user_count DESC
    LIMIT 1

)

SELECT
    ce.combined_entity_name,
    ce.combined_entity_type,
    ce.market,
    ce.country,
    tu.page_url AS top_page_url,
    tu.user_count AS top_url_users

FROM `headout-analytics.analytics_reporting.dim_combined_entities` ce
LEFT JOIN top_url tu ON TRUE

WHERE CAST(ce.combined_entity_id AS STRING) = '{{CE_ID}}'
