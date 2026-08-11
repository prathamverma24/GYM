from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(32), default="athlete")
    status: Mapped[str] = mapped_column(String(32), default="active")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    consent_type: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "consent_type", name="uq_user_consent_type"),)


class AthleteProfile(Base, TimestampMixin):
    __tablename__ = "athlete_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_system: Mapped[str] = mapped_column(String(16), default="metric")
    country: Mapped[str] = mapped_column(String(64), default="India")
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    activity_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_target_ml: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    training_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    primary_goal: Mapped[str | None] = mapped_column(String(48), nullable=True)
    equipment: Mapped[list] = mapped_column(JSON, default=list)
    schedule: Mapped[dict] = mapped_column(JSON, default=dict)
    dietary_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    limitation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=1)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)


class BodyMetricEntry(Base):
    __tablename__ = "body_metric_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    chest_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    shoulders_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    arms_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    thighs_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    hips_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    neck_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")


class ReadinessLog(Base, TimestampMixin):
    __tablename__ = "readiness_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    local_date: Mapped[date] = mapped_column(Date)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    soreness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resting_heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (UniqueConstraint("athlete_id", "local_date", name="uq_readiness_day"),)


class Exercise(Base, TimestampMixin):
    __tablename__ = "exercises"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str | None] = mapped_column(String(16), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(48))
    primary_muscles: Mapped[list] = mapped_column(JSON, default=list)
    secondary_muscles: Mapped[list] = mapped_column(JSON, default=list)
    movement_pattern: Mapped[str] = mapped_column(String(48))
    equipment: Mapped[list] = mapped_column(JSON, default=list)
    equipment_display: Mapped[str | None] = mapped_column(String(160), nullable=True)
    equipment_options: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[str] = mapped_column(String(32))
    training_types: Mapped[list] = mapped_column(JSON, default=list)
    is_compound: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unilateral: Mapped[bool] = mapped_column(Boolean, default=False)
    tracking_metric: Mapped[str] = mapped_column(String(24), default="reps")
    minimum_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    modality: Mapped[str] = mapped_column(String(32), default="weighted_reps")
    instructions: Mapped[str] = mapped_column(Text)
    safety_notes: Mapped[str] = mapped_column(Text)
    default_sets: Mapped[int] = mapped_column(Integer, default=3)
    default_rep_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_rep_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_seconds: Mapped[int] = mapped_column(Integer, default=90)
    source_version: Mapped[str] = mapped_column(String(32), default="athleteos-v1")
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[str] = mapped_column(String(24), default="1.0")
    published: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkoutSplitTemplate(Base):
    __tablename__ = "workout_split_templates"
    source_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    approach_family: Mapped[str] = mapped_column(String(64))
    days_per_week: Mapped[int] = mapped_column(Integer, index=True)
    experience_min: Mapped[str] = mapped_column(String(32))
    experience_max: Mapped[str] = mapped_column(String(32))
    primary_goals: Mapped[list] = mapped_column(JSON, default=list)
    athlete_types: Mapped[list] = mapped_column(JSON, default=list)
    typical_muscle_frequency: Mapped[str] = mapped_column(String(24))
    weekly_set_guardrails: Mapped[dict] = mapped_column(JSON, default=dict)
    session_minutes: Mapped[str] = mapped_column(String(24))
    equipment_requirement: Mapped[str] = mapped_column(String(80))
    recovery_demand: Mapped[str] = mapped_column(String(32))
    schedule_pattern: Mapped[str] = mapped_column(Text)
    day_blueprints: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text)
    source_version: Mapped[str] = mapped_column(String(32), default="dataset-v1.0")


class WorkoutDayTemplate(Base):
    __tablename__ = "workout_day_templates"
    source_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    split_source_id: Mapped[str] = mapped_column(
        ForeignKey("workout_split_templates.source_id", ondelete="CASCADE"), index=True
    )
    day_order: Mapped[int] = mapped_column(Integer)
    blueprint_code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))
    focus: Mapped[str] = mapped_column(String(180))
    recommended_after_day: Mapped[str] = mapped_column(Text)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)


