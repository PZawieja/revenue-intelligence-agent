with customers as (

    select *
    from {{ ref('customers') }}

)

, subscriptions as (

    select *
    from {{ ref('subscriptions') }}

)

select
    customers.account_id
  , customers.account_name
  , customers.segment
  , customers.country
  , customers.owner_ae

  , subscriptions.plan
  , subscriptions.status as subscription_status
  , subscriptions.start_date
  , subscriptions.renewal_date

  , subscriptions.mrr_eur as current_mrr_eur
  , subscriptions.mrr_eur * 12 as current_arr_eur

  , subscriptions.seats_purchased

from customers
left join subscriptions
    on customers.account_id = subscriptions.account_id
