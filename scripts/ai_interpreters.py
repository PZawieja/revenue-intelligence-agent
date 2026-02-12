def interpret_account_overview(row: dict) -> str:
    return f"""
--- ACCOUNT OVERVIEW ---

Account: {row['account_name']}
Plan: {row['plan']}
Status: {row['subscription_status']}
Renewal Date: {row['renewal_date']}

MRR: €{row['current_mrr_eur']}
ARR: €{row['current_arr_eur']}

Seats Purchased: {row['seats_purchased']}
"""

INTERPRETERS = {
    "account_overview": interpret_account_overview
}
