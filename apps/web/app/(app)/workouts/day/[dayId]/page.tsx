"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Clock3, History, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { Button, Card, ErrorState, LoadingState } from "@/components/primitives";
import { api, formatNumber } from "@/lib/api";
import type { Exercise, Prescription, ProgramDay } from "@/types/api";

type EditValues = {
  exercise_id: string;
  exercise_name: string;
  target_sets: number;
  rep_min: number | null;
  rep_max: number | null;
  target_seconds: number | null;
  rest_seconds: number;
  target_rir: number | null;
  notes: string | null;
};

type EditResult = { program_id: string; day_id: string; prescribed_exercise_id?: string };

export default function WorkoutDayPage() {
  const { dayId } = useParams<{ dayId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [showDayEdit, setShowDayEdit] = useState(false);
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editSearch, setEditSearch] = useState("");
  const [editValues, setEditValues] = useState<EditValues | null>(null);

  const dayQuery = useQuery({
    queryKey: ["training-day", dayId],
    queryFn: () => api<{ day: ProgramDay }>(`/training/days/${dayId}`),
  });
  const exerciseQuery = useQuery({
    queryKey: ["plan-exercise-search", search],
    queryFn: () => api<{ items: Exercise[] }>(`/exercises?q=${encodeURIComponent(search)}&page_size=12`),
    enabled: showAdd,
  });
  const replacementQuery = useQuery({
    queryKey: ["plan-exercise-replacement", editSearch],
    queryFn: () => api<{ items: Exercise[] }>(`/exercises?q=${encodeURIComponent(editSearch)}&page_size=12`),
    enabled: Boolean(editingId && editSearch.trim()),
  });

  const finishEdit = async (result: EditResult) => {
    setShowAdd(false);
    setEditingId(null);
    setEditValues(null);
    await queryClient.invalidateQueries({ queryKey: ["active-program"] });
    router.replace(`/workouts/day/${result.day_id}`);
  };

  const start = useMutation({
    mutationFn: () => api<{ session_id: string }>("/workouts", { method: "POST", body: JSON.stringify({ program_day_id: dayId }) }),
    onSuccess: (result) => router.push(`/workouts/session/${result.session_id}`),
  });
  const addExercise = useMutation({
    mutationFn: ({ day, exerciseId }: { day: ProgramDay; exerciseId: string }) => api<EditResult>(`/programs/${day.program_id}/days/${day.id}/exercises`, { method: "POST", body: JSON.stringify({ exercise_id: exerciseId }) }),
    onSuccess: finishEdit,
  });
  const updateExercise = useMutation({
    mutationFn: ({ day, itemId, values, orderIndex }: { day: ProgramDay; itemId: string; values: EditValues; orderIndex?: number }) => api<EditResult>(`/programs/${day.program_id}/days/${day.id}/exercises/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({
        exercise_id: values.exercise_id,
        order_index: orderIndex,
        target_sets: values.target_sets,
        rep_min: values.rep_min,
        rep_max: values.rep_max,
        target_seconds: values.target_seconds,
        rest_seconds: values.rest_seconds,
        target_rir: values.target_rir,
        notes: values.notes,
      }),
    }),
    onSuccess: finishEdit,
  });
  const deleteExercise = useMutation({
    mutationFn: ({ day, itemId }: { day: ProgramDay; itemId: string }) => api<EditResult>(`/programs/${day.program_id}/days/${day.id}/exercises/${itemId}`, { method: "DELETE" }),
    onSuccess: finishEdit,
  });
  const updateDay = useMutation({
    mutationFn: ({ day, title, focus, minutes }: { day: ProgramDay; title: string; focus: string; minutes: number }) => api<EditResult>(`/programs/${day.program_id}/days/${day.id}`, {
      method: "PATCH",
      body: JSON.stringify({ title, focus: focus.split(",").map((value) => value.trim()).filter(Boolean), estimated_minutes: minutes }),
    }),
    onSuccess: (result) => { setShowDayEdit(false); finishEdit(result); },
  });

  if (dayQuery.isLoading) return <LoadingState label="Preparing your training day…" />;
  if (dayQuery.isError || !dayQuery.data) return <ErrorState message={dayQuery.error?.message} onRetry={() => dayQuery.refetch()} />;
  const day = dayQuery.data.day;
  const actionError = start.error ?? addExercise.error ?? updateExercise.error ?? deleteExercise.error ?? updateDay.error;

  function beginEdit(item: Prescription) {
    setEditingId(item.id);
    setEditSearch("");
    setEditValues({
      exercise_id: item.exercise.id,
      exercise_name: item.exercise.name,
      target_sets: item.target_sets,
      rep_min: item.rep_min,
      rep_max: item.rep_max,
      target_seconds: item.target_seconds,
      rest_seconds: item.rest_seconds,
      target_rir: item.target_rir,
      notes: item.notes,
    });
  }

  function valuesFor(item: Prescription): EditValues {
    return {
      exercise_id: item.exercise.id,
      exercise_name: item.exercise.name,
      target_sets: item.target_sets,
      rep_min: item.rep_min,
      rep_max: item.rep_max,
      target_seconds: item.target_seconds,
      rest_seconds: item.rest_seconds,
      target_rir: item.target_rir,
      notes: item.notes,
    };
  }

  return <>
    <header className="page-head">
      <div><Link className="tiny" href="/workouts"><ArrowLeft size={13} style={{ display: "inline" }} /> Program</Link><h1 style={{ marginTop: 12 }}>{day.title}</h1><p>{day.focus.join(" · ") || "Custom workout"} · about {day.estimated_minutes} minutes</p></div>
      <div className="head-actions">
        <Button variant="secondary" onClick={() => { setShowDayEdit((value) => !value); setShowAdd(false); }}><Pencil size={15} /> Edit day</Button>
        <Button variant="secondary" onClick={() => { setShowAdd((value) => !value); setShowDayEdit(false); }}><Plus size={16} /> Add exercise</Button>
        <Button disabled={start.isPending || day.exercises.length === 0} onClick={() => start.mutate()}>{start.isPending ? "Opening…" : "Start workout"}<ArrowRight size={17} /></Button>
      </div>
    </header>

    {actionError && <div className="inline-alert" role="alert">{actionError.message}</div>}

    {showDayEdit && <DayEditor day={day} pending={updateDay.isPending} onClose={() => setShowDayEdit(false)} onSave={(values) => updateDay.mutate({ day, ...values })} />}

    {showAdd && <Card className="plan-editor-panel">
      <div className="editor-panel-head"><div><span className="eyebrow">Exercise library</span><h2>Add an exercise</h2><p>Search all 151 movements. Default sets, reps and rest can be edited after adding.</p></div><button className="icon-button" aria-label="Close exercise search" onClick={() => setShowAdd(false)}><X size={17} /></button></div>
      <div className="search-input-wrap plan-exercise-search"><Search size={17} /><input className="input" aria-label="Search exercises to add" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by name, muscle or equipment" /></div>
      {exerciseQuery.isLoading ? <LoadingState label="Searching exercises…" /> : <div className="exercise-option-grid">{exerciseQuery.data?.items.map((exercise) => {
        const alreadyAdded = day.exercises.some((item) => item.exercise.id === exercise.id);
        return <button type="button" className="exercise-option" key={exercise.id} disabled={alreadyAdded || addExercise.isPending} onClick={() => addExercise.mutate({ day, exerciseId: exercise.id })}><span><strong>{exercise.name}</strong><small>{exercise.category} · {exercise.equipment_display}</small></span><span>{alreadyAdded ? "Added" : <Plus size={15} />}</span></button>;
      })}</div>}
    </Card>}

    <div className="day-view-list">{day.exercises.map((item, index) => <div key={item.id}>
      <Card className="exercise-row editable-exercise-row">
        <span className="exercise-order">{item.order_index}</span>
        <div><h3>{item.exercise.name}</h3><p>{item.exercise.primary_muscles.join(", ")} · rest {Math.floor(item.rest_seconds / 60)}:{String(item.rest_seconds % 60).padStart(2, "0")}</p>{item.previous.length ? <div className="previous-line"><History size={11} style={{ display: "inline" }} /> Previous: {item.previous.map((set) => `${formatNumber(set.load_kg)} kg × ${set.reps ?? "—"}`).join(" · ")}</div> : <div className="previous-line">No comparable session yet</div>}</div>
        <div className="target">{item.target_sets} × {item.target_seconds ? `${item.target_seconds}s` : `${item.rep_min}–${item.rep_max}`}<small className="tiny">RIR {item.target_rir ?? "—"}</small></div>
        <div className="exercise-edit-actions">
          <button className="icon-button" aria-label={`Move ${item.exercise.name} up`} disabled={index === 0 || updateExercise.isPending} onClick={() => updateExercise.mutate({ day, itemId: item.id, values: valuesFor(item), orderIndex: item.order_index - 1 })}><ArrowUp size={14} /></button>
          <button className="icon-button" aria-label={`Move ${item.exercise.name} down`} disabled={index === day.exercises.length - 1 || updateExercise.isPending} onClick={() => updateExercise.mutate({ day, itemId: item.id, values: valuesFor(item), orderIndex: item.order_index + 1 })}><ArrowDown size={14} /></button>
          <button className="icon-button" aria-label={`Edit ${item.exercise.name}`} onClick={() => editingId === item.id ? setEditingId(null) : beginEdit(item)}><Pencil size={14} /></button>
          <button className="icon-button danger-icon" aria-label={`Delete ${item.exercise.name}`} disabled={day.exercises.length === 1 || deleteExercise.isPending} onClick={() => { if (window.confirm(`Remove ${item.exercise.name} from this workout?`)) deleteExercise.mutate({ day, itemId: item.id }); }}><Trash2 size={14} /></button>
        </div>
      </Card>
      {editingId === item.id && editValues && <Card className="exercise-edit-form">
        <div className="editor-panel-head"><div><span className="eyebrow">Exercise settings</span><h3>{editValues.exercise_name}</h3></div><button className="icon-button" aria-label="Close exercise editor" onClick={() => setEditingId(null)}><X size={16} /></button></div>
        <div className="search-input-wrap"><Search size={16} /><input className="input" aria-label="Find a replacement exercise" value={editSearch} onChange={(event) => setEditSearch(event.target.value)} placeholder="Find a replacement movement" /></div>
        {editSearch.trim() && <div className="replacement-results">{replacementQuery.data?.items.map((exercise) => <button type="button" key={exercise.id} onClick={() => { setEditValues({ ...editValues, exercise_id: exercise.id, exercise_name: exercise.name }); setEditSearch(""); }}><span>{exercise.name}</span><small>{exercise.equipment_display}</small></button>)}</div>}
        <form className="prescription-form" onSubmit={(event) => { event.preventDefault(); updateExercise.mutate({ day, itemId: item.id, values: editValues }); }}>
          <NumberField label="Sets" value={editValues.target_sets} min={1} max={10} onChange={(value) => setEditValues({ ...editValues, target_sets: value ?? 1 })} />
          <NumberField label="Minimum reps" value={editValues.rep_min} min={1} max={1000} onChange={(value) => setEditValues({ ...editValues, rep_min: value })} />
          <NumberField label="Maximum reps" value={editValues.rep_max} min={1} max={1000} onChange={(value) => setEditValues({ ...editValues, rep_max: value })} />
          <NumberField label="Seconds" value={editValues.target_seconds} min={1} max={86400} onChange={(value) => setEditValues({ ...editValues, target_seconds: value })} />
          <NumberField label="Rest seconds" value={editValues.rest_seconds} min={0} max={1800} onChange={(value) => setEditValues({ ...editValues, rest_seconds: value ?? 0 })} />
          <NumberField label="Target RIR" value={editValues.target_rir} min={0} max={10} onChange={(value) => setEditValues({ ...editValues, target_rir: value })} />
          <label className="field prescription-notes"><span>Notes</span><input className="input" value={editValues.notes ?? ""} onChange={(event) => setEditValues({ ...editValues, notes: event.target.value || null })} /></label>
          <Button type="submit" disabled={updateExercise.isPending}>{updateExercise.isPending ? "Saving…" : "Save changes"}</Button>
        </form>
      </Card>}
    </div>)}</div>

    {!day.exercises.length && <Card className="empty-state"><h3>This workout is empty</h3><p>Add an exercise before starting the session.</p><Button onClick={() => setShowAdd(true)}><Plus size={15} /> Add first exercise</Button></Card>}
    <Card className="card-pad session-guidance"><span className="eyebrow"><Clock3 size={13} style={{ display: "inline" }} /> Session guidance</span><p className="tiny">Warm up for the first movement, leave the prescribed reps in reserve, and stop any set that causes sharp pain. Plan changes create a new version and do not rewrite saved sessions.</p></Card>
  </>;
}

function NumberField({ label, value, min, max, onChange }: { label: string; value: number | null; min: number; max: number; onChange: (value: number | null) => void }) {
  return <label className="field"><span>{label}</span><input className="input" type="number" min={min} max={max} value={value ?? ""} onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))} /></label>;
}

function DayEditor({ day, pending, onClose, onSave }: { day: ProgramDay; pending: boolean; onClose: () => void; onSave: (values: { title: string; focus: string; minutes: number }) => void }) {
  const [title, setTitle] = useState(day.title);
  const [focus, setFocus] = useState(day.focus.join(", "));
  const [minutes, setMinutes] = useState(day.estimated_minutes);
  function submit(event: FormEvent) {
    event.preventDefault();
    if (title.trim()) onSave({ title: title.trim(), focus, minutes });
  }
  return <Card className="plan-editor-panel"><div className="editor-panel-head"><div><span className="eyebrow">Workout details</span><h2>Edit workout day</h2></div><button className="icon-button" aria-label="Close day editor" onClick={onClose}><X size={17} /></button></div><form className="day-form" onSubmit={submit}><label className="field"><span>Workout name</span><input className="input" required value={title} onChange={(event) => setTitle(event.target.value)} /></label><label className="field"><span>Focus areas</span><input className="input" value={focus} onChange={(event) => setFocus(event.target.value)} /></label><label className="field"><span>Minutes</span><input className="input" type="number" min={15} max={240} value={minutes} onChange={(event) => setMinutes(Number(event.target.value))} /></label><Button type="submit" disabled={pending}>{pending ? "Saving…" : "Save day"}</Button></form></Card>;
}
