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

SQL_TEMPLATES["health_summary"] = """
    select
        account_id
      , account_name
      , health_score
      , health_band
      , days_to_renewal
      , usage_drop_ratio
      , tickets_high
      , unpaid_invoices
    from ai_fct_account_health_score
    where lower(account_name) = lower('{account_name}')
"""

SQL_TEMPLATES["expansion_potential"] = """
    select
        account_id
      , account_name
      , health_score
      , seat_utilization_ratio
      , expansion_score
      , expansion_band
    from ai_fct_account_expansion_potential
    where lower(account_name) = lower('{account_name}')
"""
