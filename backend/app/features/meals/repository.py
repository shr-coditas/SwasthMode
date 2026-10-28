from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db.session import sessions
from app.features.meals.models import Meal
from app.features.meals.schemas import MealExtraction, MealView


class MealRepository:
    """Concrete data access to SwasthMode's single PostgreSQL database."""

    def meals(self, patient_id: str, day: date | None = None) -> list[MealView]:
        query = select(Meal).where(Meal.patient_id == patient_id)
        if day:
            query = query.where(Meal.local_day == day)
        with sessions()() as db:
            rows = db.scalars(query.order_by(Meal.updated_at.desc()).limit(100)).all()
            return [MealView.model_validate(row) for row in rows]

    def write_meal(
        self,
        db: Session,
        patient_id: str,
        request_id: str,
        extraction: MealExtraction,
        expected_revision: int | None,
    ) -> Meal:
        from app.core.db.base import now
        from fastapi import HTTPException
        from sqlalchemy import update

        values = {
            "meal_type": extraction.meal_type,
            "foods": [f.model_dump() for f in extraction.foods],
            "local_day": extraction.local_day,
            "insight_status": "pending",
            "insight": None,
            "updated_at": now(),
        }
        if extraction.intent == "update":
            meal = db.scalar(
                update(Meal)
                .where(
                    Meal.id == extraction.target_meal_id,
                    Meal.patient_id == patient_id,
                    Meal.revision == expected_revision,
                )
                .values(**values, revision=Meal.revision + 1)
                .returning(Meal)
            )
            if not meal:
                raise HTTPException(
                    409,
                    "That meal changed. Please reload and describe the correction again",
                )
        else:
            meal = Meal(
                patient_id=patient_id,
                source_request_id=request_id,
                revision=1,
                **values,
            )
            db.add(meal)
            db.flush()
        return meal
