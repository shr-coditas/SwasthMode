import json
from app.ai.client import ProviderFailure, structured
from app.ai.guardrails import check_output
from app.ai.nemo import allowed
from app.features.meals.prompts import INSIGHT
from app.features.meals.schemas import InsightOutput


async def generate_insight(foods: list[dict]) -> str:
    result = await structured(INSIGHT, json.dumps({"foods": foods}), InsightOutput)
    allowed_foods = {food["name"].casefold() for food in foods}
    if not {name.casefold() for name in result.observed_foods}.issubset(allowed_foods):
        raise ProviderFailure("Ungrounded insight")
    if not check_output(result.observation, qualitative=True):
        raise ProviderFailure("Insight exceeded its qualitative scope")
    if not await allowed(result.observation, "output"):
        raise ProviderFailure("NeMo rejected the meal insight")
    return result.observation