class ProgressionRuleDefinition(Base):
    __tablename__ = "progression_rule_definitions"
    source_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    applies_to: Mapped[str] = mapped_column(Text)
    trigger: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    regression: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text)


class ExerciseSubstitutionGroup(Base):
    __tablename__ = "exercise_substitution_groups"
    source_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    default_exercise: Mapped[str] = mapped_column(String(120))
    alternatives: Mapped[list] = mapped_column(JSON, default=list)
    logic: Mapped[str] = mapped_column(Text)


class WorkoutPrescriptionTemplate(Base):
    __tablename__ = "workout_prescription_templates"
    source_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    day_template_source_id: Mapped[str] = mapped_column(
        ForeignKey("workout_day_templates.source_id", ondelete="CASCADE"), index=True
    )
    exercise_source_id: Mapped[str] = mapped_column(
        ForeignKey("exercises.source_id"), index=True
    )
    exercise_name: Mapped[str] = mapped_column(String(120))
    exercise_order: Mapped[int] = mapped_column(Integer)
    sets: Mapped[int] = mapped_column(Integer)
    rep_min: Mapped[int] = mapped_column(Integer)
    rep_max: Mapped[int] = mapped_column(Integer)
    target_rir: Mapped[int] = mapped_column(Integer)
    rest_seconds: Mapped[int] = mapped_column(Integer)
    progression_rule_source_id: Mapped[str] = mapped_column(
        ForeignKey("progression_rule_definitions.source_id"), index=True
    )
    substitution_group_source_id: Mapped[str | None] = mapped_column(
        ForeignKey("exercise_substitution_groups.source_id"), nullable=True
    )
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProgramSelectionRule(Base):
    __tablename__ = "program_selection_rules"
    source_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    days_min: Mapped[int] = mapped_column(Integer)
    days_max: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(40))
    goal: Mapped[str] = mapped_column(String(80))
    equipment: Mapped[str] = mapped_column(String(80))
    athlete_type: Mapped[str] = mapped_column(String(80))
    recommended_splits: Mapped[list] = mapped_column(JSON, default=list)
    priority: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)


class ResearchSource(Base):
    __tablename__ = "research_sources"
    source_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    topic: Mapped[str] = mapped_column(String(180))
    evidence_summary: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(500))
    accessed: Mapped[date] = mapped_column(Date)


class Program(Base):
    __tablename__ = "programs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(24), default="active")
    generator_version: Mapped[str] = mapped_column(String(24), default="rules-v1")
    rationale: Mapped[list] = mapped_column(JSON, default=list)
    starts_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProgramDay(Base):
    __tablename__ = "program_days"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    program_id: Mapped[str] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), index=True)
    day_index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(100))
    focus: Mapped[list] = mapped_column(JSON, default=list)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=60)
    __table_args__ = (UniqueConstraint("program_id", "day_index", name="uq_program_day_index"),)


class PrescribedExercise(Base):
    __tablename__ = "prescribed_exercises"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    program_day_id: Mapped[str] = mapped_column(ForeignKey("program_days.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"))
    order_index: Mapped[int] = mapped_column(Integer)
    target_sets: Mapped[int] = mapped_column(Integer)
    rep_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rep_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_seconds: Mapped[int] = mapped_column(Integer)
    target_rir: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    program_day_id: Mapped[str] = mapped_column(ForeignKey("program_days.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[str | None] = mapped_column(String(24), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_volume_kg: Mapped[float] = mapped_column(Float, default=0)


class SetLog(Base, TimestampMixin):
    __tablename__ = "set_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workout_session_id: Mapped[str] = mapped_column(ForeignKey("workout_sessions.id", ondelete="CASCADE"), index=True)
    prescribed_exercise_id: Mapped[str] = mapped_column(ForeignKey("prescribed_exercises.id"), index=True)
    set_index: Mapped[int] = mapped_column(Integer)
    client_operation_id: Mapped[str] = mapped_column(String(64), unique=True)
    load_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    assistance_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    rir: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint(
            "workout_session_id",
            "prescribed_exercise_id",
            "set_index",
            name="uq_session_prescription_set",
        ),
    )


class PersonalRecord(Base):
    __tablename__ = "personal_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), index=True)
    workout_session_id: Mapped[str] = mapped_column(ForeignKey("workout_sessions.id"))
    record_type: Mapped[str] = mapped_column(String(32))
    value: Mapped[float] = mapped_column(Float)
    achieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RecommendationDecision(Base):
    __tablename__ = "recommendation_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    decision_type: Mapped[str] = mapped_column(String(48))
    evidence_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    rule_set_version: Mapped[str] = mapped_column(String(24), default="progression-v1")
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    safety_checks: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="proposed")
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Food(Base, TimestampMixin):
    __tablename__ = "foods"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    canonical_name: Mapped[str] = mapped_column(String(160))
    normalized_name: Mapped[str] = mapped_column(String(180), index=True)
    food_type: Mapped[str] = mapped_column(String(32), default="dish")
    cuisine: Mapped[str] = mapped_column(String(48), default="global")
    diet_type: Mapped[str] = mapped_column(String(24), default="vegetarian")
    energy_kcal: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carb_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    fiber_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="athleteos_curated_v1")
    source_version: Mapped[str] = mapped_column(String(24), default="1.0")
    data_quality: Mapped[str] = mapped_column(String(24), default="estimated")


