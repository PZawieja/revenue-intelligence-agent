SQL_TEMPLATES = {
    "account_overview": """
        select
            account_id
          , account_name
          , plan
          , subscription_status
          , renewal_date
          , current_mrr_eur
          , current_arr_eur
          , seats_purchased
        from ai_dm_account_overview
        where lower(account_name) = lower('{account_name}')
    """
}
