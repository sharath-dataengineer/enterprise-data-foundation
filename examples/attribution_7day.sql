-- 7-day first-touch attribution
--
-- Rule: attribute a booking to the FIRST advisor who made a qualifying
-- recommendation in the 7 days BEFORE the order close, matched on
-- company + product family. First touch within the window wins; bookings
-- with no qualifying recommendation are flagged is_attributed = 0.
--
-- Subtlety this query gets right: "first touch" is evaluated RELATIVE TO each
-- booking's 7-day window — not the globally-earliest recommendation. Picking
-- the global first touch and then filtering by the window drops valid
-- attributions whenever the earliest recommendation falls outside the window.
--
-- Engine: Spark SQL. Anonymized — table/column names are illustrative.
-- The same rule is implemented and unit-tested in attribution.py (see tests/).

WITH bookings AS (
    SELECT
        booking_id,
        company_id,
        product_family,
        order_amount,
        units_booked,
        order_close_ts,
        run_date
    FROM analytics_mart.fact_booking
    WHERE run_date = CURRENT_DATE
),

-- All qualifying recommendations that fall within each booking's 7-day window,
-- ranked earliest-first PER BOOKING.
candidates AS (
    SELECT
        b.booking_id,
        r.advisor_id,
        r.recommendation_id,
        r.contact_id,
        r.recommendation_ts,
        ROW_NUMBER() OVER (
            PARTITION BY b.booking_id
            ORDER BY r.recommendation_ts ASC
        ) AS touch_rank
    FROM bookings b
    JOIN analytics_mart.fact_offer_event r
        ON  r.company_id     = b.company_id
        AND r.product_family = b.product_family
        AND r.recommendation_status IN ('acted_on', 'lead_created')
        -- Window: recommendation must precede the booking by ≤ 7 days
        AND r.recommendation_ts
                BETWEEN b.order_close_ts - INTERVAL '7' DAY
                    AND b.order_close_ts
),

first_touch AS (
    SELECT * FROM candidates WHERE touch_rank = 1
)

SELECT
    b.booking_id,
    b.company_id,
    b.product_family,
    b.order_amount,
    b.units_booked,
    b.order_close_ts,

    -- Attribution columns — NULL when no qualifying recommendation in window
    ft.advisor_id                                        AS attributed_advisor_id,
    ft.recommendation_id                                 AS attributed_recommendation_id,
    ft.contact_id                                        AS attributed_contact_id,
    ft.recommendation_ts                                 AS attributed_recommendation_ts,
    DATEDIFF(b.order_close_ts, ft.recommendation_ts)     AS days_recommendation_to_close,

    CASE WHEN ft.advisor_id IS NOT NULL THEN 1 ELSE 0 END AS is_attributed,
    CURRENT_TIMESTAMP()                                  AS updated_ts,
    b.run_date

FROM bookings b
LEFT JOIN first_touch ft
    ON b.booking_id = ft.booking_id
