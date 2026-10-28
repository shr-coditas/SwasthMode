from datetime import date
from app.ai.client import ProviderFailure
from app.features.meals.schemas import MealExtraction, MealView


def validate_meal(value: MealExtraction, source: str, today: date, meals: list[MealView]) -> str | None:
    if value.local_day and value.local_day != today:
        return "This first version records meals for today only. Which meal did you have today?"
    if value.intent in {"greeting", "out_of_scope"}:
        return None
    # Evidence requirements are independent of whether the output matches its JSON schema.
    normalized = " ".join(source.casefold().split())
    for food in value.foods:
        evidence = " ".join(food.evidence.casefold().split())
        if (evidence not in normalized or food.name.casefold() not in evidence
                or (food.quantity and food.quantity.casefold() not in evidence)):
            raise ProviderFailure("The extracted food lacked supplied evidence. Please describe it again")
    if value.intent == "update":
        if not value.target_meal_id:
            return "Which saved meal should I change? Please name the meal type and its foods."
        if value.target_meal_id not in {meal.id for meal in meals}:
            return "I could not identify that meal in today's records. Which saved meal should I change?"
    if not value.foods:
        return "What foods did you have?"
    if not value.meal_type:
        return "Was that breakfast, lunch, dinner, or a snack?"
    if value.intent == "clarify":
        return "Please clarify which foods and meal you want to record or change."
    return None
