from __future__ import annotations
import json
import logging
import os
from typing import Any

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


# ─── Briefing ──────────────────────────────────────────────────────────────

BRIEFING_SYSTEM = """You are Piotr, an AI Revenue Intelligence Partner. Generate a proactive daily briefing for a CS Manager.
Analyse the provided portfolio data and return exactly 3 actionable insights as JSON.

Each insight must be immediately actionable and reference specific account names or numbers from the data.
Categories: "critical" (churn risk / red accounts), "warning" (usage drops / renewal urgency), "opportunity" (expansion / healthy growth).

Return ONLY valid JSON — no text outside:
{"insights":[{"category":"critical"|"warning"|"opportunity","title":"short title max 8 words","body":"1-2 sentence insight with specific names and numbers","action_label":"short CTA 3-5 words","action_query":"exact question for the intelligence agent"}]}"""


ACTION_SYSTEM = """You are Piotr, an AI Revenue Intelligence Partner. Generate a professional, copy-pasteable business asset.
Be specific and concise. Reference the actual account name and situation provided.

For email: write a professional follow-up (Subject + Body, 3 paragraphs max).
For slack: one paragraph, professional but conversational.
For crm_note: structured bullet points, factual, no filler.

Return ONLY valid JSON. For email: {"subject":"...","body":"..."}. For slack and crm_note: {"body":"..."}."""


def _eur_str(val: Any) -> str:
    v = int(val or 0)
    if v >= 1_000_000:
        return f"€{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"€{v / 1_000:.0f}k"
    return f"€{v}"


def _parse_llm_json(raw: str) -> dict:
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


def _briefing_fallback(
    arr_data: list[dict],
    urgent_renewals: list[dict],
    top_expansion: list[dict],
    anomalies: list[dict],
) -> dict:
    band_map = {r["health_band"]: r for r in arr_data}
    red = band_map.get("red", {})
    insights: list[dict] = []

    if urgent_renewals:
        names = ", ".join(r["account_name"].split()[0] for r in urgent_renewals[:2])
        insights.append({
            "category": "critical",
            "title": f"{len(urgent_renewals)} renewal{'s' if len(urgent_renewals) > 1 else ''} expiring within 14 days",
            "body": f"{names} {'and others are' if len(urgent_renewals) > 1 else 'is'} renewing imminently — contact now to secure the contract.",
            "action_label": "Show renewals →",
            "action_query": "Show renewals at risk in the next 14 days",
        })
    elif red:
        insights.append({
            "category": "critical",
            "title": f"{red.get('cnt', 0)} accounts in Critical health",
            "body": f"{_eur_str(red.get('arr_eur', 0))} ARR at churn risk. Prioritise outreach to these accounts today.",
            "action_label": "View ARR exposure →",
            "action_query": "Show ARR exposure by health band",
        })

    if anomalies:
        top = anomalies[0]
        drop_pct = int((top.get("drop_ratio") or 0) * 100)
        insights.append({
            "category": "warning",
            "title": f"Usage anomaly: {top['account_name'].split()[0]} dropped {drop_pct}%",
            "body": (
                f"{top['account_name']} active users fell {drop_pct}% from early-period baseline — "
                f"{_eur_str(top['current_arr_eur'])} ARR. Investigate before next renewal."
            ),
            "action_label": "Check health →",
            "action_query": f"Is {top['account_name']} healthy?",
        })
    else:
        band_map_y = band_map.get("yellow", {})
        insights.append({
            "category": "warning",
            "title": f"{band_map_y.get('cnt', 0)} accounts in Warning band",
            "body": f"{_eur_str(band_map_y.get('arr_eur', 0))} ARR showing moderate risk. Proactive outreach now prevents churn.",
            "action_label": "ARR breakdown →",
            "action_query": "Show ARR exposure by health band",
        })

    if top_expansion:
        top = top_expansion[0]
        insights.append({
            "category": "opportunity",
            "title": f"Expansion opening: {top['account_name'].split()[0]}",
            "body": (
                f"{top['account_name']} scores {(top['expansion_score'] or 0):.2f} for expansion — "
                f"{top.get('recommended_angle', 'high seat utilisation')}."
            ),
            "action_label": "Expansion shortlist →",
            "action_query": "Show expansion shortlist",
        })
    else:
        insights.append({
            "category": "opportunity",
            "title": "Identify expansion candidates",
            "body": "Healthy accounts with high seat utilisation are primed for an upgrade conversation.",
            "action_label": "Expansion shortlist →",
            "action_query": "Show expansion shortlist",
        })

    return {"insights": insights[:3], "ai_generated": False}


