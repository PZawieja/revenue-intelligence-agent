{{ config(materialized='view') }}

select
    account_id
  , account_name
  , segment
  , country
  , owner_ae
  , plan
  , subscription_status
  , start_date
  , renewal_date
  , current_mrr_eur
  , current_arr_eur
  , seats_purchased
from {{ ref('dm_account_overview') }}
