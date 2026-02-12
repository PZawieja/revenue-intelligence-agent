{{ config(materialized='table') }}

select
    'model' as asset_type
  , 'ai_dm_account_overview' as asset_name
  , 'account_id' as grain
  , 'account_id' as primary_keys
  , true as is_allowed_for_ai
  , 'Account overview for AEs: ARR/MRR, plan, subscription status, renewal date, seats.' as description
