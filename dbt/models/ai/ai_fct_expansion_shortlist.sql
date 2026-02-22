{{ config(materialized='view') }}

select
    account_id
  , account_name
  , expansion_score
  , current_mrr_eur * 12 as current_arr_eur
  , seat_utilization_ratio as utilization
  , health_score
  , case
        when seat_utilization_ratio >= 0.85 then 'Add seats'
        when seat_utilization_ratio < 0.5 and (current_mrr_eur * 12) > 10000 then 'Adoption + expansion later'
        when health_score >= 0.7 then 'Upgrade plan / add module'
        else 'Review opportunity'
    end as recommended_angle
  , case
        when seat_utilization_ratio >= 0.85 then 'seat_headroom'
        when seat_utilization_ratio < 0.5 then 'usage_trend'
        else 'feature_adoption'
    end as supporting_signal
from {{ ref('fct_account_expansion_potential') }}
