from sqlalchemy import select

from app.core.db.session import sessions
from app.features.briefs.models import Brief
from app.features.briefs.schemas import BriefView
from app.features.briefs.validation import reuse_until


class BriefRepository:
    def reusable(self, db, patient_id, kind, local_day, timezone, timestamp):
        row = db.scalar(select(Brief).where(
            Brief.patient_id == patient_id, Brief.kind == kind, Brief.local_day == local_day,
            Brief.timezone == timezone, Brief.created_at <= timestamp)
            .order_by(Brief.created_at.desc(), Brief.id).limit(1))
        if row and timestamp < reuse_until(row.kind, row.local_day, row.timezone, row.created_at):
            return row
        return None

    def history(self, patient_id):
        with sessions()() as db:
            return [BriefView.model_validate(row) for row in db.scalars(select(Brief).where(
                Brief.patient_id == patient_id).order_by(Brief.created_at.desc(), Brief.id).limit(30))]
