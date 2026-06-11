{{ config(materialized='table') }}

select
    'model' as asset_type,
    'ai_dm_account_overview' as asset_name,
    'account_id' as grain,
    'account_id' as primary_keys,
    true as is_allowed_for_ai,
    'Account overview for AEs: ARR/MRR, plan, subscription status, renewal date, seats.'
        as description

union all
select
    'model',
    'ai_fct_account_health_score',
    'account_id',
    'account_id',
    true,
    'Account health score with risk drivers (usage, tickets, unpaid invoices, renewal proximity).'

union all
select
    'model',
    'ai_fct_account_expansion_potential',
    'account_id',
    'account_id',
    true,
    'Account expansion potential based on health score and seat utilization.'

union all
select
    'model',
    'ai_fct_renewals_at_risk',
    'account_id',
    'account_id',
    true,
    'Renewals at risk: accounts with renewal date and health in horizon; for portfolio view.'

union all
select
    'model',
    'ai_fct_expansion_shortlist',
    'account_id',
    'account_id',
    true,
    'Expansion shortlist: accounts with expansion score, utilization, recommended angle; for portfolio view.'

union all
select
    'model',
    'ai_arr_exposure',
    'account_id',
    'account_id',
    true,
    'ARR exposure by health band: account-level health_band, current_arr_eur, primary_risk_driver; for CEO overview.'

union all
select
    'model',
    'ai_fct_account_usage_trend',
    'account_id',
    'account_id,date_day',
    true,
    'Daily active users and key events per account; powers usage sparklines and trend analysis.'
