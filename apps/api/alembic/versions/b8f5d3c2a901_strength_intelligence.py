"""strength intelligence reference data and stored reports

Revision ID: b8f5d3c2a901
Revises: 68cd1aa1ec80
Create Date: 2026-08-12 02:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8f5d3c2a901"
down_revision: str | Sequence[str] | None = "68cd1aa1ec80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "muscle_groups",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("body_region", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_muscle_groups_slug", "muscle_groups", ["slug"], unique=True)
    op.create_table(
        "exercise_muscle_mappings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("exercise_id", sa.String(length=36), nullable=False),
        sa.Column("muscle_group_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("contribution_weight", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["muscle_group_id"], ["muscle_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "exercise_id", "muscle_group_id", name="uq_exercise_muscle_mapping"
        ),
    )
    op.create_index(
        "ix_exercise_muscle_mappings_exercise_id",
        "exercise_muscle_mappings",
        ["exercise_id"],
    )
    op.create_index(
        "ix_exercise_muscle_mappings_muscle_group_id",
        "exercise_muscle_mappings",
        ["muscle_group_id"],
    )
    op.create_table(
        "exercise_progressions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("exercise_id", sa.String(length=36), nullable=False),
        sa.Column("progression_group", sa.String(length=80), nullable=False),
        sa.Column("level", sa.Float(), nullable=False),
        sa.Column("previous_exercise_id", sa.String(length=36), nullable=True),
        sa.Column("next_exercise_id", sa.String(length=36), nullable=True),
        sa.Column("difficulty_multiplier", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["previous_exercise_id"], ["exercises.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["next_exercise_id"], ["exercises.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exercise_id"),
    )
    op.create_index(
        "ix_exercise_progressions_exercise_id",
        "exercise_progressions",
        ["exercise_id"],
        unique=True,
    )
    op.create_index(
        "ix_exercise_progressions_progression_group",
        "exercise_progressions",
        ["progression_group"],
    )
    op.create_table(
        "strength_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("period_type", sa.String(length=24), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analytics_version", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strength_reports_user_id", "strength_reports", ["user_id"])
    op.create_index("ix_strength_reports_period_type", "strength_reports", ["period_type"])
    op.create_index("ix_strength_reports_period_start", "strength_reports", ["period_start"])
    op.create_index(
        "ix_strength_reports_user_generated",
        "strength_reports",
        ["user_id", "generated_at"],
    )
    op.create_index(
        "ix_workout_sessions_athlete_completed",
        "workout_sessions",
        ["athlete_id", "completed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_workout_sessions_athlete_completed", table_name="workout_sessions")
    op.drop_index("ix_strength_reports_user_generated", table_name="strength_reports")
    op.drop_index("ix_strength_reports_period_start", table_name="strength_reports")
    op.drop_index("ix_strength_reports_period_type", table_name="strength_reports")
    op.drop_index("ix_strength_reports_user_id", table_name="strength_reports")
    op.drop_table("strength_reports")
    op.drop_index(
        "ix_exercise_progressions_progression_group", table_name="exercise_progressions"
    )
    op.drop_index("ix_exercise_progressions_exercise_id", table_name="exercise_progressions")
    op.drop_table("exercise_progressions")
    op.drop_index(
        "ix_exercise_muscle_mappings_muscle_group_id",
        table_name="exercise_muscle_mappings",
    )
    op.drop_index(
        "ix_exercise_muscle_mappings_exercise_id",
        table_name="exercise_muscle_mappings",
    )
    op.drop_table("exercise_muscle_mappings")
    op.drop_index("ix_muscle_groups_slug", table_name="muscle_groups")
    op.drop_table("muscle_groups")
