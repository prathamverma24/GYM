import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { StrengthIntelligence } from "@/features/progress/strength-intelligence";
import type { StrengthAnalysis, StrengthReport } from "@/types/api";

const chest = {
  id: "chest-id",
  slug: "chest",
  name: "Chest",
  body_region: "upper" as const,
  score: 78,
  previous_score: 72,
  change_percent: 8.3,
  performance_change_percent: 6.5,
  status: "Strong",
  confidence: "high" as const,
  sessions: 7,
  working_sets: 18,
  training_volume_kg: 18450,
  exercise_diversity: 2,
  top_exercise: {
    id: "bench-id",
    name: "Barbell Bench Press",
    contribution: 1,
    sets: 10,
    volume: 8400,
    best: 82.5,
    best_e1rm: 82.5,
    previous_best: 77.8,
    change_percent: 6,
    best_set: { date: "2026-08-11", load_kg: 65, reps: 8, seconds: null, rir: 2, performance: 82.5 },
    recent: [],
  },
  exercises: [],
};

const hamstrings = {
  ...chest,
  id: "hamstrings-id",
  slug: "hamstrings",
  name: "Hamstrings",
  score: null,
  previous_score: null,
  change_percent: null,
  performance_change_percent: null,
  status: "Insufficient Data",
  confidence: "insufficient" as const,
  sessions: 1,
  working_sets: 2,
  training_volume_kg: 1200,
  exercise_diversity: 1,
  top_exercise: null,
  exercises: [],
};

const analysis: StrengthAnalysis = {
  analytics_version: "strength_v1",
  period: { type: "month", start: "2026-08-01", end: "2026-08-12", expected_end: "2026-08-31", partial: true, comparison_start: "2026-07-01", comparison_end: "2026-07-12", timezone: "Asia/Kolkata" },
  profile_state: "ready",
  sessions_recorded: 7,
  unlock_target_sessions: 3,
  overall: { score: 75, previous_score: 70, change_percent: 7.1, confidence: "high" },
  strongest: { muscle_id: "chest-id", muscle: "Chest", score: 78 },
  most_improved: { muscle_id: "chest-id", muscle: "Chest", change_percent: 8.3 },
  needs_attention: null,
  muscles: [chest, hamstrings],
  balance: [{ name: "Chest vs Back", left_label: "Chest", right_label: "Back", left: { score: 78, working_sets: 18, sessions: 7, confidence: "high" }, right: { score: null, working_sets: 0, sessions: 0, confidence: "insufficient" }, difference_percent: null, insight: "More completed training history is needed for this performance comparison." }],
  trend: [{ date: "2026-08-05", overall: 70, chest: 72, hamstrings: null }, { date: "2026-08-12", overall: 75, chest: 78, hamstrings: null }],
  recommendations: [{ muscle: "Chest", action: "Maintain current progression", reason: "Chest was one of your fastest improving areas this period.", confidence: "high" }],
  methodology_note: "Scores describe user-relative recorded training performance and exposure, not isolated biological or medical strength.",
};

function renderStrength(overrides: Partial<StrengthAnalysis> = {}, report: StrengthReport | null = null) {
  const onPeriodChange = vi.fn();
  const onGenerateReport = vi.fn();
  render(<StrengthIntelligence data={{ ...analysis, ...overrides }} period="month" onPeriodChange={onPeriodChange} onGenerateReport={onGenerateReport} report={report} onCloseReport={vi.fn()} generatingReport={false} />);
  return { onPeriodChange, onGenerateReport };
}

describe("StrengthIntelligence", () => {
  it("changes periods and renders actual strength cards", () => {
    const { onPeriodChange } = renderStrength();
    expect(screen.getByText("75 / 100")).toBeInTheDocument();
    expect(screen.getAllByText("Chest").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Week" }));
    expect(onPeriodChange).toHaveBeenCalledWith("week");
  });

  it("opens the accessible muscle detail panel and triggers report generation", () => {
    const { onGenerateReport } = renderStrength();
    fireEvent.click(screen.getByRole("button", { name: /Chest: 78 out of 100, Strong/ }));
    expect(screen.getByRole("dialog", { name: "Chest" })).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /Generate Strength Report/ })[0]);
    expect(onGenerateReport).toHaveBeenCalledOnce();
  });

  it("shows honest empty and limited-data states instead of fake scores", () => {
    const { rerender } = render(<StrengthIntelligence data={{ ...analysis, profile_state: "empty", sessions_recorded: 0, overall: { score: null, previous_score: null, change_percent: null, confidence: "insufficient" }, strongest: null, most_improved: null, muscles: [hamstrings] }} period="month" onPeriodChange={vi.fn()} onGenerateReport={vi.fn()} report={null} onCloseReport={vi.fn()} generatingReport={false} />);
    expect(screen.getByText("Complete your first few workouts.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Start Workout/ })).toHaveAttribute("href", "/workouts");
    rerender(<StrengthIntelligence data={{ ...analysis, profile_state: "building", sessions_recorded: 2, overall: { score: null, previous_score: null, change_percent: null, confidence: "insufficient" }, strongest: null, most_improved: null, muscles: [hamstrings] }} period="month" onPeriodChange={vi.fn()} onGenerateReport={vi.fn()} report={null} onCloseReport={vi.fn()} generatingReport={false} />);
    expect(screen.getByText("2 of 3 recommended sessions recorded")).toBeInTheDocument();
    expect(screen.getAllByText("Not Enough Data").length).toBeGreaterThan(0);
  });
});
