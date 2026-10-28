from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.ai.guardrails import check_output
from app.features.briefs.schemas import BriefContext, Narrative

OPENINGS = {
    "overview": "Here is an overview of your recorded information.",
    "check_in": "Here is a check-in based on your records.",
    "reflection": "Here is a moment to reflect on your recorded information.",
}
FOCUSES = {
    "log_meal": "If useful, record one meal with the foods you remember.",
    "record_activity": "If useful, record activity you have already done.",
    "reflect": "If useful, note one thing you noticed in your records.",
}


def render(context: BriefContext, narrative: Narrative) -> tuple[str, str]:
    facts = {fact.id: fact.text for fact in context.facts}
    if len(set(narrative.fact_ids)) != len(narrative.fact_ids) or any(
            fact_id not in facts for fact_id in narrative.fact_ids):
        raise HTTPException(422, "The generated brief was not grounded. No brief was saved")
    text = " ".join([OPENINGS[narrative.opening], *[facts[fact_id] for fact_id in narrative.fact_ids]])
    focus = FOCUSES[narrative.focus]
    if not check_output(text + " " + focus):
        raise HTTPException(422, "The generated brief did not pass output rules. No brief was saved")
    return text, focus


def reuse_until(kind: str, local_day, timezone: str, created_at: datetime) -> datetime:
    midnight = datetime.combine(local_day + timedelta(days=1), time.min, ZoneInfo(timezone)).astimezone(UTC)
    return midnight if kind == "morning" else min(midnight, created_at + timedelta(minutes=30))
