{{ config(materialized='table') }}

SELECT
    account_id,
    date_day,
    active_users,
    key_events
FROM {{ ref('product_usage_daily') }}
ORDER BY account_id, date_day
