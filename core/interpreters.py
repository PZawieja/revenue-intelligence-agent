def _eur(val) -> str:
    v = int(val or 0)
    if v >= 1_000_000:
        return f"€{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"€{v/1_000:.0f}k"
    return f"€{v}"


def interpret_account_overview(row: dict, _rows: list[dict] = None) -> dict:
    bullets = [
        f"{row['account_name']} is on the {row['plan']} plan — status: {row['subscription_status']}.",
        f"Renewal date: {row['renewal_date']}.",
        f"Revenue: {_eur(row['current_mrr_eur'])} MRR ({_eur(row['current_arr_eur'])} ARR).",
        f"Seats purchased: {row['seats_purchased']}.",
    ]
    return {
        "title": "Account overview",
        "narrative": "Confirm renewal timing, current value, and plan context before any customer conversation.",
        "bullets": bullets,
        "next_action": "",
    }


def interpret_health_summary(row: dict, _rows: list[dict] = None) -> dict:
    reasons = []
    if row.get("usage_drop_ratio", 0) >= 0.3:
        reasons.append("usage is declining")
    if row.get("tickets_high", 0) >= 1:
        reasons.append("high-severity tickets are open")
    if row.get("unpaid_invoices", 0) >= 1:
        reasons.append("unpaid invoices exist")
    dtr = row.get("days_to_renewal")
    if dtr is not None and dtr < 90:
        reasons.append(f"renewal is {dtr} days away")

    reason_text = ", ".join(reasons) if reasons else "no major risk signals detected"
    band = row.get("health_band", "unknown")
    score = row.get("health_score", 0)

    if band == "red":
        narrative = (
            f"{row['account_name']} is at high churn risk (score {score:.2f}). "
            f"Signals: {reason_text}. Immediate intervention recommended."
        )
        next_action = "Schedule a retention call before the renewal date."
    elif band == "yellow":
        narrative = (
            f"{row['account_name']} shows moderate risk (score {score:.2f}). "
            f"Signals: {reason_text}. Proactive outreach advised."
        )
        next_action = "Reach out to confirm value delivery and address open issues."
    else:
        narrative = (
            f"{row['account_name']} is healthy (score {score:.2f}). "
            "No major risk signals detected. Good expansion candidate."
        )
        next_action = "Consider scheduling an expansion conversation."

    bullets = [
        f"Health score: {score:.2f} — {band.capitalize()}.",
        f"Days to renewal: {dtr}.",
        f"Primary signal: {reason_text}.",
    ]
    return {"title": "Health summary", "narrative": narrative, "bullets": bullets, "next_action": next_action}


def interpret_expansion_potential(row: dict, _rows: list[dict] = None) -> dict:
    band = row.get("expansion_band", "low")
    score = row.get("expansion_score", 0)
    utilization = row.get("seat_utilization_ratio", 0)

    if band == "high":
        recommendation = "Strong upsell candidate — initiate expansion conversation now."
        next_action = f"Book an upgrade call. Utilization at {utilization:.0%} signals seat headroom pressure."
    elif band == "medium":
        recommendation = "Moderate opportunity — worth a feature adoption check-in first."
        next_action = "Schedule a QBR to review adoption and gauge appetite for expansion."
    else:
        recommendation = "Focus on retention and adoption before pitching expansion."
        next_action = "Address health issues first; revisit expansion in 60–90 days."

    bullets = [
        f"Expansion score: {score:.2f} ({band.capitalize()}).",
        f"Seat utilization: {utilization:.0%}.",
        f"Recommendation: {recommendation}.",
    ]
    return {
        "title": "Expansion potential",
        "narrative": f"{row['account_name']} expansion score is {score:.2f}. {recommendation}",
        "bullets": bullets,
        "next_action": next_action,
    }


