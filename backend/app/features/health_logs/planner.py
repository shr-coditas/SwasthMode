import json
import re

from fastapi import HTTPException
from app.ai.client import structured
from app.ai.guardrails import check_input, check_output
from app.ai.nemo import allowed
from app.features.health_logs.prompts import PLANNING
from app.features.health_logs.schemas import Plan


def validate(plan: Plan, text: str):
    if (plan.disposition == "logging") != bool(plan.steps):
        raise HTTPException(422, "The planner did not return a usable bounded plan. Nothing was started")
    end = 0
    for step in plan.steps:
        if step.start < end or text[step.start:step.end] != step.text or step.end <= step.start:
            raise HTTPException(422, "The plan changed or overlapped your words. Send separate complete reports")
        gap = text[end:step.start]
        if re.sub(r"\b(and|then|also)\b|[\s,;.!&]", "", gap, flags=re.I):
            raise HTTPException(422, "The plan omitted part of your message. Send separate complete reports")
        if check_input(step.text, feature="health_logs") or not check_output(step.text):
            raise HTTPException(422, "Safety rules blocked a planned report")
        end = step.end
    if plan.steps and re.sub(r"[\s,;.!]", "", text[end:]):
        raise HTTPException(422, "The plan omitted the end of your message. Send separate complete reports")


async def plan(text: str) -> Plan:
    if not await allowed(json.dumps({"feature": "health_logs", "text": text}), "input"):
        raise HTTPException(422, "Safety checking blocked this message. No plan was started")
    result = await structured(PLANNING, json.dumps({"text": text}), Plan)
    validate(result, text)
    if not check_output(result.model_dump_json()) or not await allowed(result.model_dump_json(), "output"):
        raise HTTPException(422, "Safety checking blocked the proposed plan. No plan was started")
    return result
