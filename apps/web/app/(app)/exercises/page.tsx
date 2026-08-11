"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Clock3, Dumbbell, Filter, Search, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Button, Card, EmptyState, ErrorState, LoadingState } from "@/components/primitives";
import { api } from "@/lib/api";
import type { Exercise } from "@/types/api";

type Facet = { value: string; count: number };
type ExerciseResults = {
  items: Exercise[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  facets: {
    categories: Facet[];
    equipment: Facet[];
    difficulties: Facet[];
    training_types: Facet[];
    tracking_metrics: Facet[];
  };
  dataset: { version: string; exercise_count: number; split_template_count: number; prescription_count: number };
};

function label(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function target(exercise: Exercise) {
  const range = `${exercise.default_rep_min}–${exercise.default_rep_max}`;
  if (exercise.tracking_metric === "seconds") return `${range} sec`;
  if (exercise.tracking_metric === "meters") return `${range} m`;
  if (exercise.tracking_metric === "minutes") return `${range} min`;
  return `${range} reps`;
}

export default function ExercisesPage() {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [trainingType, setTrainingType] = useState("");
  const [category, setCategory] = useState("");
  const [equipment, setEquipment] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [compound, setCompound] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const search = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "24" });
    if (debounced) params.set("q", debounced);
    if (trainingType) params.set("training_type", trainingType);
    if (category) params.set("category", category);
    if (equipment) params.set("equipment", equipment);
    if (difficulty) params.set("difficulty", difficulty);
    if (compound) params.set("compound", compound);
    return params.toString();
  }, [category, compound, debounced, difficulty, equipment, page, trainingType]);

  const exercises = useQuery({
    queryKey: ["exercises", search],
    queryFn: () => api<ExerciseResults>(`/exercises?${search}`),
  });
  const data = exercises.data;
  const hasFilters = Boolean(query || trainingType || category || equipment || difficulty || compound);
  function clearFilters() {
    setQuery("");
    setDebounced("");
    setTrainingType("");
    setCategory("");
    setEquipment("");
    setDifficulty("");
    setCompound("");
    setPage(1);
  }

  return <>
    <header className="page-head">
      <div><span className="eyebrow">Dataset-backed movement catalogue</span><h1>Exercise library</h1><p>Every movement is connected to equipment, muscles, prescriptions, substitutions and progression logic.</p></div>
      {data && <div className="head-actions"><span className="pill pill-success"><Sparkles size={14} /> Dataset v{data.dataset.version}</span></div>}
    </header>

    {data && <section className="catalog-stats" aria-label="Exercise dataset coverage">
      <Card><strong>{data.dataset.exercise_count}</strong><span>Exercises</span></Card>
      <Card><strong>{data.dataset.split_template_count}</strong><span>Program splits</span></Card>
      <Card><strong>{data.dataset.prescription_count}</strong><span>Prescriptions</span></Card>
      <Card><strong>{data.facets.categories.length}</strong><span>Categories</span></Card>
    </section>}

    <Card className="catalog-toolbar">
      <div className="search-input-wrap catalog-search"><Search size={18} /><input className="input" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Search name, muscle, movement or equipment" aria-label="Search exercise catalogue" /></div>
      <select className="select" value={category} onChange={(event) => { setCategory(event.target.value); setPage(1); }} aria-label="Filter by category"><option value="">All categories</option>{data?.facets.categories.map((item) => <option key={item.value} value={item.value}>{item.value} ({item.count})</option>)}</select>
      <select className="select" value={equipment} onChange={(event) => { setEquipment(event.target.value); setPage(1); }} aria-label="Filter by equipment"><option value="">All equipment</option>{data?.facets.equipment.map((item) => <option key={item.value} value={item.value}>{label(item.value)} ({item.count})</option>)}</select>
      <select className="select" value={difficulty} onChange={(event) => { setDifficulty(event.target.value); setPage(1); }} aria-label="Filter by difficulty"><option value="">All difficulty levels</option>{data?.facets.difficulties.map((item) => <option key={item.value} value={item.value}>{label(item.value)} ({item.count})</option>)}</select>
      <select className="select" value={trainingType} onChange={(event) => { setTrainingType(event.target.value); setPage(1); }} aria-label="Filter by athlete type"><option value="">All athlete types</option>{data?.facets.training_types.map((item) => <option key={item.value} value={item.value}>{label(item.value)} ({item.count})</option>)}</select>
      <select className="select" value={compound} onChange={(event) => { setCompound(event.target.value); setPage(1); }} aria-label="Filter by exercise type"><option value="">Compound and isolation</option><option value="true">Compound</option><option value="false">Isolation</option></select>
      {hasFilters && <Button variant="ghost" onClick={clearFilters}><Filter size={15} /> Clear filters</Button>}
    </Card>

    {exercises.isLoading ? <LoadingState label="Loading the complete exercise dataset…" /> : exercises.isError ? <ErrorState message={exercises.error.message} onRetry={() => exercises.refetch()} /> : data?.items.length ? <>
      <div className="section-title"><h2>{data.total} movement{data.total === 1 ? "" : "s"}</h2><span className="tiny">Page {data.page} of {data.pages}</span></div>
      <div className="plan-grid exercise-catalog-grid">{data.items.map((exercise) => <Card className="day-card exercise-card" key={exercise.id}>
        <div className="exercise-card-top"><span className="pill"><Dumbbell size={13} /> {exercise.equipment_display ?? exercise.equipment.map(label).join(" · ")}</span><span className="dataset-id">{exercise.source_id}</span></div>
        <h3>{exercise.name}</h3>
        <span className="focus-list">{exercise.category} · {label(exercise.movement_pattern)}</span>
        <div className="exercise-card-target"><strong>{exercise.default_sets} sets</strong><span>{target(exercise)}</span><span><Clock3 size={13} /> {exercise.rest_seconds}s rest</span></div>
        <div className="chip-grid compact-chips">{exercise.primary_muscles.map((muscle) => <span className="pill" key={muscle}>{muscle}</span>)}<span className="pill">{label(exercise.difficulty)}</span>{exercise.is_unilateral && <span className="pill">Unilateral</span>}</div>
        <Link href={`/exercises/${exercise.id}`} className="text-link">Full exercise profile <ArrowRight size={13} /></Link>
      </Card>)}</div>
      {data.pages > 1 && <nav className="pagination" aria-label="Exercise pages"><Button variant="secondary" disabled={page === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}><ArrowLeft size={15} /> Previous</Button><span>Page {page} of {data.pages}</span><Button variant="secondary" disabled={page === data.pages} onClick={() => setPage((value) => Math.min(data.pages, value + 1))}>Next <ArrowRight size={15} /></Button></nav>}
    </> : <EmptyState icon={<Search />} title="No exercises found" message="Try a broader movement or clear one of the catalogue filters." action={hasFilters ? <Button onClick={clearFilters}>Clear filters</Button> : undefined} />}
  </>;
}
