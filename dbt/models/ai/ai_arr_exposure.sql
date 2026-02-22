{{ config(materialized='view') }}

with health as (
    select
        account_id
      , account_name
      , health_score
      , usage_drop_ratio
      , tickets_high
      , unpaid_invoices
      , days_to_renewal
    from {{ ref('fct_account_health_score') }}
),
overview as (
    select account_id, current_arr_eur
    from {{ ref('dm_account_overview') }}
)
select
    health.account_id
  , health.account_name
  , health.health_score
  , case
        when health.health_score >= 0.8 then 'green'
        when health.health_score >= 0.6 then 'yellow'
        else 'red'
    end as health_band
  , overview.current_arr_eur
  , case
        when health.usage_drop_ratio >= 0.20 then 'Usage decline'
        when health.tickets_high >= 1 then 'Support tickets'
        when health.unpaid_invoices >= 1 then 'Unpaid invoices'
        when health.days_to_renewal is not null and health.days_to_renewal < 60 then 'Renewal soon'
        else 'Other'
    end as primary_risk_driver
from health
left join overview on health.account_id = overview.account_id
where overview.current_arr_eur is not null
