{{ config(materialized='view') }}

select
    account_id
  , account_name
  , subscription_status
  , renewal_date
  , days_to_renewal
  , avg_active_users
  , usage_drop_ratio
  , tickets_total
  , tickets_high
  , unpaid_invoices
  , health_score
  , health_band
from {{ ref('fct_account_health_score') }}
