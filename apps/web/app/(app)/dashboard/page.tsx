"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, Droplets, Dumbbell, Gauge, Plus, Sparkles, Trophy } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button, Card, EmptyState, ErrorState, LoadingState, MetricCard } from "@/components/primitives";
import { api, formatNumber, todayIso } from "@/lib/api";

type Dashboard = {
  user: { first_name: string; full_name: string; experience_level: string | null };
  date: string;
  metrics: { weight_kg: number | null; water_target_ml: number | null; workout_streak: number };
  workout: { id: string; title: string; focus: string[]; scheduled_date: string; estimated_minutes: number; exercises: Array<{ name: string; sets: number; rep_min: number | null; rep_max: number | null; target_seconds: number | null }> } | null;
  nutrition: { totals: { energy_kcal: number; protein_g: number; carb_g: number; fat_g: number }; targets: { energy_kcal: number; protein_g: number; carb_g: number; fat_g: number; water_ml: number }; water_ml: number };
  habits: Array<{ id: string; name: string; derived: boolean; completed: boolean; streak: number }>;
  readiness: { score: number; explanation: string[] } | null;
  recent_prs: Array<{ exercise: string; type: string; value: number; achieved_at: string }>;
  recommendations: Array<{ id: string; type: string; explanation: string; confidence: number }>;
};

