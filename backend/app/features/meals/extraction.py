import json
from app.ai.client import structured
from app.features.meals.prompts import EXTRACTION
from app.features.meals.schemas import MealExtraction


async def extract(context: dict) -> MealExtraction:
    return await structured(EXTRACTION, json.dumps(context, ensure_ascii=False), MealExtraction)
