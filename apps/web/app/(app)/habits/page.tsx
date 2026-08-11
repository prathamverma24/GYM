"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronLeft, ChevronRight, Flame, Plus, SlidersHorizontal } from "lucide-react";
import { FormEvent, useState } from "react";

import { Button, Card, ErrorState, LoadingState, MetricCard } from "@/components/primitives";
import { api, todayIso } from "@/lib/api";

type HabitRow = { id: string; name: string; category: string; measurement_type: string; target_value: number; target_unit: string | null; schedule: Record<string, unknown>; active: boolean; derived_source: string | null; streak: { current: number; best: number }; days: Record<string, { value: number; completed: boolean }>; scheduled_days: string[] };
type HabitGrid = { month: string; dates: string[]; rows: HabitRow[] };

function monthKey(date: Date) { return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`; }
function shiftMonth(value: string, amount: number) { const [year, month] = value.split("-").map(Number); return monthKey(new Date(year, month - 1 + amount, 1)); }

export default function HabitsPage() {
  const [month, setMonth] = useState(monthKey(new Date())); const [showCreate, setShowCreate] = useState(false); const [name, setName] = useState(""); const queryClient = useQueryClient();
  const grid = useQuery({ queryKey: ["habit-grid", month], queryFn: () => api<HabitGrid>(`/habit-grid?month=${month}`) });
  const toggle = useMutation({ mutationFn: ({ habit, day }: { habit: HabitRow; day: string }) => { const current = habit.days[day]?.completed ?? false; return api(`/habits/${habit.id}/days/${day}`, { method: "PUT", body: JSON.stringify({ value: current ? 0 : 1, completed: !current }) }); }, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["habit-grid", month] }) });
  const create = useMutation({ mutationFn: () => api("/habits", { method: "POST", body: JSON.stringify({ name, category: "wellness", measurement_type: "boolean", target_value: 1, schedule: { frequency: "daily" } }) }), onSuccess: () => { setName(""); setShowCreate(false); queryClient.invalidateQueries({ queryKey: ["habit-grid", month] }); } });
  function submit(event: FormEvent) { event.preventDefault(); if (name.trim()) create.mutate(); }
  if (grid.isLoading) return <LoadingState label="Building your month matrix…" />;
  if (grid.isError || !grid.data) return <ErrorState message={grid.error?.message} onRetry={() => grid.refetch()} />;
  const data = grid.data; const completions = data.rows.reduce((count, row) => count + Object.values(row.days).filter((day) => day.completed).length, 0); const scheduled = data.rows.reduce((count, row) => count + row.scheduled_days.filter((day) => day <= todayIso()).length, 0); const best = Math.max(0, ...data.rows.map((row) => row.streak.current));
  return <><header className="page-head"><div><span className="eyebrow">Consistency system</span><h1>Habit tracker</h1><p>Rows are your habits; columns are athlete-local calendar days. Planned rest never breaks a schedule-aware streak.</p></div><div className="head-actions"><Button variant="secondary" onClick={() => setShowCreate((value) => !value)}><Plus size={16} /> New habit</Button></div></header>
    {showCreate && <Card className="card-pad" style={{ marginBottom: 16 }}><form className="form-row" onSubmit={submit}><label className="field"><span>Habit name</span><input className="input" required value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Mobility 10 minutes" /></label><div style={{ alignSelf: "end" }}><Button disabled={create.isPending}>{create.isPending ? "Creating…" : "Add daily habit"}</Button></div></form></Card>}
    <section className="grid metric-grid" style={{ marginBottom: 16 }}><MetricCard label="Current streak" value={best} unit="days" accent="pink" note="Best active habit" /><MetricCard label="Month completion" value={scheduled ? Math.round(completions / scheduled * 100) : 0} unit="%" accent="violet" note={`${completions} completed cells`} /><MetricCard label="Active habits" value={data.rows.length} accent="blue" note="Derived habits update from logs" /><MetricCard label="Month" value={new Date(`${month}-02`).toLocaleString("en", { month: "short" })} unit={month.slice(0, 4)} accent="orange" /></section>
    <Card className="habit-grid-card"><div style={{ padding: 16, display: "flex", justifyContent: "space-between", alignItems: "center", position: "sticky", left: 0 }}><Button variant="ghost" onClick={() => setMonth(shiftMonth(month, -1))}><ChevronLeft size={16} /> Previous</Button><strong>{new Date(`${month}-02`).toLocaleString("en", { month: "long", year: "numeric" })}</strong><Button variant="ghost" disabled={month >= monthKey(new Date())} onClick={() => setMonth(shiftMonth(month, 1))}>Next <ChevronRight size={16} /></Button></div><table className="habit-table"><thead><tr><th className="habit-name">Habit</th>{data.dates.map((day) => <th key={day}><span>{new Date(`${day}T12:00:00`).toLocaleString("en", { weekday: "narrow" })}</span><br />{Number(day.slice(-2))}</th>)}</tr></thead><tbody>{data.rows.map((habit) => <tr key={habit.id}><th className="habit-name"><span>{habit.name}</span><span className="tiny" style={{ float: "right" }}><Flame size={11} style={{ display: "inline" }} /> {habit.streak.current}</span></th>{data.dates.map((day) => { const scheduledDay = habit.scheduled_days.includes(day); const completed = habit.days[day]?.completed; const future = day > todayIso(); return <td key={day}>{scheduledDay ? <button className={`habit-cell ${completed ? "done" : ""} ${habit.derived_source ? "readonly" : ""}`} aria-label={`${habit.name} ${day} ${completed ? "complete" : "incomplete"}`} disabled={Boolean(habit.derived_source) || future || toggle.isPending} onClick={() => toggle.mutate({ habit, day })}>{completed && <Check size={14} />}</button> : <span className="habit-cell unscheduled" aria-label="Not scheduled" />}</td>; })}</tr>)}</tbody></table>{data.rows.length === 0 && <div className="empty-state"><SlidersHorizontal size={24} /><h3>No habits yet</h3><p>Create a daily or scheduled habit to start your matrix.</p></div>}</Card>
  </>;
}

