"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarDays, ChevronRight } from "lucide-react";
import Link from "next/link";

import { Card, EmptyState, ErrorState, LoadingState } from "@/components/primitives";
import { api } from "@/lib/api";
import type { Program } from "@/types/api";

export default function CalendarPage() {
  const program = useQuery({ queryKey: ["active-program"], queryFn: () => api<{ program: Program | null }>("/programs/active") });
  if (program.isLoading) return <LoadingState label="Opening your schedule…" />; if (program.isError) return <ErrorState message={program.error.message} />;
  return <><header className="page-head"><div><span className="eyebrow">Training schedule</span><h1>Calendar</h1><p>Scheduled sessions use athlete-local dates. Missed volume is never compressed blindly into tomorrow.</p></div></header>{program.data?.program ? <div className="day-view-list">{program.data.program.days.map((day) => <Link href={`/workouts/day/${day.id}`} key={day.id}><Card className="exercise-row"><span className="exercise-order"><CalendarDays size={16} /></span><div><h3>{day.title}</h3><p>{day.scheduled_date ? new Date(`${day.scheduled_date}T12:00:00`).toLocaleDateString("en", { weekday: "long", month: "long", day: "numeric" }) : "Flexible day"} · {day.focus.join(", ")}</p></div><ChevronRight size={18} /></Card></Link>)}</div> : <EmptyState icon={<CalendarDays />} title="No scheduled program" message="Generate a training plan to populate your calendar." />}</>;
}

