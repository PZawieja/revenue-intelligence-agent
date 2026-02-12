with overview as (

    select *
    from {{ ref('dm_account_overview') }}

)

, health as (

    select *
    from {{ ref('fct_account_health_score') }}

)

, usage as (

    select
        account_id
      , avg(active_users) as avg_active_users
    from {{ ref('product_usage_daily') }}
    group by 1

)

, joined as (

    select
        overview.account_id
      , overview.account_name
      , overview.current_mrr_eur
      , overview.seats_purchased
      , health.health_score
      , coalesce(usage.avg_active_users, 0) as avg_active_users

    from overview
    left join health
        on overview.account_id = health.account_id
    left join usage
        on overview.account_id = usage.account_id

)

select
    account_id
  , account_name
  , current_mrr_eur
  , seats_purchased
  , avg_active_users
  , health_score

  -- utilization ratio proxy
  , case
        when seats_purchased = 0 then 0
        else avg_active_users * 1.0 / seats_purchased
    end as seat_utilization_ratio

  -- expansion score 0..1
  , least(
        1.0,
        0.5 * health_score
      + 0.5 * case
            when seats_purchased = 0 then 0
            else avg_active_users * 1.0 / seats_purchased
        end
    ) as expansion_score

  , case
        when (
            0.5 * health_score
          + 0.5 * case
                when seats_purchased = 0 then 0
                else avg_active_users * 1.0 / seats_purchased
            end
        ) >= 0.75 then 'high'
        when (
            0.5 * health_score
          + 0.5 * case
                when seats_purchased = 0 then 0
                else avg_active_users * 1.0 / seats_purchased
            end
        ) >= 0.5 then 'medium'
        else 'low'
    end as expansion_band

from joined
