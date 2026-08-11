"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Clock3, Database, GitCompareArrows, ShieldAlert, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { Card, ErrorState, LoadingState, MetricCard } from "@/components/primitives";
import { api } from "@/lib/api";
import type { Exercise } from "@/types/api";

type ExerciseProfile = {
  exercise: Exercise;
  template_usage: {
    total: number;
    items: Array<{ prescription_id: string; split_id: string; split_name: string; days_per_week: number; day_name: string; day_focus: string; sets: number; rep_min: number; rep_max: number; target_rir: number; rest_seconds: number; optional: boolean; progression_rule_id: string }>;
  };
  substitutions: Array<{ group_id: string; name: string; logic: string; exercises: Array<{ id: string; name: string; equipment_display: string | null; difficulty: string }> }>;
  progression_rules: Array<{ id: string; name: string; applies_to: string; trigger: string; action: string; regression: string; notes: string }>;
};

function label(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function target(exercise: Exercise) {
  const range = `${exercise.default_rep_min}–${exercise.default_rep_max}`;
  return `${range} ${exercise.tracking_metric === "reps" ? "reps" : exercise.tracking_metric}`;
}

export default function ExerciseDetailPage() {
  const { exerciseId } = useParams<{ exerciseId: string }>();
  const query = useQuery({ queryKey: ["exercise", exerciseId], queryFn: () => api<ExerciseProfile>(`/exercises/${exerciseId}`) });
  if (query.isLoading) return <LoadingState label="Opening exercise profile…" />;
  if (query.isError || !query.data) return <ErrorState message={query.error?.message} />;
  const { exercise, template_usage: usage, substitutions, progression_rules: progressionRules } = query.data;
  return <>
    <header className="page-head"><div><Link className="tiny" href="/exercises"><ArrowLeft size={13} style={{ display: "inline" }} /> Exercise library</Link><div className="detail-title-row"><div><h1>{exercise.name}</h1><p>{exercise.category} · {label(exercise.movement_pattern)} · {label(exercise.difficulty)}</p></div><span className="pill pill-success"><Database size={13} /> {exercise.source_id} · v{exercise.version}</span></div></div></header>

    <section className="grid progress-summary exercise-summary"><MetricCard label="Default volume" value={exercise.default_sets} unit="sets" /><MetricCard label="Target range" value={`${exercise.default_rep_min}–${exercise.default_rep_max}`} unit={exercise.tracking_metric} accent="pink" /><MetricCard label="Rest" value={exercise.rest_seconds} unit="sec" accent="orange" /><MetricCard label="Template use" value={usage.total} unit="prescriptions" accent="blue" /></section>

    <div className="report-grid exercise-profile-grid" style={{ marginTop: 16 }}>
      <Card className="report-card"><span className="eyebrow">Movement profile</span><p style={{ marginTop: 14 }}>{exercise.instructions}</p><div className="profile-facts"><div><span>Equipment</span><strong>{exercise.equipment_display ?? exercise.equipment.map(label).join(" · ")}</strong></div><div><span>Minimum level</span><strong>{label(exercise.minimum_level ?? exercise.difficulty)}</strong></div><div><span>Classification</span><strong>{exercise.is_compound ? "Compound" : "Isolation"}{exercise.is_unilateral ? " · Unilateral" : " · Bilateral"}</strong></div><div><span>Tracking</span><strong>{target(exercise)}</strong></div></div></Card>
      <Card className="report-card"><span className="eyebrow"><ShieldAlert size={13} style={{ display: "inline" }} /> Safety and muscles</span><p style={{ marginTop: 14 }}>{exercise.safety_notes}</p><span className="tiny">Primary muscles</span><div className="chip-grid compact-chips">{exercise.primary_muscles.map((muscle) => <span className="pill pill-success" key={muscle}>{muscle}</span>)}</div>{exercise.secondary_muscles.length > 0 && <><span className="tiny">Secondary muscles</span><div className="chip-grid compact-chips">{exercise.secondary_muscles.map((muscle) => <span className="pill" key={muscle}>{muscle}</span>)}</div></>}<span className="tiny">Suitable athlete types</span><div className="chip-grid compact-chips">{exercise.training_types.map((type) => <span className="pill" key={type}>{label(type)}</span>)}</div></Card>
    </div>

    <div className="section-title"><h2>Program prescriptions</h2><span className="tiny">{usage.total} appearances across normalized split templates</span></div>
    {usage.items.length ? <Card className="table-card"><div className="set-table-wrap"><table className="template-table"><thead><tr><th>Split</th><th>Training day</th><th>Prescription</th><th>RIR</th><th>Rest</th><th>Progression</th></tr></thead><tbody>{usage.items.map((item) => <tr key={item.prescription_id}><td><strong>{item.split_name}</strong><small>{item.days_per_week} days/week</small></td><td><strong>{item.day_name}</strong><small>{item.day_focus}</small></td><td>{item.sets} × {item.rep_min}–{item.rep_max}{item.optional ? " · optional" : ""}</td><td>{item.target_rir}</td><td>{item.rest_seconds}s</td><td>{item.progression_rule_id}</td></tr>)}</tbody></table></div>{usage.total > usage.items.length && <p className="tiny table-note">Showing the first {usage.items.length} of {usage.total} prescriptions.</p>}</Card> : <Card className="empty-state"><Sparkles size={22} /><h3>Catalogue-only movement</h3><p>This exercise is available for substitutions and custom programming but is not a default template prescription.</p></Card>}

    {substitutions.length > 0 && <><div className="section-title"><h2>Smart substitutions</h2><span className="tiny">Preserves movement intent</span></div><div className="plan-grid">{substitutions.map((group) => <Card className="day-card" key={group.group_id}><span className="eyebrow"><GitCompareArrows size={13} style={{ display: "inline" }} /> {group.group_id}</span><h3>{group.name}</h3><p className="tiny">{group.logic}</p><div className="substitution-list">{group.exercises.map((candidate) => <Link href={`/exercises/${candidate.id}`} key={candidate.id}><span><strong>{candidate.name}</strong><small>{candidate.equipment_display} · {label(candidate.difficulty)}</small></span><ArrowRight size={14} /></Link>)}</div></Card>)}</div></>}

    {progressionRules.length > 0 && <><div className="section-title"><h2>Progression logic</h2><span className="tiny">Research-informed rules used by templates</span></div><div className="report-grid">{progressionRules.map((rule) => <Card className="report-card" key={rule.id}><span className="eyebrow">{rule.id}</span><h3>{rule.name}</h3><div className="rule-steps"><div><span>Trigger</span><p>{rule.trigger}</p></div><div><span>Next action</span><p>{rule.action}</p></div><div><span>If performance regresses</span><p>{rule.regression}</p></div></div><span className="pill"><Clock3 size={13} /> {rule.applies_to}</span></Card>)}</div></>}
  </>;
}
