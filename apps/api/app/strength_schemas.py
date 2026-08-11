from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

StrengthPeriod = Literal["week", "month", "3_months"]
Confidence = Literal["insufficient", "low", "medium", "high"]


class StrengthPeriodOut(BaseModel):
    type: StrengthPeriod
    start: date
    end: date
    expected_end: date
    partial: bool
    comparison_start: date
    comparison_end: date
    timezone: str


class OverallStrengthOut(BaseModel):
    score: float | None
    previous_score: float | None
    change_percent: float | None
    confidence: Confidence


class StrengthSetOut(BaseModel):
    date: date
    load_kg: float | None
    reps: int | None
    seconds: int | None
    rir: int | None
    performance: float | None


class ExercisePerformanceOut(BaseModel):
    id: str
    name: str
    contribution: float
    sets: int
    volume: float
    best: float | None
    best_e1rm: float | None
    best_set: StrengthSetOut | None
    recent: list[StrengthSetOut]
    previous_best: float | None
    change_percent: float | None


class MusclePerformanceOut(BaseModel):
    id: str
    slug: str
    name: str
    body_region: str
    score: float | None
    previous_score: float | None
    change_percent: float | None
    performance_change_percent: float | None
    status: str
    confidence: Confidence
    sessions: int
    working_sets: float
    training_volume_kg: float
    exercise_diversity: int
    top_exercise: ExercisePerformanceOut | None
    exercises: list[ExercisePerformanceOut]


class StrongestOut(BaseModel):
    muscle_id: str
    muscle: str
    score: float


class ImprovedOut(BaseModel):
    muscle_id: str
    muscle: str
    change_percent: float


class BalanceSideOut(BaseModel):
    score: float | None
    working_sets: float
    sessions: int
    confidence: Confidence


class BalanceOut(BaseModel):
    name: str
    left_label: str
    right_label: str
    left: BalanceSideOut
    right: BalanceSideOut
    difference_percent: float | None
    insight: str


class TrendPointOut(BaseModel):
    date: date
    overall: float | None

    model_config = {"extra": "allow"}


class RecommendationOut(BaseModel):
    muscle: str | None
    action: str
    reason: str
    confidence: Confidence


class StrengthAnalysisOut(BaseModel):
    analytics_version: str
    period: StrengthPeriodOut
    profile_state: Literal["empty", "building", "ready"]
    sessions_recorded: int
    unlock_target_sessions: int
    overall: OverallStrengthOut
    strongest: StrongestOut | None
    most_improved: ImprovedOut | None
    needs_attention: StrongestOut | None
    muscles: list[MusclePerformanceOut]
    balance: list[BalanceOut]
    trend: list[TrendPointOut]
    recommendations: list[RecommendationOut]
    methodology_note: str


class MuscleDetailOut(BaseModel):
    period: StrengthPeriodOut
    muscle: MusclePerformanceOut
    trend: list[TrendPointOut]
    recommendations: list[RecommendationOut]
    methodology_note: str


class StrengthReportRequest(BaseModel):
    period: StrengthPeriod = "month"
    through: date | None = None


class StrengthReportSummaryOut(BaseModel):
    id: str
    period_type: StrengthPeriod
    period_start: date
    period_end: date
    overall_score: float | None
    generated_at: datetime
    analytics_version: str


class StrengthReportOut(StrengthReportSummaryOut):
    report: dict


class StrengthReportListOut(BaseModel):
    items: list[StrengthReportSummaryOut]


class StrengthQuery(BaseModel):
    period: StrengthPeriod = "week"
    through: date | None = Field(default=None)
