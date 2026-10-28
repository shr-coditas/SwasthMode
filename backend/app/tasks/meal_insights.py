import asyncio
import logging
from sqlalchemy import update
from app.ai.client import ProviderFailure
from app.ai.nemo import SafetyUnavailable
from app.core.db.session import sessions
from app.features.meals.insights import generate_insight
from app.features.meals.models import Meal
from app.tasks.celery_app import celery

log = logging.getLogger("swasthmode.tasks")


def set_status(meal_id: str, revision: int, **values):
    with sessions()() as db, db.begin():
        db.execute(update(Meal).where(Meal.id == meal_id, Meal.revision == revision,
                                     Meal.insight_status != "completed").values(**values))


@celery.task(bind=True, name="swasthmode.meal_insight", max_retries=2)
def meal_insight(self, meal_id: str, revision: int):
    with sessions()() as db:
        meal = db.get(Meal, meal_id)
        if not meal or meal.revision != revision or meal.insight_status == "completed":
            return {"status": "obsolete_or_completed"}
        foods = meal.foods
    try:
        text = asyncio.run(generate_insight(foods))
        set_status(meal_id, revision, insight=text, insight_status="completed")
        log.info("task_id=%s status=completed", self.request.id)
        return {"status": "completed"}
    except (ProviderFailure, SafetyUnavailable):
        set_status(meal_id, revision, insight=None, insight_status="failed")
        log.info("task_id=%s status=failed", self.request.id)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=RuntimeError("Meal insight provider failed"), countdown=15)
        raise RuntimeError("Meal insight failed after bounded retries") from None


def enqueue(meal_id: str, revision: int):
    try:
        meal_insight.delay(meal_id, revision)
    except Exception:
        set_status(meal_id, revision, insight_status="failed", insight=None)
        log.info("status=enqueue_failed")
