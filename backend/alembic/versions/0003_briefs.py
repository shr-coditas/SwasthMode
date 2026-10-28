"""Persist patient morning and evening brief snapshots."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002_medication_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "briefs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("source_request_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("local_day", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(60), nullable=False),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        sa.Column("narrative", postgresql.JSONB(), nullable=False),
        sa.Column("text", sa.String(6000), nullable=False),
        sa.Column("focus_text", sa.String(300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('morning', 'evening')", name="kind_allowed"),
        sa.UniqueConstraint("patient_id", "source_request_id"))
    op.create_index("ix_briefs_patient_kind_day", "briefs", ["patient_id", "kind", "local_day"])


def downgrade():
    op.drop_table("briefs")
