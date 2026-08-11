"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CalendarDays, Check, Clock3, Dumbbell, Plus, RefreshCw, Settings2, Trash2, X } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { Button, Card, EmptyState, ErrorState, LoadingState } from "@/components/primitives";
import { api } from "@/lib/api";
import type { Program, ProgramDay } from "@/types/api";

type PlanTemplate = {
  id: string;
  name: string;
  approach_family: string;
  days_per_week: number;
  experience_min: string;
  experience_max: string;
  primary_goals: string[];
  athlete_types: string[];
  session_minutes: string;
  equipment_requirement: string;
  recovery_demand: string;
  description: string;
  recommended: boolean;
};

export default function WorkoutsPage() {
  const queryClient = useQueryClient();
  const [showPlans, setShowPlans] = useState(false);
  const [showAddDay, setShowAddDay] = useState(false);
  const [templateId, setTemplateId] = useState("");
  const [title, setTitle] = useState("");
  const [focus, setFocus] = useState("");
  const [scheduledDate, setScheduledDate] = useState("");
  const [minutes, setMinutes] = useState(60);

  const programQuery = useQuery({
    queryKey: ["active-program"],
    queryFn: () => api<{ program: Program | null }>("/programs/active"),
  });
  const templatesQuery = useQuery({
    queryKey: ["program-templates"],
    queryFn: () => api<{ items: PlanTemplate[]; total: number }>("/programs/templates"),
    enabled: showPlans,
  });

  const refreshProgram = () => queryClient.invalidateQueries({ queryKey: ["active-program"] });
  const generate = useMutation({
    mutationFn: () => api("/programs/generate", { method: "POST" }),
    onSuccess: refreshProgram,
  });
  const activate = useMutation({
    mutationFn: (splitId: string) => api(`/programs/templates/${splitId}/activate`, { method: "POST" }),
    onSuccess: async () => {
      setShowPlans(false);
      await refreshProgram();
    },
  });
  const addWorkout = useMutation({
    mutationFn: ({ programId }: { programId: string }) => api(`/programs/${programId}/days`, {
      method: "POST",
      body: JSON.stringify({
        title,
        focus: focus.split(",").map((value) => value.trim()).filter(Boolean),
        scheduled_date: scheduledDate || null,
        estimated_minutes: minutes,
      }),
    }),
    onSuccess: async () => {
      setTitle("");
      setFocus("");
      setScheduledDate("");
      setShowAddDay(false);
      await refreshProgram();
    },
  });
  const deleteWorkout = useMutation({
    mutationFn: ({ programId, dayId }: { programId: string; dayId: string }) => api(`/programs/${programId}/days/${dayId}`, { method: "DELETE" }),
    onSuccess: refreshProgram,
  });
  const rescheduleWorkout = useMutation({
    mutationFn: ({ day, scheduledDate: nextDate }: { day: ProgramDay; scheduledDate: string | null }) => api(`/programs/${day.program_id}/days/${day.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        title: day.title,
        focus: day.focus,
        scheduled_date: nextDate,
        estimated_minutes: day.estimated_minutes,
      }),
    }),
    onSuccess: refreshProgram,
  });

  if (programQuery.isLoading) return <LoadingState label="Loading your training block…" />;
  if (programQuery.isError) return <ErrorState message={programQuery.error.message} onRetry={() => programQuery.refetch()} />;
  const program = programQuery.data?.program;
  const templates = templatesQuery.data?.items ?? [];
  const selectedTemplate = templates.find((item) => item.id === templateId)
    ?? templates.find((item) => item.recommended)
    ?? templates[0];
  const actionError = generate.error ?? activate.error ?? addWorkout.error ?? deleteWorkout.error ?? rescheduleWorkout.error;

  function submitDay(event: FormEvent) {
    event.preventDefault();
    if (program && title.trim()) addWorkout.mutate({ programId: program.id });
  }

  return <>
    <header className="page-head">
      <div>
        <span className="eyebrow">Training program</span>
        <h1>{program?.name ?? "Your training week"}</h1>
        <p>{program ? `Versioned with ${program.generator_version}. Plan edits never change your workout history.` : "Complete onboarding or generate a fresh evidence-based program."}</p>
      </div>
      <div className="head-actions">
        {program && <Button variant="secondary" onClick={() => { setShowPlans((value) => !value); setShowAddDay(false); }}><Settings2 size={16} /> Change plan</Button>}
        {program && <Button onClick={() => { setShowAddDay((value) => !value); setShowPlans(false); }}><Plus size={16} /> Add workout</Button>}
        <Button variant="ghost" disabled={generate.isPending} onClick={() => generate.mutate()}><RefreshCw size={16} />{generate.isPending ? "Generating…" : "Recalculate"}</Button>
      </div>
    </header>

    {actionError && <div className="inline-alert" role="alert">{actionError.message}</div>}

    {program && showPlans && <Card className="plan-editor-panel">
      <div className="editor-panel-head">
        <div><span className="eyebrow">Choose a training structure</span><h2>Change workout plan</h2><p>Your current version is archived, so existing session history stays intact.</p></div>
        <button className="icon-button" aria-label="Close plan chooser" onClick={() => setShowPlans(false)}><X size={17} /></button>
      </div>
      {templatesQuery.isLoading ? <LoadingState label="Loading 30 workout plans…" /> : templatesQuery.isError ? <ErrorState message={templatesQuery.error.message} onRetry={() => templatesQuery.refetch()} /> : selectedTemplate && <div className="template-picker">
        <label className="field"><span>Workout plan</span><select className="select" value={selectedTemplate.id} onChange={(event) => setTemplateId(event.target.value)}>{templates.map((item) => <option key={item.id} value={item.id}>{item.recommended ? "Recommended · " : ""}{item.name}</option>)}</select></label>
        <div className="template-preview">
          <div><span className="pill">{selectedTemplate.days_per_week} days/week</span>{selectedTemplate.recommended && <span className="pill pill-success">Recommended</span>}</div>
          <h3>{selectedTemplate.name}</h3>
          <p>{selectedTemplate.description}</p>
          <div className="template-facts"><span>{selectedTemplate.session_minutes} min/session</span><span>{selectedTemplate.experience_min}–{selectedTemplate.experience_max}</span><span>{selectedTemplate.equipment_requirement}</span><span>{selectedTemplate.recovery_demand} recovery</span></div>
        </div>
        <Button disabled={activate.isPending} onClick={() => activate.mutate(selectedTemplate.id)}>{activate.isPending ? "Switching…" : "Use this plan"}<ArrowRight size={16} /></Button>
      </div>}
    </Card>}

    {program && showAddDay && <Card className="plan-editor-panel">
      <div className="editor-panel-head">
        <div><span className="eyebrow">Custom workout</span><h2>Add a workout day</h2><p>Create the day first, then add exercises from the full library.</p></div>
        <button className="icon-button" aria-label="Close add workout form" onClick={() => setShowAddDay(false)}><X size={17} /></button>
      </div>
      <form className="day-form" onSubmit={submitDay}>
        <label className="field"><span>Workout name</span><input className="input" required minLength={2} maxLength={100} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Example: Upper body strength" /></label>
        <label className="field"><span>Focus areas</span><input className="input" value={focus} onChange={(event) => setFocus(event.target.value)} placeholder="Chest, Back, Shoulders" /></label>
        <label className="field"><span>Workout date</span><input className="input" type="date" value={scheduledDate} onChange={(event) => setScheduledDate(event.target.value)} /></label>
        <label className="field"><span>Minutes</span><input className="input" type="number" min={15} max={240} value={minutes} onChange={(event) => setMinutes(Number(event.target.value))} /></label>
        <Button type="submit" disabled={addWorkout.isPending || !title.trim()}>{addWorkout.isPending ? "Adding…" : "Add workout"}</Button>
      </form>
    </Card>}

    {program ? <>
      <Card className="card-pad plan-rationale">
        <span className="eyebrow">Why this plan</span>
        <ul className="report-list">{program.rationale.map((reason) => <li key={reason}><span>{reason}</span><span>✓</span></li>)}</ul>
      </Card>
      <div className="plan-grid">{program.days.map((day) => <Card className="day-card" key={day.id}>
        <div className="day-card-heading"><span className="pill"><CalendarDays size={13} /> Day {day.day_index}</span><button className="icon-button danger-icon" aria-label={`Delete ${day.title}`} disabled={deleteWorkout.isPending || program.days.length === 1} onClick={() => { if (window.confirm(`Remove ${day.title} from your plan? Your workout history will stay available.`)) deleteWorkout.mutate({ programId: program.id, dayId: day.id }); }}><Trash2 size={15} /></button></div>
        <h3>{day.title}</h3>
        <span className="focus-list">{day.focus.join(" · ") || "Custom focus"}</span>
        <ScheduleDateEditor day={day} pending={rescheduleWorkout.isPending} onSave={(nextDate) => rescheduleWorkout.mutate({ day, scheduledDate: nextDate })} />
        {day.exercises.length ? <ul className="day-card-list">{day.exercises.slice(0, 5).map((item) => <li key={item.id}><span>{item.exercise.name}</span><span>{item.target_sets} × {item.target_seconds ? `${item.target_seconds}s` : `${item.rep_min}–${item.rep_max}`}</span></li>)}</ul> : <div className="empty-day-note">No exercises yet. Open the workout to add your first movement.</div>}
        <span className="tiny day-duration"><Clock3 size={13} /> About {day.estimated_minutes} minutes</span>
        <Link href={`/workouts/day/${day.id}`}><Button variant="secondary" className="button-wide">Manage day <ArrowRight size={15} /></Button></Link>
      </Card>)}</div>
    </> : <EmptyState icon={<Dumbbell />} title="No program yet" message="Finish your athlete profile to generate an equipment-aware first week." action={<Link href="/onboarding"><Button>Complete setup</Button></Link>} />}
  </>;
}

function ScheduleDateEditor({ day, pending, onSave }: { day: ProgramDay; pending: boolean; onSave: (value: string | null) => void }) {
  const [value, setValue] = useState(day.scheduled_date ?? "");
  const changed = value !== (day.scheduled_date ?? "");
  const readableDate = value
    ? new Date(`${value}T12:00:00`).toLocaleDateString("en", { weekday: "short", month: "short", day: "numeric" })
    : "Flexible day";

  return <div className="day-date-editor">
    <div className="day-date-copy"><CalendarDays size={15} /><span><strong>Workout date</strong><small>{readableDate}</small></span></div>
    <div className="day-date-actions">
      <input className="date-input" aria-label={`Workout date for ${day.title}`} type="date" value={value} onChange={(event) => setValue(event.target.value)} />
      <button type="button" className="date-save" disabled={!changed || pending} onClick={() => onSave(value || null)}>{pending ? <RefreshCw size={14} /> : <Check size={14} />}<span>{pending ? "Saving" : "Save"}</span></button>
    </div>
  </div>;
}