class FoodAlias(Base):
    __tablename__ = "food_aliases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    food_id: Mapped[str] = mapped_column(ForeignKey("foods.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(160))
    normalized_alias: Mapped[str] = mapped_column(String(180), index=True)
    locale: Mapped[str] = mapped_column(String(16), default="en-IN")


class ServingOption(Base):
    __tablename__ = "serving_options"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    food_id: Mapped[str] = mapped_column(ForeignKey("foods.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(64))
    grams: Mapped[float] = mapped_column(Float)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class MealLog(Base):
    __tablename__ = "meal_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    local_date: Mapped[date] = mapped_column(Date)
    meal_type: Mapped[str] = mapped_column(String(24))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("athlete_id", "local_date", "meal_type", name="uq_meal_day_type"),)


class MealItem(Base, TimestampMixin):
    __tablename__ = "meal_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    meal_log_id: Mapped[str] = mapped_column(ForeignKey("meal_logs.id", ondelete="CASCADE"), index=True)
    food_id: Mapped[str] = mapped_column(ForeignKey("foods.id"))
    food_name_snapshot: Mapped[str] = mapped_column(String(160))
    consumed_grams: Mapped[float] = mapped_column(Float)
    serving_label: Mapped[str] = mapped_column(String(64))
    energy_kcal: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carb_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    source_snapshot: Mapped[str] = mapped_column(String(96))


class WaterLog(Base):
    __tablename__ = "water_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    amount_ml: Mapped[int] = mapped_column(Integer)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    local_date: Mapped[date] = mapped_column(Date)
    client_operation_id: Mapped[str] = mapped_column(String(64), unique=True)


class Habit(Base, TimestampMixin):
    __tablename__ = "habits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(32), default="wellness")
    measurement_type: Mapped[str] = mapped_column(String(24), default="boolean")
    target_value: Mapped[float] = mapped_column(Float, default=1)
    target_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    schedule: Mapped[dict] = mapped_column(JSON, default=lambda: {"frequency": "daily"})
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    derived_source: Mapped[str | None] = mapped_column(String(32), nullable=True)


class HabitCompletion(Base, TimestampMixin):
    __tablename__ = "habit_completions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    habit_id: Mapped[str] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"), index=True)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    local_date: Mapped[date] = mapped_column(Date)
    value: Mapped[float] = mapped_column(Float, default=1)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        UniqueConstraint("habit_id", "athlete_id", "local_date", name="uq_habit_completion_day"),
    )


class CvAssessment(Base):
    __tablename__ = "cv_assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athlete_profiles.id", ondelete="CASCADE"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    capture_type: Mapped[str] = mapped_column(String(24), default="front")
    model_version: Mapped[str] = mapped_column(String(64))
    feature_schema_version: Mapped[str] = mapped_column(String(32))
    quality_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    quality_flags: Mapped[list] = mapped_column(JSON, default=list)
    derived_features: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_media_stored: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
