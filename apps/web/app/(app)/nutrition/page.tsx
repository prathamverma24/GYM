"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Droplets, Plus, Trash2, UtensilsCrossed } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button, Card, ErrorState, LoadingState } from "@/components/primitives";
import { api, formatNumber, todayIso } from "@/lib/api";

type DayNutrition = { date: string; totals: { energy_kcal: number; protein_g: number; carb_g: number; fat_g: number }; targets: { energy_kcal: number; protein_g: number; carb_g: number; fat_g: number; water_ml: number }; water_ml: number; meals: Array<{ id: string; meal_type: string; items: Array<{ id: string; name: string; serving_label: string; energy_kcal: number; protein_g: number; carb_g: number; fat_g: number }> }>; target_note: string };
const mealTypes = ["breakfast", "lunch", "snacks", "dinner"];

function shiftDate(value: string, amount: number) { const next = new Date(`${value}T12:00:00`); next.setDate(next.getDate() + amount); return next.toISOString().slice(0, 10); }

export default function NutritionPage() {
  const [date, setDate] = useState(todayIso());
  const queryClient = useQueryClient();
  const dayQuery = useQuery({ queryKey: ["nutrition", date], queryFn: () => api<DayNutrition>(`/nutrition/days/${date}`) });
  const water = useMutation({ mutationFn: (amount_ml: number) => api("/water", { method: "POST", body: JSON.stringify({ amount_ml, local_date: date, client_operation_id: crypto.randomUUID() }) }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["nutrition", date] }) });
  const deleteItem = useMutation({ mutationFn: (id: string) => api(`/meal-items/${id}`, { method: "DELETE" }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["nutrition", date] }) });
  if (dayQuery.isLoading) return <LoadingState label="Loading today’s nutrition…" />;
  if (dayQuery.isError || !dayQuery.data) return <ErrorState message={dayQuery.error?.message} onRetry={() => dayQuery.refetch()} />;
  const day = dayQuery.data; const caloriePercent = Math.min(100, Math.round(day.totals.energy_kcal / day.targets.energy_kcal * 100)); const waterPercent = Math.min(100, Math.round(day.water_ml / day.targets.water_ml * 100));
  return <><header className="page-head"><div><span className="eyebrow">Daily nutrition</span><h1>Fuel the work.</h1><p>Prepared dishes are transparent estimates with a serving context. Your logged snapshot never changes later.</p></div><div className="head-actions"><Button variant="ghost" aria-label="Previous day" onClick={() => setDate(shiftDate(date, -1))}><ChevronLeft size={17} /></Button><span className="pill">{date === todayIso() ? "Today" : date}</span><Button variant="ghost" aria-label="Next day" disabled={date >= todayIso()} onClick={() => setDate(shiftDate(date, 1))}><ChevronRight size={17} /></Button></div></header>
    <div className="nutrition-grid"><div className="dashboard-stack"><Card className="nutrition-overview"><div className="calorie-row"><div><span className="eyebrow">Calories consumed</span><div><strong>{formatNumber(day.totals.energy_kcal, 0)}</strong> <span className="tiny">/ {day.targets.energy_kcal} kcal</span></div></div><span className="pill pill-success">{caloriePercent}%</span></div><div className="progress-track"><span style={{ width: `${caloriePercent}%` }} /></div><div className="macro-tiles">{[["Protein", day.totals.protein_g, day.targets.protein_g], ["Carbs", day.totals.carb_g, day.targets.carb_g], ["Fat", day.totals.fat_g, day.targets.fat_g]].map(([label, value, target]) => <div className="macro-tile" key={String(label)}><span>{label}</span><strong>{formatNumber(Number(value), 0)}g</strong><small>{formatNumber(Number(target) - Number(value), 0)}g remaining</small></div>)}</div><p className="tiny" style={{ margin: "17px 0 0" }}>{day.target_note}</p></Card>
      {mealTypes.map((type) => { const meal = day.meals.find((item) => item.meal_type === type); return <Card className="meal-section" key={type}><div className="meal-head"><h3>{type}</h3><Link href={`/nutrition/add?meal=${type}&date=${date}`}><Button variant="ghost"><Plus size={15} /> Add food</Button></Link></div>{meal?.items.length ? meal.items.map((item) => <div className="meal-item" key={item.id}><div><strong>{item.name}</strong><small>{item.serving_label} · P {formatNumber(item.protein_g)} · C {formatNumber(item.carb_g)} · F {formatNumber(item.fat_g)}</small></div><div style={{ display: "flex", alignItems: "center", gap: 8 }}><strong>{formatNumber(item.energy_kcal, 0)} kcal</strong><button className="icon-button" aria-label={`Delete ${item.name}`} onClick={() => deleteItem.mutate(item.id)}><Trash2 size={14} /></button></div></div>) : <p className="tiny" style={{ margin: 0 }}>Nothing logged yet. Search recent and Indian foods in one tap.</p>}</Card>; })}</div>
      <aside className="dashboard-stack"><Card className="water-card"><div className="water-head"><div><span className="eyebrow"><Droplets size={13} style={{ display: "inline" }} /> Water tracker</span><strong style={{ display: "block", marginTop: 7, fontSize: "1.35rem" }}>{formatNumber(day.water_ml / 1000)} / {formatNumber(day.targets.water_ml / 1000)} L</strong></div><span className="pill pill-success">{waterPercent}%</span></div><div className="progress-track" style={{ marginBottom: 18 }}><span style={{ width: `${waterPercent}%` }} /></div><div className="water-quick"><Button variant="secondary" onClick={() => water.mutate(250)}><Plus size={14} />250 ml</Button><Button variant="secondary" onClick={() => water.mutate(500)}><Plus size={14} />500 ml</Button></div></Card><Card className="card-pad"><span className="eyebrow"><UtensilsCrossed size={13} style={{ display: "inline" }} /> Faster tomorrow</span><h3 style={{ marginTop: 12 }}>Your history becomes the shortcut.</h3><p className="tiny">Recent meals and favorites are the next ranking layer. The internal catalogue remains the runtime source of truth.</p><Link href={`/nutrition/add?date=${date}`}><Button variant="secondary" className="button-wide">Search foods</Button></Link></Card></aside></div>
  </>;
}

