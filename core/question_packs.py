FOLLOWUP_SUGGESTIONS: dict[str, list[str]] = {
    "account_overview": [
        "Is this account healthy?",
        "What is the expansion potential?",
        "What are the renewal risks?",
    ],
    "health_summary": [
        "What is the expansion potential?",
        "Give me an account overview",
        "Show renewals at risk in the next 90 days",
    ],
    "expansion_potential": [
        "Is this account healthy?",
        "Give me an account overview",
        "Show expansion shortlist",
    ],
    "renewals_at_risk": [
        "ARR exposure by health band",
        "Show expansion shortlist",
        "Is this account healthy?",
    ],
    "expansion_shortlist": [
        "ARR exposure by health band",
        "Show renewals at risk in the next 90 days",
        "What is the expansion potential?",
    ],
    "arr_exposure_overview": [
        "Show renewals at risk in the next 90 days",
        "Show expansion shortlist",
        "Is this account healthy?",
    ],
}

QUICK_QUESTIONS_GROUPED: dict[str, list[str]] = {
    "One account": [
        "Give me an account overview",
        "Is this account healthy?",
        "What is the expansion potential?",
    ],
    "Portfolio": [
        "Show renewals at risk in the next 90 days",
        "Show expansion shortlist",
        "ARR exposure by health band",
    ],
}
