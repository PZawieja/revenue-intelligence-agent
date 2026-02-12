{{ config(materialized='table') }}

select
    'model' as asset_type
  , 'ai_dm_account_overview' as asset_name
  , 'account_id' as grain
  , 'account_id' as primary_keys
  , true as is_allowed_for_ai
  , 'Account overview for AEs: ARR/MRR, plan, subscription status, renewal date, seats.' as description

union all
select
    'model'
  , 'ai_fct_account_health_score'
  , 'account_id'
  , 'account_id'
  , true
  , 'Account health score with risk drivers (usage, tickets, unpaid invoices, renewal proximity).'

union all
select
    'model'
  , 'ai_fct_account_expansion_potential'
  , 'account_id'
  , 'account_id'
  , true
  , 'Account expansion potential based on health score and seat utilization.'
