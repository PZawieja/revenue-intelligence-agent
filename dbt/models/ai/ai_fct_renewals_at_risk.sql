{{ config(materialized='view') }}

select
    account_id
  , account_name
  , renewal_date
  , days_to_renewal
  , health_score
  , health_band
  , current_arr_eur
  , usage_drop_ratio
  , tickets_high
  , unpaid_invoices
  , primary_risk_driver
from {{ ref('fct_renewals_at_risk') }}
