from app.features.meals.schemas import MealView


def saved_reply(meal: MealView, updated: bool) -> str:
    foods = ", ".join(f"{food.quantity} {food.name}" if food.quantity else food.name for food in meal.foods)
    return f"{'Updated' if updated else 'Saved'} your {meal.meal_type}: {foods}. Your meal insight is pending."
