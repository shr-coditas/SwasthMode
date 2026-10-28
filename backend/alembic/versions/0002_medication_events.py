"""Medication events and retained confirmation questions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_medication_events"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("medication_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("prescription_id", sa.String(36), sa.ForeignKey("prescriptions.id"), nullable=False),
        sa.Column("source_request_id", sa.String(36), nullable=False),
        sa.Column("reported", JSONB(), nullable=False),
        sa.Column("prescription_snapshot", JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(60), nullable=False),
        sa.Column("time_evidence", sa.String(100), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision > 0", name=op.f("ck_medication_events_revision_positive")),
        sa.UniqueConstraint("patient_id", "source_request_id", name="uq_medication_events_patient_id"))
    op.create_index("ix_medication_events_patient_id", "medication_events", ["patient_id"])
    op.create_index("ix_medication_events_occurred_at", "medication_events", ["occurred_at"])
    op.create_table("medication_questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("step_id", sa.String(36), nullable=False),
        sa.Column("question_version", sa.Integer(), nullable=False),
        sa.Column("medication_id", sa.String(36), sa.ForeignKey("prescriptions.id"), nullable=False),
        sa.Column("proposal", JSONB(), nullable=False),
        sa.Column("readback", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("step_id", name="uq_medication_questions_step_id"))
    op.create_index("ix_medication_questions_patient_id", "medication_questions", ["patient_id"])


def downgrade():
    op.drop_table("medication_questions")
    op.drop_table("medication_events")
