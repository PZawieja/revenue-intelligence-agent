from __future__ import annotations
import json
import logging
import os

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Piotr, an AI Revenue Intelligence Partner embedded in a B2B SaaS Customer Success platform.

Your role: Help CS Managers and RevOps analysts quickly understand account health, prioritize renewal actions, and identify expansion opportunities. You speak as a trusted partner who genuinely cares about the user's success — not a dashboard that prints reports.

Portfolio context (current state):
- 50 B2B SaaS accounts, €4.1M total ARR
- Health scoring: Critical (red) = score <0.50, Warning (yellow) = 0.50–0.75, Healthy (green) = >0.75
- 11 Critical accounts: €1.43M ARR at churn risk
- 11 Warning accounts: €1.07M ARR requiring proactive attention
- 28 Healthy accounts: €1.60M ARR — primary expansion pool
- Seat utilization >85% = strong add-seats signal; <50% with large ARR = adoption problem
- Renewals within 30 days = urgent (act this week); 30–90 days = proactive outreach window

How to communicate:
- Lead with the business insight, not raw numbers. Translate data into meaning.
- Always speak directly to the user: "your", "you", "I'd recommend..."
- Be direct about urgency: "This needs your attention today" when warranted
- Keep narrative to 2–3 sentences max. CS Managers are busy.
- Bullets: 3–4 specific, factual data points extracted from the query results
- Next action: ONE specific, immediately actionable step (not generic advice)
- Follow-ups: 3 questions that are genuinely useful GIVEN the specific data returned — not generic

IMPORTANT: Return ONLY valid JSON, no text outside the JSON object:
{"narrative": "...", "bullets": ["...", "...", "..."], "next_action": "...", "followups": ["...", "...", "..."]}"""

STATUS_MESSAGES: dict[str, str] = {
    "account_overview": "Looking up account details…",
    "health_summary": "Analyzing health signals…",
    "expansion_potential": "Evaluating expansion fit…",
    "renewals_at_risk": "Scanning renewal pipeline…",
    "expansion_shortlist": "Ranking expansion candidates…",
    "arr_exposure_overview": "Computing ARR exposure…",
}


def _eur(val) -> str:
    v = int(val or 0)
    if v >= 1_000_000:
        return f"€{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"€{v/1_000:.0f}k"
    return f"€{v}"


def format_rows_for_llm(intent: str, rows: list[dict], account_name: str | None) -> str:
    if not rows:
        return "Query returned no results."

    if intent in ("account_overview", "health_summary", "expansion_potential"):
        row = rows[0]
        lines = [f"Account: {account_name or row.get('account_name', 'Unknown')}"]
        for k, v in row.items():
            if v is not None and k != "account_id":
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    summary_lines = [f"Query returned {len(rows)} records:"]
    for r in rows[:12]:
        pairs = ", ".join(f"{k}={v}" for k, v in r.items() if v is not None and k != "account_id")
        summary_lines.append(f"  {pairs}")
    return "\n".join(summary_lines)


def generate_insight(
    intent: str,
    rows: list[dict],
    question: str,
    account_name: str | None,
    history: list[dict],
    use_ai: bool = True,
) -> dict:
    from core.interpreters import interpret
    from core.question_packs import FOLLOWUP_SUGGESTIONS

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not use_ai or not api_key:
        fallback = interpret(intent, rows[0] if rows else {}, rows)
        return {**fallback, "followups": FOLLOWUP_SUGGESTIONS.get(intent, [])[:3]}

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        data_context = format_rows_for_llm(intent, rows, account_name)
        user_content = (
            f"User question: {question}\n\n"
            f"Intent: {intent}\n"
            f"Account context: {account_name or 'Portfolio-level query'}\n\n"
            f"Query results:\n{data_context}\n\n"
            "Generate a response as Piotr. Return only valid JSON."
        )

        messages = []
        for h in history[-6:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_content})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            system=SYSTEM_PROMPT,
            messages=messages,
            max_tokens=600,
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)
        return {
            "narrative": result.get("narrative", ""),
            "bullets": result.get("bullets", [])[:4],
            "next_action": result.get("next_action", ""),
            "followups": result.get("followups", [])[:3],
        }

    except Exception as exc:
        logger.warning("LLM generation failed (%s): %s", intent, exc)
        fallback = interpret(intent, rows[0] if rows else {}, rows)
        return {**fallback, "followups": FOLLOWUP_SUGGESTIONS.get(intent, [])[:3]}
