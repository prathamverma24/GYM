export type User = {
  id: string;
  email: string;
  full_name: string;
  first_name: string;
  role: string;
  timezone: string;
  onboarding_completed: boolean;
  onboarding_step: number;
  experience_level: string | null;
};

export type ApiErrorPayload = {
  code: string;
  message: string;
  details?: unknown;
  request_id?: string;
  retryable?: boolean;
};

export type Exercise = {
  id: string;
  source_id: string | null;
  name: string;
  slug: string;
  category: string;
  primary_muscles: string[];
  secondary_muscles: string[];
  movement_pattern: string;
  equipment: string[];
  equipment_display: string | null;
  equipment_options: string[][];
  difficulty: string;
  training_types: string[];
  is_compound: boolean;
  is_unilateral: boolean;
  tracking_metric: "reps" | "seconds" | "meters" | "minutes";
  minimum_level: string | null;
  modality: string;
  instructions: string;
  safety_notes: string;
  default_sets: number;
  default_rep_min: number | null;
  default_rep_max: number | null;
  default_seconds: number | null;
  rest_seconds: number;
  source_version: string;
  version: string;
};

export type Prescription = {
  id: string;
  order_index: number;
  target_sets: number;
  rep_min: number | null;
  rep_max: number | null;
  target_seconds: number | null;
  rest_seconds: number;
  target_rir: number | null;
  notes: string | null;
  exercise: Exercise;
  previous: Array<{ load_kg: number | null; reps: number | null; rir: number | null }>;
};

export type ProgramDay = {
  id: string;
  program_id: string;
  day_index: number;
  title: string;
  focus: string[];
  scheduled_date: string | null;
  estimated_minutes: number;
  exercises: Prescription[];
};

export type Program = {
  id: string;
  name: string;
  generator_version: string;
  rationale: string[];
  starts_on: string;
  days: ProgramDay[];
};

export type SetLog = {
  id?: string;
  prescribed_exercise_id: string;
  set_index: number;
  client_operation_id: string;
  load_kg: number | null;
  reps: number | null;
  seconds: number | null;
  distance_m?: number | null;
  assistance_kg?: number | null;
  rir: number | null;
  rpe?: number | null;
  completed: boolean;
  notes?: string | null;
};

export type WorkoutSession = {
  id: string;
  status: "active" | "completed";
  started_at: string;
  completed_at: string | null;
  session_rpe: number | null;
  rating: string | null;
  notes: string | null;
  total_volume_kg: number;
  day: ProgramDay;
  sets: SetLog[];
};

export type StrengthPeriod = "week" | "month" | "3_months";
export type StrengthConfidence = "insufficient" | "low" | "medium" | "high";

export type ExercisePerformance = {
  id: string;
  name: string;
  contribution: number;
  sets: number;
  volume: number;
  best: number | null;
  best_e1rm: number | null;
  previous_best: number | null;
  change_percent: number | null;
  best_set: { date: string; load_kg: number | null; reps: number | null; seconds: number | null; rir: number | null; performance: number | null } | null;
  recent: Array<{ date: string; load_kg: number | null; reps: number | null; seconds: number | null; rir: number | null; performance: number | null }>;
};

export type MusclePerformance = {
  id: string;
  slug: string;
  name: string;
  body_region: "upper" | "core" | "lower";
  score: number | null;
  previous_score: number | null;
  change_percent: number | null;
  performance_change_percent: number | null;
  status: string;
  confidence: StrengthConfidence;
  sessions: number;
  working_sets: number;
  training_volume_kg: number;
  exercise_diversity: number;
  top_exercise: ExercisePerformance | null;
  exercises: ExercisePerformance[];
};

export type StrengthAnalysis = {
  analytics_version: string;
  period: { type: StrengthPeriod; start: string; end: string; expected_end: string; partial: boolean; comparison_start: string; comparison_end: string; timezone: string };
  profile_state: "empty" | "building" | "ready";
  sessions_recorded: number;
  unlock_target_sessions: number;
  overall: { score: number | null; previous_score: number | null; change_percent: number | null; confidence: StrengthConfidence };
  strongest: { muscle_id: string; muscle: string; score: number } | null;
  most_improved: { muscle_id: string; muscle: string; change_percent: number } | null;
  needs_attention: { muscle_id: string; muscle: string; score: number } | null;
  muscles: MusclePerformance[];
  balance: Array<{
    name: string;
    left_label: string;
    right_label: string;
    left: { score: number | null; working_sets: number; sessions: number; confidence: StrengthConfidence };
    right: { score: number | null; working_sets: number; sessions: number; confidence: StrengthConfidence };
    difference_percent: number | null;
    insight: string;
  }>;
  trend: Array<{ date: string; overall: number | null; [muscle: string]: string | number | null }>;
  recommendations: Array<{ muscle: string | null; action: string; reason: string; confidence: StrengthConfidence }>;
  methodology_note: string;
};

export type StrengthReport = {
  id: string;
  period_type: StrengthPeriod;
  period_start: string;
  period_end: string;
  overall_score: number | null;
  generated_at: string;
  analytics_version: string;
  report: {
    title: string;
    analysis: StrengthAnalysis;
    training_summary: { sessions: number; sessions_started: number; working_sets: number; training_volume_kg: number; workout_completion_percent: number };
    recovery: { average_sleep_hours: number | null; average_readiness: number | null; check_ins: number };
    recommendations: StrengthAnalysis["recommendations"];
    generated_for: string;
  };
};

export type Food = {
  id: string;
  canonical_name: string;
  food_type: string;
  cuisine: string;
  diet_type: string;
  per_100g: { energy_kcal: number; protein_g: number; carb_g: number; fat_g: number; fiber_g: number | null };
  source: string;
  data_quality: string;
  servings: Array<{ id: string; label: string; grams: number; is_default: boolean }>;
  estimate_note: string | null;
};
