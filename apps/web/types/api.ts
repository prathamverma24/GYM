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
