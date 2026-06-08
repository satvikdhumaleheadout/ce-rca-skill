-- Q5: Daily price per experience for LP2S price sensitivity analysis
--
-- Source: analytics_features.product_rankings_features
--   product_id        = experience_id
--   original_price_usd = list price before any discount
--   final_price_usd    = displayed/selling price (what users see as "from $X")
--
-- Approach:
--   1. Find all experience_ids that belong to this CE (via the funnel table).
--   2. Pull daily original + final price for each experience across both periods.
--   3. aggregate.py then computes a traffic-weighted average price at CE level
--      and a per-experience price delta to correlate with LP2S rate changes.
--
-- Why traffic-weighted? The CE-level "effective listed price" is the blend of
-- what users actually see. Experiences with more traffic drive the perception
-- more than low-traffic experiences, so weighting by select_users from Q4
-- gives a meaningful aggregate signal.
--
-- Placeholders: {{CE_ID}}, {{PRE_START}}, {{PRE_END}}, {{POST_START}}, {{POST_END}}

WITH ce_experiences AS (

    SELECT DISTINCT
        CAST(experience_id AS STRING) AS experience_id

    FROM `analytics_reporting.mixpanel_user_page_funnel_progression`

    WHERE combined_entity_id = '{{CE_ID}}'
        AND experience_id IS NOT NULL
        AND (
            event_date BETWEEN '{{PRE_START}}' AND '{{PRE_END}}'
            OR event_date BETWEEN '{{POST_START}}' AND '{{POST_END}}'
        )

)

SELECT
    CAST(p.product_id AS STRING)                               AS experience_id,
    COALESCE(e.experience_name, CONCAT('Exp ', p.product_id)) AS experience_name,
    p.event_date,
    CASE
        WHEN p.event_date BETWEEN '{{PRE_START}}' AND '{{PRE_END}}'   THEN 'pre'
        WHEN p.event_date BETWEEN '{{POST_START}}' AND '{{POST_END}}' THEN 'post'
    END                                                        AS period,
    p.original_price_usd,
    p.final_price_usd,
    CASE
        WHEN p.final_price_usd < p.original_price_usd THEN TRUE
        ELSE FALSE
    END                                                        AS is_discount_available,
    (p.original_price_usd - p.final_price_usd)               AS discount_usd

FROM `analytics_features.product_rankings_features` p

INNER JOIN ce_experiences
    ON CAST(p.product_id AS STRING) = ce_experiences.experience_id

LEFT JOIN `analytics_reporting.dim_experiences` e
    ON CAST(e.experience_id AS STRING) = CAST(p.product_id AS STRING)

WHERE (
        p.event_date BETWEEN '{{PRE_START}}' AND '{{PRE_END}}'
        OR p.event_date BETWEEN '{{POST_START}}' AND '{{POST_END}}'
    )
    AND p.final_price_usd IS NOT NULL
    AND p.final_price_usd > 0

ORDER BY p.event_date, p.product_id
