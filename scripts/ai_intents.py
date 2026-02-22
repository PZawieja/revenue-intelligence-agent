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

SQL_TEMPLATES["renewals_at_risk"] = """
    select
        account_id
      , account_name
      , renewal_date
      , days_to_renewal
      , health_score
      , health_band
      , current_arr_eur
      , usage_drop_ratio
      , tickets_high
      , unpaid_invoices
      , primary_risk_driver
    from ai_fct_renewals_at_risk
    where days_to_renewal between 0 and {horizon_days}
      and health_score < {health_threshold}
    order by health_score asc, current_arr_eur desc nulls last
    limit {limit_n}
"""

SQL_TEMPLATES["expansion_shortlist"] = """
    select
        account_id
      , account_name
      , expansion_score
      , current_arr_eur
      , utilization
      , health_score
      , recommended_angle
      , supporting_signal
    from ai_fct_expansion_shortlist
    where health_score >= {minimum_health}
    order by expansion_score desc nulls last, current_arr_eur desc nulls last
    limit {top_n}
"""

# ARR exposure overview: two queries (both use ai_arr_exposure)
SQL_TEMPLATES["arr_exposure_overview_bands"] = """
    select
        health_band
      , sum(current_arr_eur) as arr_eur
      , count(*) as accounts_count
    from ai_arr_exposure
    group by health_band
    order by case health_band when 'green' then 1 when 'yellow' then 2 when 'red' then 3 else 4 end
"""

SQL_TEMPLATES["arr_exposure_overview_top"] = """
    select
        account_id
      , account_name
      , health_score
      , current_arr_eur
      , primary_risk_driver
    from ai_arr_exposure
    where health_score < {risk_threshold}
    order by current_arr_eur desc nulls last
    limit 10
"""
