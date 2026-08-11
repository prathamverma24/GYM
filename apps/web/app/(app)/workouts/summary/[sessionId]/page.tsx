"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Dumbbell, Gauge, Repeat2, Trophy } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { Button, Card, ErrorState, LoadingState, MetricCard } from "@/components/primitives";
import { api, formatNumber } from "@/lib/api";
import type { WorkoutSession } from "@/types/api";

export default function WorkoutSummaryPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const sessionQuery = useQuery({ queryKey: ["workout", sessionId], queryFn: () => api<{ session: WorkoutSession }>(`/workouts/${sessionId}`) });
  const recommendations = useQuery({ queryKey: ["recommendations"], queryFn: () => api<{ items: Array<{ id: string; decision_type: string; explanation: string; confidence: number }> }>("/recommendations") });
  if (sessionQuery.isLoading) return <LoadingState label="Calculating your workout summary…" />;
  if (sessionQuery.isError || !sessionQuery.data) return <ErrorState message={sessionQuery.error?.message} />;
  const session = sessionQuery.data.session; const duration = session.completed_at ? Math.max(1, Math.round((new Date(session.completed_at).getTime() - new Date(session.started_at).getTime()) / 60000)) : 0; const completedSets = session.sets.filter((item) => item.completed); const reps = completedSets.reduce((total, item) => total + (item.reps ?? 0), 0);
  return <><header className="page-head"><div><span className="eyebrow"><CheckCircle2 size={14} style={{ display: "inline" }} /> Session complete</span><h1>{session.day.title} is in the books.</h1><p>Your performed sets are durable and the progression engine has reviewed this exposure.</p></div><div className="head-actions"><Link href="/workouts"><Button variant="secondary">Back to program</Button></Link><Link href="/dashboard"><Button>Dashboard</Button></Link></div></header><section className="grid metric-grid"><MetricCard label="Total volume" value={formatNumber(session.total_volume_kg, 0)} unit="kg" /><MetricCard label="Duration" value={duration} unit="min" accent="blue" /><MetricCard label="Sets" value={completedSets.length} unit="completed" accent="pink" /><MetricCard label="Reps" value={reps} unit="total" accent="orange" /></section><div className="report-grid" style={{ marginTop: 18 }}><Card className="report-card"><span className="eyebrow"><Dumbbell size={13} style={{ display: "inline" }} /> Work completed</span><ul className="report-list">{session.day.exercises.map((item) => <li key={item.id}><span>{item.exercise.name}</span><strong>{completedSets.filter((set) => set.prescribed_exercise_id === item.id).length} sets</strong></li>)}</ul></Card><Card className="report-card"><span className="eyebrow"><Gauge size={13} style={{ display: "inline" }} /> Next exposure</span>{recommendations.data?.items.slice(0, 3).map((item) => <div key={item.id} style={{ marginTop: 16 }}><span className={`pill ${item.decision_type === "increase_load" ? "pill-success" : ""}`}><Repeat2 size={13} /> {item.decision_type.replaceAll("_", " ")}</span><p className="tiny" style={{ margin: "9px 0" }}>{item.explanation}</p><small className="tiny">Confidence {Math.round(item.confidence * 100)}%</small></div>)}{!recommendations.data?.items.length && <p className="tiny" style={{ marginTop: 16 }}><Trophy size={14} style={{ display: "inline" }} /> One comparable exposure is needed before load progression.</p>}</Card></div></>;
}