function greeting() { const hour = new Date().getHours(); return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening"; }

export default function DashboardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const today = todayIso();
  const dashboard = useQuery({ queryKey: ["dashboard", today], queryFn: () => api<Dashboard>(`/dashboard/today?local_date=${today}`) });
  const water = useMutation({ mutationFn: (amount_ml: number) => api("/water", { method: "POST", body: JSON.stringify({ amount_ml, local_date: today, client_operation_id: crypto.randomUUID() }) }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard", today] }) });
  const startWorkout = useMutation({ mutationFn: (program_day_id: string) => api<{ session_id: string }>("/workouts", { method: "POST", body: JSON.stringify({ program_day_id }) }), onSuccess: (result) => router.push(`/workouts/session/${result.session_id}`) });
  const toggleHabit = useMutation({ mutationFn: ({ id, completed }: { id: string; completed: boolean }) => api(`/habits/${id}/days/${today}`, { method: "PUT", body: JSON.stringify({ value: completed ? 0 : 1, completed: !completed }) }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard", today] }) });
  if (dashboard.isLoading) return <LoadingState label="Building today’s command center…" />;
  if (dashboard.isError || !dashboard.data) return <ErrorState message={dashboard.error?.message} onRetry={() => dashboard.refetch()} />;
  const data = dashboard.data;
  const caloriePercent = Math.min(100, Math.round((data.nutrition.totals.energy_kcal / data.nutrition.targets.energy_kcal) * 100));
  const waterPercent = Math.min(100, Math.round((data.nutrition.water_ml / data.nutrition.targets.water_ml) * 100));
  return <>
    <header className="page-head"><div><h1>{greeting()}, {data.user.first_name}! <span aria-hidden="true">👋</span></h1><p>{data.workout ? "Your next training session is ready." : "Log a baseline action to start building your week."}</p></div><div className="head-actions"><Link href="/progress"><Button variant="secondary">View progress</Button></Link></div></header>
    <section className="grid metric-grid">
      <MetricCard label="Latest weight" value={formatNumber(data.metrics.weight_kg)} unit="kg" note={data.metrics.weight_kg == null ? "Add a measurement" : "From your recorded history"} />
      <MetricCard label="Water intake" value={formatNumber(data.nutrition.water_ml / 1000)} unit={`/ ${formatNumber(data.nutrition.targets.water_ml / 1000)} L`} note={`${waterPercent}% of today’s target`} accent="blue" />
      <MetricCard label="Workout streak" value={data.metrics.workout_streak} unit="days" note="Schedule-aware consistency" accent="pink" />
      <MetricCard label="Readiness" value={data.readiness?.score ?? "—"} unit={data.readiness ? "/ 100" : ""} note={data.readiness?.explanation[0] ?? "Optional 30-second check-in"} accent="orange" />
    </section>
    <section className="grid dashboard-grid">
      <div className="dashboard-stack">
        <div className="section-title"><h2>Next workout</h2><Link href="/workouts">Full program <ArrowRight size={13} /></Link></div>
        {data.workout ? <Card className="workout-card"><div className="workout-card-head"><div><span className="eyebrow">Day plan · {data.workout.estimated_minutes} min</span><h3>{data.workout.title}</h3><span className="focus-list">{data.workout.focus.join(" · ")}</span></div><span className="pill"><Dumbbell size={14} /> {data.workout.exercises.length} exercises</span></div><div className="exercise-preview">{data.workout.exercises.slice(0, 5).map((exercise, index) => <div className="exercise-preview-row" key={exercise.name}><span><i className="exercise-number">{index + 1}</i>{exercise.name}</span><small>{exercise.target_seconds ? `${exercise.sets} × ${exercise.target_seconds}s` : `${exercise.sets} × ${exercise.rep_min}–${exercise.rep_max}`}</small></div>)}</div><Button className="button-wide" disabled={startWorkout.isPending} onClick={() => startWorkout.mutate(data.workout!.id)}>{startWorkout.isPending ? "Opening session…" : "Start workout"} <ArrowRight size={17} /></Button></Card> : <EmptyState icon={<Dumbbell />} title="No active workout" message="Generate a program after completing your training profile." action={<Link href="/workouts"><Button>Open workouts</Button></Link>} />}
        <div className="section-title"><h2>Recent progress</h2><Link href="/progress">Open reports</Link></div>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))" }}>
          <Card className="card-pad"><span className="eyebrow"><Trophy size={13} style={{ display: "inline" }} /> Recent PRs</span>{data.recent_prs.length ? <ul className="report-list">{data.recent_prs.map((pr) => <li key={`${pr.exercise}-${pr.achieved_at}`}><span>{pr.exercise}</span><strong>{formatNumber(pr.value)} kg</strong></li>)}</ul> : <p className="tiny" style={{ marginTop: 18 }}>Complete workouts to build your personal-record timeline.</p>}</Card>
          <Card className="card-pad"><span className="eyebrow"><Sparkles size={13} style={{ display: "inline" }} /> Next recommendation</span><p className="tiny" style={{ marginTop: 18 }}>{data.recommendations[0]?.explanation ?? "More completed sets will unlock evidence-based recommendations."}</p></Card>
        </div>
      </div>
      <aside className="dashboard-stack">
        <div className="section-title"><h2>Fuel today</h2><Link href="/nutrition">Details</Link></div>
        <Card className="macro-card"><div className="macro-summary"><div className="ring" style={{ "--value": `${caloriePercent}%` } as React.CSSProperties}><strong>{caloriePercent}%</strong></div><div><strong style={{ fontSize: "1.15rem" }}>{formatNumber(data.nutrition.totals.energy_kcal, 0)} <small className="tiny">/ {formatNumber(data.nutrition.targets.energy_kcal, 0)} kcal</small></strong><div className="macro-list" style={{ marginTop: 16 }}>{[["Protein", data.nutrition.totals.protein_g, data.nutrition.targets.protein_g], ["Carbs", data.nutrition.totals.carb_g, data.nutrition.targets.carb_g], ["Fat", data.nutrition.totals.fat_g, data.nutrition.targets.fat_g]].map(([label, value, target]) => <div className="macro-row" key={String(label)}><span>{label}</span><strong>{formatNumber(Number(value), 0)} / {target}g</strong></div>)}</div></div></div></Card>
        <Card className="water-card"><div className="water-head"><div><span className="eyebrow"><Droplets size={13} style={{ display: "inline" }} /> Hydration</span><strong style={{ display: "block", marginTop: 6 }}>{formatNumber(data.nutrition.water_ml / 1000)} / {formatNumber(data.nutrition.targets.water_ml / 1000)} L</strong></div><span className="pill pill-success">{waterPercent}%</span></div><div className="progress-track" style={{ marginBottom: 15 }}><span style={{ width: `${waterPercent}%` }} /></div><div className="water-quick"><Button variant="secondary" disabled={water.isPending} onClick={() => water.mutate(250)}><Plus size={14} />250 ml</Button><Button variant="secondary" disabled={water.isPending} onClick={() => water.mutate(500)}><Plus size={14} />500 ml</Button></div></Card>
        <div className="section-title"><h2>Today’s habits</h2><Link href="/habits">Month grid</Link></div>
        <div className="habit-list">{data.habits.map((habit) => <button className="habit-item" key={habit.id} disabled={habit.derived || toggleHabit.isPending} onClick={() => toggleHabit.mutate({ id: habit.id, completed: habit.completed })}><span>{habit.name}</span><span className={`habit-check ${habit.completed ? "done" : ""}`}>{habit.completed && <Check size={15} />}</span></button>)}{data.habits.length === 0 && <Card className="card-pad"><p className="tiny">No habits configured yet.</p></Card>}</div>
        {!data.readiness && <Link href="/progress#readiness"><Button variant="secondary" className="button-wide"><Gauge size={16} /> Add readiness check-in</Button></Link>}
      </aside>
    </section>
  </>;
}
