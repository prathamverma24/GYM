"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, Search, UtensilsCrossed } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button, Card, EmptyState, ErrorState, LoadingState } from "@/components/primitives";
import { api, formatNumber, todayIso } from "@/lib/api";
import type { Food } from "@/types/api";

function AddMeal() {
  const params = useSearchParams(); const router = useRouter();
  const [query, setQuery] = useState(""); const [debounced, setDebounced] = useState(""); const [mealType, setMealType] = useState(params.get("meal") ?? "lunch"); const [selected, setSelected] = useState<Food | null>(null); const [servingId, setServingId] = useState(""); const [quantity, setQuantity] = useState(1);
  const date = params.get("date") ?? todayIso();
  useEffect(() => { const timeout = window.setTimeout(() => setDebounced(query), 350); return () => window.clearTimeout(timeout); }, [query]);
  const search = useQuery({ queryKey: ["food-search", debounced], queryFn: () => api<{ items: Food[] }>(`/foods/search?q=${encodeURIComponent(debounced)}`) });
  const add = useMutation({ mutationFn: () => api(`/meals/${date}/${mealType}/items`, { method: "POST", body: JSON.stringify({ food_id: selected!.id, serving_id: servingId || selected!.servings[0]?.id, quantity }) }), onSuccess: () => router.push("/nutrition") });
  function choose(food: Food) { setSelected(food); setServingId(food.servings.find((item) => item.is_default)?.id ?? food.servings[0]?.id ?? ""); }
  const serving = selected?.servings.find((item) => item.id === servingId); const factor = ((serving?.grams ?? 100) * quantity) / 100;
  return <><header className="page-head"><div><Link className="tiny" href="/nutrition"><ArrowLeft size={13} style={{ display: "inline" }} /> Nutrition</Link><h1 style={{ marginTop: 12 }}>Log your meal</h1><p>Search aliases and common spelling variants across the internal AthleteOS catalogue.</p></div></header><div className="food-search-panel"><div className="chip-grid" style={{ marginBottom: 14 }}>{["breakfast", "lunch", "snacks", "dinner"].map((type) => <button className={`choice-chip ${mealType === type ? "selected" : ""}`} key={type} onClick={() => setMealType(type)}>{type}</button>)}</div><div className="search-input-wrap"><Search size={19} /><input className="input" value={query} onChange={(event) => setQuery(event.target.value)} autoFocus placeholder="Try ‘aloo matar’, ‘alu mutter’, ‘bhindi’ or ‘poha’" aria-label="Search foods" /></div>
    {search.isLoading && <LoadingState label="Searching the catalogue…" />}{search.isError && <ErrorState message={search.error.message} />}
    {!search.isLoading && search.data?.items.length === 0 && <EmptyState icon={<UtensilsCrossed />} title="No close match" message="Try a shorter dish name. Custom foods are planned for the next catalogue increment." />}
    <div className="search-results">{search.data?.items.map((food) => <Card className={`food-result ${selected?.id === food.id ? "accent-pink" : ""}`} key={food.id} role="button" tabIndex={0} onClick={() => choose(food)} onKeyDown={(event) => { if (event.key === "Enter") choose(food); }}><div><h3>{food.canonical_name} {selected?.id === food.id && <Check size={14} style={{ display: "inline", color: "var(--success)" }} />}</h3><div className="food-macros"><span>P {formatNumber(food.per_100g.protein_g)}g</span><span>C {formatNumber(food.per_100g.carb_g)}g</span><span>F {formatNumber(food.per_100g.fat_g)}g</span><span>{food.data_quality}</span></div></div><div className="food-calories"><strong>{formatNumber(food.per_100g.energy_kcal, 0)}</strong>kcal / 100g</div></Card>)}</div>
    {selected && <Card className="serving-composer"><label className="field"><span>Serving</span><select className="select" value={servingId} onChange={(event) => setServingId(event.target.value)}>{selected.servings.map((item) => <option value={item.id} key={item.id}>{item.label} · {item.grams} g</option>)}</select></label><label className="field"><span>Quantity</span><input className="input" type="number" min="0.25" max="20" step="0.25" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} /></label><Button disabled={add.isPending} onClick={() => add.mutate()}>{add.isPending ? "Adding…" : `Add · ${formatNumber(selected.per_100g.energy_kcal * factor, 0)} kcal`}</Button><p className="tiny" style={{ gridColumn: "1/-1", margin: 0 }}>{selected.estimate_note ?? `Source: ${selected.source}`}</p>{add.error && <p className="field-error">{add.error.message}</p>}</Card>}</div></>;
}

export default function AddMealPage() { return <Suspense fallback={<LoadingState label="Opening food search…" />}><AddMeal /></Suspense>; }

