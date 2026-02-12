{{ config(materialized='view') }}

select
    account_id
  , account_name
  , current_mrr_eur
  , seats_purchased
  , avg_active_users
  , health_score
  , seat_utilization_ratio
  , expansion_score
  , expansion_band
from {{ ref('fct_account_expansion_potential') }}
