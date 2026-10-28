"""Initial synthetic profiles, permissions, conversation safety, and meals.

Explicit schema snapshot; do not import mutable model definitions into migrations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def patient_fk():
    return sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False)


def upgrade():
    op.create_table("patients",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(100), nullable=False),
        sa.Column("timezone", sa.String(60), nullable=False), sa.Column("summary", sa.String(500), nullable=False))
    op.create_table("prescriptions", sa.Column("id", sa.String(36), primary_key=True), patient_fk(),
        sa.Column("name", sa.String(100), nullable=False), sa.Column("strength", sa.String(60), nullable=False),
        sa.Column("frequency", sa.String(100), nullable=False))
    op.create_index("ix_prescriptions_patient_id", "prescriptions", ["patient_id"])
    op.create_table("measurements", sa.Column("id", sa.String(36), primary_key=True), patient_fk(),
        sa.Column("day", sa.Date(), nullable=False), sa.Column("values", JSONB(), nullable=False),
        sa.UniqueConstraint("patient_id", "day", name="uq_measurements_patient_id"))
    op.create_index("ix_measurements_patient_id", "measurements", ["patient_id"])
    op.create_table("goals", sa.Column("id", sa.String(36), primary_key=True), patient_fk(),
        sa.Column("metric", sa.String(40), nullable=False), sa.Column("target", sa.Integer(), nullable=False))
    op.create_index("ix_goals_patient_id", "goals", ["patient_id"])
    op.create_table("accounts", sa.Column("clerk_user_id", sa.String(100), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=True),
        sa.CheckConstraint("role IN ('patient', 'clinician')", name=op.f("ck_accounts_role")),
        sa.CheckConstraint("(role = 'patient' AND patient_id IS NOT NULL) OR "
                           "(role = 'clinician' AND patient_id IS NULL)",
                           name=op.f("ck_accounts_role_patient_mapping")))
    op.create_table("clinician_assignments",
        sa.Column("clinician_id", sa.String(100), sa.ForeignKey("accounts.clerk_user_id"), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), primary_key=True))
    op.create_table("conversations", sa.Column("id", sa.String(36), primary_key=True), patient_fk(),
        sa.Column("feature", sa.String(30), nullable=False), sa.Column("state", JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(36)), sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("patient_id", "feature", name="uq_conversations_patient_id"))
    op.create_index("ix_conversations_patient_id", "conversations", ["patient_id"])
    op.create_table("client_requests",
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), primary_key=True),
        sa.Column("request_id", sa.String(36), primary_key=True),
        sa.Column("feature", sa.String(30), nullable=False), sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False), sa.Column("checkpoint", JSONB()),
        sa.Column("result", JSONB()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("meals", sa.Column("id", sa.String(36), primary_key=True), patient_fk(),
        sa.Column("source_request_id", sa.String(36), nullable=False),
        sa.Column("local_day", sa.Date(), nullable=False), sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("foods", JSONB(), nullable=False), sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("insight_status", sa.String(20), nullable=False), sa.Column("insight", sa.String(1000)),
        sa.CheckConstraint("revision > 0", name=op.f("ck_meals_revision_positive")),
        sa.UniqueConstraint("patient_id", "source_request_id", name="uq_meals_patient_id"))
    op.create_index("ix_meals_patient_id", "meals", ["patient_id"])
    op.create_index("ix_meals_local_day", "meals", ["local_day"])


def downgrade():
    for table in ("meals", "client_requests", "conversations", "clinician_assignments",
                  "accounts", "goals", "measurements", "prescriptions", "patients"):
        op.drop_table(table)
