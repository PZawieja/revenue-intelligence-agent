# Single source of quick questions: same templates for every persona and after New Chat.
# Order: account-level first, then portfolio (renewals, expansion, ARR exposure).
QUICK_QUESTIONS_ALL = [
    "Give me an account overview",
    "Is this account healthy?",
    "What is the health score for this account?",
    "What is the expansion potential?",
    "Why is this account at risk?",
    "Summarize the account status",
    "What are the renewal risks?",
    "Show renewals at risk in the next 90 days",
    "Show expansion shortlist",
    "ARR exposure by health band",
]

# For UX: group by intent so users can scan "one account" vs "portfolio".
QUICK_QUESTIONS_GROUPED = {
    "One account": [
        "Give me an account overview",
        "Is this account healthy?",
        "What is the health score for this account?",
        "What is the expansion potential?",
        "Why is this account at risk?",
        "Summarize the account status",
        "What are the renewal risks?",
    ],
    "Portfolio": [
        "Show renewals at risk in the next 90 days",
        "Show expansion shortlist",
        "ARR exposure by health band",
    ],
}

PERSONA_QUESTION_PACKS = {
    "Customer Success": list(QUICK_QUESTIONS_ALL),
    "RevOps": list(QUICK_QUESTIONS_ALL),
    "Finance": list(QUICK_QUESTIONS_ALL),
}

PERSONA_DESCRIPTIONS = {
    "Customer Success": (
        "Focus on customer health, renewals, and risk drivers. Use these questions to "
        "prioritize outreach and prevent churn."
    ),
    "RevOps": (
        "Focus on performance and pipeline efficiency. Use these questions to spot "
        "expansion opportunities and healthy accounts."
    ),
    "Finance": (
        "Focus on revenue predictability and risk. Use these questions to assess "
        "renewal proximity, health, and expansion potential."
    ),
}

FOLLOWUP_SUGGESTIONS = {
    "account_overview": [
        "Is this account healthy?",
        "What is the health score for this account?",
        "What is the expansion potential?",
        "Why is this account at risk?",
        "What are the renewal risks?",
        "Summarize the account status",
    ],
    "health_summary": [
        "Why is this account at risk?",
        "What is the expansion potential?",
        "Give me an account overview",
        "What are the renewal risks?",
        "Summarize the account status",
        "What is the health score for this account?",
    ],
    "expansion_potential": [
        "Give me an account overview",
        "Is this account healthy?",
        "What is the health score for this account?",
        "Why is this account at risk?",
        "Summarize the account status",
        "What are the renewal risks?",
    ],
}