def generate_briefing(
    arr_data: list[dict],
    urgent_renewals: list[dict],
    top_expansion: list[dict],
    anomalies: list[dict],
) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _briefing_fallback(arr_data, urgent_renewals, top_expansion, anomalies)

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        band_map = {r["health_band"]: r for r in arr_data}
        red = band_map.get("red", {})
        yellow = band_map.get("yellow", {})
        green = band_map.get("green", {})
        total_arr = sum(r.get("arr_eur") or 0 for r in arr_data)

        parts = [
            f"Portfolio: {sum(r['cnt'] for r in arr_data)} accounts, {_eur_str(total_arr)} total ARR",
            f"Critical (red): {red.get('cnt', 0)} accounts, {_eur_str(red.get('arr_eur', 0))} ARR",
            f"Warning (yellow): {yellow.get('cnt', 0)} accounts, {_eur_str(yellow.get('arr_eur', 0))} ARR",
            f"Healthy (green): {green.get('cnt', 0)} accounts, {_eur_str(green.get('arr_eur', 0))} ARR",
        ]
        if urgent_renewals:
            lines = [f"  - {r['account_name']}: {r['days_to_renewal']}d, {_eur_str(r['current_arr_eur'])}" for r in urgent_renewals]
            parts.append("Urgent renewals (<=14 days):\n" + "\n".join(lines))
        if top_expansion:
            lines = [f"  - {r['account_name']}: score {(r['expansion_score'] or 0):.2f}, {r.get('recommended_angle', '')}" for r in top_expansion]
            parts.append("Top expansion candidates:\n" + "\n".join(lines))
        if anomalies:
            lines = [f"  - {r['account_name']}: {int((r['drop_ratio'] or 0)*100)}% usage drop, {_eur_str(r['current_arr_eur'])}" for r in anomalies]
            parts.append("Usage anomalies detected:\n" + "\n".join(lines))

        response = client.messages.create(
            model="claude-sonnet-4-6",
            system=BRIEFING_SYSTEM,
            messages=[{"role": "user", "content": "Portfolio data:\n" + "\n".join(parts) + "\n\nGenerate 3 actionable briefing insights."}],
            max_tokens=800,
        )
        result = _parse_llm_json(response.content[0].text.strip())
        return {"insights": result.get("insights", [])[:3], "ai_generated": True}

    except Exception as exc:
        logger.warning("Briefing generation failed: %s", exc)
        return _briefing_fallback(arr_data, urgent_renewals, top_expansion, anomalies)


# ─── Action Assets ─────────────────────────────────────────────────────────

def generate_action_asset(
    action_type: str,
    intent: str,
    account_name: str | None,
    narrative: str,
    bullets: list[str],
    next_action: str,
) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": True, "message": "Set ANTHROPIC_API_KEY to generate action assets."}

    type_labels = {
        "email": "a professional follow-up email",
        "slack": "a Slack message for the team",
        "crm_note": "a CRM activity note",
    }
    format_hints = {
        "email": '{"subject":"...","body":"..."}',
        "slack": '{"body":"..."}',
        "crm_note": '{"body":"..."}',
    }

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        context = (
            f"Account: {account_name or 'Portfolio'}\n"
            f"Situation: {narrative}\n"
            f"Key data points: {'; '.join(bullets)}\n"
            f"Recommended action: {next_action}"
        )
        type_label = type_labels.get(action_type, "a business document")
        fmt = format_hints.get(action_type, '{"body":"..."}')

        response = client.messages.create(
            model="claude-sonnet-4-6",
            system=ACTION_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Generate {type_label} for this CS context:\n{context}\n\nReturn JSON: {fmt}",
            }],
            max_tokens=600,
        )
        result = _parse_llm_json(response.content[0].text.strip())
        return {"type": action_type, "content": result, "error": False}

    except Exception as exc:
        logger.warning("Action asset generation failed (%s): %s", action_type, exc)
        return {"error": True, "message": f"Could not generate asset: {exc}"}