def interpret_renewals_at_risk(row: dict, rows: list[dict]) -> dict:
    if not rows:
        return {
            "title": "Renewals at risk",
            "narrative": "No accounts match the renewal + health criteria.",
            "bullets": [],
            "next_action": "",
        }
    total_arr = sum(r.get("current_arr_eur") or 0 for r in rows)
    urgent = [r for r in rows if (r.get("days_to_renewal") or 999) <= 30]
    bullets = [
        f"{len(rows)} accounts renewing soon with elevated churn risk.",
        f"Combined ARR at stake: {_eur(total_arr)}.",
    ]
    if urgent:
        bullets.append(f"{len(urgent)} account(s) renewing within 30 days — act now.")
    closest = min(rows, key=lambda r: r.get("days_to_renewal") or 999)
    closest_days = closest.get("days_to_renewal", "?")
    closest_arr = _eur(closest.get("current_arr_eur"))
    return {
        "title": f"Renewals at risk — {len(rows)} accounts",
        "narrative": (
            f"{len(rows)} accounts have upcoming renewals and health risk. "
            f"Total ARR exposure: {_eur(total_arr)}. "
            f"Prioritize by renewal date."
        ),
        "bullets": bullets,
        "next_action": f"Start with {closest['account_name']} — {closest_days}d to renewal, {closest_arr} at stake. Book a call today.",
    }


def interpret_expansion_shortlist(row: dict, rows: list[dict]) -> dict:
    if not rows:
        return {
            "title": "Expansion shortlist",
            "narrative": "No high-fit expansion candidates found.",
            "bullets": [],
            "next_action": "",
        }
    top = rows[0]
    total_arr = sum(r.get("current_arr_eur") or 0 for r in rows)
    bullets = [
        f"{len(rows)} accounts qualify as expansion candidates.",
        f"Top: {top['account_name']} (score {top['expansion_score']:.2f}) — {top.get('recommended_angle', '')}.",
        f"Combined ARR of shortlist: {_eur(total_arr)}.",
    ]
    return {
        "title": f"Expansion shortlist — {len(rows)} candidates",
        "narrative": (
            f"{len(rows)} accounts show expansion potential. "
            f"Top candidate: {top['account_name']} (score {top['expansion_score']:.2f})."
        ),
        "bullets": bullets,
        "next_action": f"Start with {top['account_name']}: {top.get('recommended_angle', 'Upgrade plan')}.",
    }


def interpret_arr_exposure_overview(row: dict, rows: list[dict]) -> dict:
    if not rows:
        return {
            "title": "ARR exposure",
            "narrative": "No data available.",
            "bullets": [],
            "next_action": "",
        }
    total = sum(r.get("arr_eur") or 0 for r in rows)
    red_band = next((r for r in rows if r.get("health_band") == "red"), None)
    red_pct = round((red_band["arr_eur"] or 0) / total * 100, 1) if red_band and total else 0
    bullets = [f"Total portfolio ARR: {_eur(total)}."]
    for r in rows:
        bullets.append(f"  {r['health_band'].capitalize()}: {_eur(r['arr_eur'])} ({r['accounts_count']} accounts).")
    return {
        "title": "ARR exposure by health band",
        "narrative": (
            f"Portfolio ARR is {_eur(total)}. "
            f"{red_pct}% sits in red accounts."
        ),
        "bullets": bullets,
        "next_action": "Focus retention on red accounts to reduce ARR at risk." if red_pct > 0 else "",
    }


INTERPRETERS: dict[str, callable] = {
    "account_overview": interpret_account_overview,
    "health_summary": interpret_health_summary,
    "expansion_potential": interpret_expansion_potential,
    "renewals_at_risk": interpret_renewals_at_risk,
    "expansion_shortlist": interpret_expansion_shortlist,
    "arr_exposure_overview": interpret_arr_exposure_overview,
}


def interpret(intent: str, row: dict, rows: list[dict]) -> dict:
    fn = INTERPRETERS.get(intent)
    if not fn:
        return {"title": intent, "narrative": "", "bullets": [], "next_action": ""}
    return fn(row, rows)
