with customers as (

    select *
    from {{ ref('customers') }}

)

, subscriptions as (

    select *
    from {{ ref('subscriptions') }}

)

, usage as (

    select
        account_id
      , avg(active_users) as avg_active_users
      , min(active_users) as min_active_users
      , max(active_users) as max_active_users
    from {{ ref('product_usage_daily') }}
    group by 1

)

, tickets as (

    select
        account_id
      , count(*) as tickets_total
      , sum(case when severity = 'high' then 1 else 0 end) as tickets_high
    from {{ ref('support_tickets') }}
    group by 1

)

, invoices as (

    select
        account_id
      , sum(case when paid = false then 1 else 0 end) as unpaid_invoices
    from {{ ref('invoices') }}
    group by 1

)

, joined as (

    select
        customers.account_id
      , customers.account_name

      , subscriptions.renewal_date
      , subscriptions.status as subscription_status

      , coalesce(usage.avg_active_users, 0) as avg_active_users
      , coalesce(usage.min_active_users, 0) as min_active_users
      , coalesce(usage.max_active_users, 0) as max_active_users

      , coalesce(tickets.tickets_total, 0) as tickets_total
      , coalesce(tickets.tickets_high, 0) as tickets_high

      , coalesce(invoices.unpaid_invoices, 0) as unpaid_invoices

    from customers
    left join subscriptions
        on customers.account_id = subscriptions.account_id
    left join usage
        on customers.account_id = usage.account_id
    left join tickets
        on customers.account_id = tickets.account_id
    left join invoices
        on customers.account_id = invoices.account_id

)

, scored as (

    select
        *

        -- Usage trend proxy: if min is much lower than max, assume downward trend risk
        , case
            when max_active_users = 0 then 0
            else (max_active_users - min_active_users) * 1.0 / max_active_users
          end as usage_drop_ratio

        -- Renewal urgency: simplistic, based on months until renewal
        , datediff('day', current_date, renewal_date) as days_to_renewal

    from joined

)

select
    account_id
  , account_name
  , subscription_status
  , renewal_date
  , days_to_renewal

  , avg_active_users
  , min_active_users
  , max_active_users
  , usage_drop_ratio

  , tickets_total
  , tickets_high
  , unpaid_invoices

  -- Score components (all normalized 0..1)
  , least(1.0, usage_drop_ratio) as risk_usage
  , least(1.0, tickets_high * 1.0 / 3) as risk_tickets
  , case when unpaid_invoices > 0 then 1.0 else 0.0 end as risk_payment
  , case
        when days_to_renewal is null then 0.0
        when days_to_renewal < 30 then 1.0
        when days_to_renewal < 90 then 0.5
        else 0.0
    end as risk_renewal

  -- Final health score: 1 is good, 0 is bad
  , 1.0
    - (
        0.35 * least(1.0, usage_drop_ratio)
      + 0.25 * least(1.0, tickets_high * 1.0 / 3)
      + 0.25 * case when unpaid_invoices > 0 then 1.0 else 0.0 end
      + 0.15 * case
            when days_to_renewal is null then 0.0
            when days_to_renewal < 30 then 1.0
            when days_to_renewal < 90 then 0.5
            else 0.0
        end
      ) as health_score

  , case
        when (
            1.0
            - (
                0.35 * least(1.0, usage_drop_ratio)
              + 0.25 * least(1.0, tickets_high * 1.0 / 3)
              + 0.25 * case when unpaid_invoices > 0 then 1.0 else 0.0 end
              + 0.15 * case
                    when days_to_renewal is null then 0.0
                    when days_to_renewal < 30 then 1.0
                    when days_to_renewal < 90 then 0.5
                    else 0.0
                end
            )
        ) >= 0.75 then 'green'
        when (
            1.0
            - (
                0.35 * least(1.0, usage_drop_ratio)
              + 0.25 * least(1.0, tickets_high * 1.0 / 3)
              + 0.25 * case when unpaid_invoices > 0 then 1.0 else 0.0 end
              + 0.15 * case
                    when days_to_renewal is null then 0.0
                    when days_to_renewal < 30 then 1.0
                    when days_to_renewal < 90 then 0.5
                    else 0.0
                end
            )
        ) >= 0.5 then 'yellow'
        else 'red'
    end as health_band

from scored
