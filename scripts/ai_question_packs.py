PERSONA_QUESTION_PACKS = {
    "Customer Success": [
        "Give me an account overview",
        "Is this account healthy?",
        "Why is this account at risk?",
        "What is the expansion potential?",
        "What is the health score for this account?",
        "Summarize the account status",
    ],
    "RevOps": [
        "Give me an account overview",
        "Is this account healthy?",
        "What is the expansion potential?",
        "What is the health score for this account?",
        "Summarize the account status",
        "What are the renewal risks?",
    ],
    "Finance": [
        "Give me an account overview",
        "What is the health score for this account?",
        "Is this account healthy?",
        "What is the expansion potential?",
        "Summarize the account status",
        "What are the renewal risks?",
    ],
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
