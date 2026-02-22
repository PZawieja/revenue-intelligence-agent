with health as (
    select *
    from {{ ref('fct_account_health_score') }}
),
overview as (
    select account_id, account_name, current_mrr_eur, current_arr_eur
    from {{ ref('dm_account_overview') }}
)
select
    health.account_id
  , health.account_name
  , health.renewal_date
  , health.days_to_renewal
  , health.health_score
  , health.health_band
  , overview.current_arr_eur
  , health.usage_drop_ratio
  , health.tickets_high
  , health.unpaid_invoices
  , case
        when health.usage_drop_ratio >= 0.20 then 'Usage decline'
        when health.tickets_high >= 1 then 'Support tickets'
        when health.unpaid_invoices >= 1 then 'Unpaid invoices'
        when health.days_to_renewal is not null and health.days_to_renewal < 60 then 'Renewal soon'
        else 'Other'
    end as primary_risk_driver
from health
left join overview on health.account_id = overview.account_id
