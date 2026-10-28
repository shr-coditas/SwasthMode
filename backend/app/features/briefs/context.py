from datetime import UTC, datetime, time, timedelta
import math
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.auth.permissions import PatientAccess
from app.features.briefs.schemas import BriefContext, BriefKind, Fact
from app.features.meals.models import Meal
from app.features.medications.models import MedicationEvent
from app.features.patients.models import Goal, Measurement


def gather(db, access: PatientAccess, kind: BriefKind, captured_at: datetime) -> BriefContext:
    zone = ZoneInfo(access.timezone)
    today = captured_at.astimezone(zone).date()
    end = today - timedelta(days=1) if kind == "morning" else today
    start = end - timedelta(days=6) if kind == "morning" else today
    lower = datetime.combine(start, time.min, zone).astimezone(UTC)
    upper = min(datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(UTC), captured_at)
    measurements = list(db.scalars(select(Measurement).where(
        Measurement.patient_id == access.patient_id, Measurement.day >= start,
        Measurement.day <= end).order_by(Measurement.day.desc()).limit(7)))
    goals = list(db.scalars(select(Goal).where(Goal.patient_id == access.patient_id)
                           .order_by(Goal.id).limit(21)))
    meals = list(db.scalars(select(Meal).where(
        Meal.patient_id == access.patient_id, Meal.local_day >= start, Meal.local_day <= end,
        Meal.created_at <= captured_at).order_by(Meal.local_day.desc(), Meal.id).limit(101)))
    events = list(db.scalars(select(MedicationEvent).where(
        MedicationEvent.patient_id == access.patient_id, MedicationEvent.occurred_at >= lower,
        MedicationEvent.occurred_at < upper, MedicationEvent.created_at <= captured_at)
        .order_by(MedicationEvent.occurred_at.desc(), MedicationEvent.id).limit(101)))
    facts = []
    missing = []
    limits = ["Morning uses the previous seven complete local days; evening uses today up to capture time.",
              "Daily measurements have no collection time; today's values may be partial.",
              "Meal dates are reported local days. Medication windows use recorded event instants.",
              "Medication records describe reports only. Missing logs never establish missed doses.",
              "Profiles, goals and measurements are synthetic POC data; medication events can also be labeled synthetic."]
    for label, rows in (("meal", meals), ("medication event", events)):
        sampled = rows[:100]
        bounded = len(rows) > 100
        count_text = f"At least {len(sampled)}" if bounded else str(len(sampled))
        sources = [f"{'meals' if label == 'meal' else 'medication_events'}:{row.id}:revision:{row.revision}"
                   for row in sampled]
        facts.append(Fact(id=f"count_{label.replace(' ', '_')}",
                          text=f"{count_text} {label} records in the selected window.", sources=sources))
        if bounded:
            limits.append(f"{label.capitalize()} provenance is limited to the first 100 records; count is a lower bound.")
        if not rows:
            missing.append(f"No {label} records in this window; this does not establish what happened outside logging.")
        if label == "medication event" and any(row.synthetic for row in sampled):
            limits.append("The medication event sample includes explicitly synthetic seed events.")
    if len(goals) > 20:
        limits.append("Goal context is limited to the first 20 goals ordered by ID.")
    for metric, unit, ceiling in (("steps", "steps", 200000), ("sleep_hours", "hours of sleep", 24)):
        recorded = []
        for row in measurements:
            value = row.values.get(metric)
            if (isinstance(value, (int, float)) and not isinstance(value, bool)
                    and math.isfinite(value) and 0 <= value <= ceiling
                    and (metric != "steps" or float(value).is_integer())):
                recorded.append((row, value))
                facts.append(Fact(id=f"{metric}_{row.day.isoformat()}",
                                  text=f"On {row.day.isoformat()}, the recorded value was {value:g} {unit}.",
                                  sources=[f"measurements:{row.id}:{metric}"]))
        absent = [str(start + timedelta(days=offset)) for offset in range((end - start).days + 1)
                  if not any(row.day == start + timedelta(days=offset) for row, value in recorded)]
        if absent:
            missing.append(f"No usable {metric} measurement for: {', '.join(absent)}.")
        if recorded:
            average = sum(value for row, value in recorded) / len(recorded)
            facts.append(Fact(id=f"average_{metric}",
                              text=f"The recorded-day average was {average:.1f} {unit} across {len(recorded)} recorded days; missing days are excluded.",
                              sources=[f"measurements:{row.id}:{metric}" for row, value in recorded]))
        matching = [goal for goal in goals[:20] if goal.metric == metric]
        if len(matching) != 1 or not 0 < matching[0].target <= ceiling:
            missing.append(f"No single supported {metric} goal is available for comparison.")
            continue
        goal = matching[0]
        on_end = next(((row, value) for row, value in recorded if row.day == end), None)
        if on_end:
            row, value = on_end
            outcome = "at or above" if value >= goal.target else "below"
            facts.append(Fact(id=f"goal_{metric}",
                              text=f"For {end}, the recorded {metric} value was {outcome} the stored goal of {goal.target}; this compares recorded values only.",
                              sources=[f"measurements:{row.id}:{metric}", f"goals:{goal.id}"]))
    return BriefContext(kind=kind, local_day=today, timezone=access.timezone, captured_at=captured_at,
                        window_start=start, window_end=end, facts=facts, missing=missing, limits=limits)
