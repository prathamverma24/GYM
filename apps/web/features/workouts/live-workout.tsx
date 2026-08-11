"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, Copy, Plus, RotateCcw, Save, Trash2, Wifi, WifiOff } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Button, Card, ErrorState, LoadingState } from "@/components/primitives";
import { api, ApiError } from "@/lib/api";
import type { Prescription, WorkoutSession } from "@/types/api";
import { type DraftSet, useWorkoutStore } from "./workout-store";

const EMPTY_DRAFTS: DraftSet[] = [];

function blankSet(prescription: Prescription, setIndex: number, previous?: DraftSet): DraftSet {
  const comparable = prescription.previous[setIndex - 1];
  return {
    prescribed_exercise_id: prescription.id,
    set_index: setIndex,
    client_operation_id: crypto.randomUUID(),
    load_kg: previous?.load_kg ?? comparable?.load_kg ?? (prescription.exercise.modality === "weighted_reps" ? 0 : null),
    reps: previous?.reps ?? comparable?.reps ?? prescription.rep_min,
    seconds: previous?.seconds ?? prescription.target_seconds,
    assistance_kg: previous?.assistance_kg ?? null,
    rir: previous?.rir ?? prescription.target_rir,
    completed: false,
    sync: "draft",
  };
}

export function LiveWorkout({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const sessionQuery = useQuery({ queryKey: ["workout", sessionId], queryFn: () => api<{ session: WorkoutSession }>(`/workouts/${sessionId}`) });
  const storedDrafts = useWorkoutStore((state) => state.drafts[sessionId]);
  const drafts = storedDrafts ?? EMPTY_DRAFTS;
  const replace = useWorkoutStore((state) => state.replace);
  const update = useWorkoutStore((state) => state.update);
  const remove = useWorkoutStore((state) => state.remove);
  const clear = useWorkoutStore((state) => state.clear);
  const [rest, setRest] = useState(0);
  const [online, setOnline] = useState(() => typeof navigator === "undefined" || navigator.onLine);

  useEffect(() => { const on = () => setOnline(true); const off = () => setOnline(false); window.addEventListener("online", on); window.addEventListener("offline", off); return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); }; }, []);
  useEffect(() => { if (rest <= 0) return; const timer = window.setInterval(() => setRest((value) => Math.max(0, value - 1)), 1000); return () => window.clearInterval(timer); }, [rest]);
  useEffect(() => {
    if (sessionQuery.data?.session.status === "completed") {
      router.replace(`/workouts/summary/${sessionId}`);
    }
  }, [router, sessionId, sessionQuery.data?.session.status]);
  useEffect(() => {
    const session = sessionQuery.data?.session;
    if (!session || drafts.length) return;
    const serverSets: DraftSet[] = session.sets.map((set) => ({ ...set, sync: "saved" }));
    const initialized = [...serverSets];
    for (const prescription of session.day.exercises) {
      for (let index = 1; index <= prescription.target_sets; index += 1) {
        if (!initialized.some((set) => set.prescribed_exercise_id === prescription.id && set.set_index === index)) initialized.push(blankSet(prescription, index));
      }
    }
    replace(sessionId, initialized);
  }, [sessionQuery.data, drafts.length, replace, sessionId]);

  const saveSet = useCallback(async (draft: DraftSet) => {
    update(sessionId, draft.client_operation_id, { sync: "pending", completed: true });
    try {
      const result = await api<{ set: { id: string } }>(`/workouts/${sessionId}/sets`, { method: "POST", body: JSON.stringify({ ...draft, completed: true, sync: undefined }) });
      update(sessionId, draft.client_operation_id, { id: result.set.id, sync: "saved", completed: true });
      const prescription = sessionQuery.data?.session.day.exercises.find((item) => item.id === draft.prescribed_exercise_id);
      setRest(prescription?.rest_seconds ?? 90);
    } catch (error) {
      update(sessionId, draft.client_operation_id, { sync: error instanceof ApiError ? "error" : "pending", completed: true });
    }
  }, [sessionId, sessionQuery.data, update]);

  async function syncPending() { for (const draft of drafts.filter((item) => item.sync === "pending" || item.sync === "error")) await saveSet(draft); }
  const finish = useMutation({ mutationFn: async () => { await syncPending(); const pending = useWorkoutStore.getState().drafts[sessionId]?.some((item) => item.completed && item.sync !== "saved"); if (pending) throw new Error("Some sets are still waiting to sync."); return api(`/workouts/${sessionId}/complete`, { method: "POST", body: JSON.stringify({ rating: "good", session_rpe: 8 }) }); }, onSuccess: () => { clear(sessionId); router.push(`/workouts/summary/${sessionId}`); } });

  const pendingCount = drafts.filter((item) => item.completed && item.sync !== "saved").length;
  const grouped = useMemo(() => Object.groupBy(drafts, (item) => item.prescribed_exercise_id), [drafts]);
  if (sessionQuery.isLoading) return <LoadingState label="Restoring your active workout…" />;
  if (sessionQuery.isError || !sessionQuery.data) return <ErrorState message={sessionQuery.error?.message} onRetry={() => sessionQuery.refetch()} />;
  const session = sessionQuery.data.session;
  if (session.status === "completed") return null;

  function addSet(prescription: Prescription) { const current = grouped[prescription.id] ?? []; replace(sessionId, [...drafts, blankSet(prescription, current.length + 1, current.at(-1))]); }
  async function deleteSet(draft: DraftSet) { if (draft.id) await api(`/workouts/${sessionId}/sets/${draft.id}`, { method: "DELETE" }); remove(sessionId, draft.client_operation_id); }
  const formatTimer = `${String(Math.floor(rest / 60)).padStart(2, "0")}:${String(rest % 60).padStart(2, "0")}`;
  return <>
    <header className="page-head"><div><span className="eyebrow">Live session</span><h1>{session.day.title}</h1><p>{session.day.focus.join(" · ")} · every input is stored locally before sync</p></div><div className="head-actions"><Button disabled={finish.isPending || !drafts.some((item) => item.completed)} onClick={() => finish.mutate()}>{finish.isPending ? "Finishing…" : "Finish workout"}<Check size={17} /></Button></div></header>
    {finish.error && <p className="field-error" role="alert">{finish.error.message}</p>}
    <div className="session-layout"><div>{session.day.exercises.map((prescription) => { const sets = (grouped[prescription.id] ?? []).toSorted((a, b) => a.set_index - b.set_index); const timed = prescription.exercise.modality === "isometric_hold"; return <Card className="session-exercise" key={prescription.id}><div className="session-exercise-head"><div><h2>{prescription.exercise.name}</h2><span className="focus-list">Target · {prescription.target_sets} × {timed ? `${prescription.target_seconds}s` : `${prescription.rep_min}–${prescription.rep_max}`} · RIR {prescription.target_rir}</span></div><span className="pill">Rest {Math.floor(prescription.rest_seconds / 60)}:{String(prescription.rest_seconds % 60).padStart(2, "0")}</span></div><div className="set-table-wrap"><table className="set-table"><thead><tr><th>Set</th>{!timed && <th>Weight kg</th>}<th>{timed ? "Seconds" : "Reps"}</th><th>RIR</th><th>Save</th><th /></tr></thead><tbody>{sets.map((draft, index) => <tr key={draft.client_operation_id}><td><span className={`set-number ${draft.sync === "saved" ? "saved" : ""}`}>{draft.sync === "saved" ? <Check size={14} /> : draft.set_index}</span></td>{!timed && <td><input className="input" inputMode="decimal" type="number" min="0" step="0.5" value={draft.load_kg ?? ""} onChange={(e) => update(sessionId, draft.client_operation_id, { load_kg: e.target.value === "" ? null : Number(e.target.value), sync: "draft", completed: false })} /></td>}<td><input className="input" inputMode="numeric" type="number" min="0" value={(timed ? draft.seconds : draft.reps) ?? ""} onChange={(e) => update(sessionId, draft.client_operation_id, timed ? { seconds: Number(e.target.value), sync: "draft", completed: false } : { reps: Number(e.target.value), sync: "draft", completed: false })} /></td><td><input className="input" inputMode="numeric" type="number" min="0" max="10" value={draft.rir ?? ""} onChange={(e) => update(sessionId, draft.client_operation_id, { rir: e.target.value === "" ? null : Number(e.target.value), sync: "draft", completed: false })} /></td><td><button className="icon-button" type="button" aria-label={`Save set ${draft.set_index}`} disabled={draft.sync === "pending"} onClick={() => saveSet(draft)}>{draft.sync === "pending" ? <RotateCcw className="spinner" size={15} /> : draft.sync === "saved" ? <Check size={16} /> : <Save size={16} />}</button></td><td><div style={{ display: "flex", gap: 5 }}>{index > 0 && <button className="icon-button" type="button" aria-label="Copy previous set" onClick={() => { const previous = sets[index - 1]; update(sessionId, draft.client_operation_id, { load_kg: previous.load_kg, reps: previous.reps, seconds: previous.seconds, rir: previous.rir, sync: "draft", completed: false }); }}><Copy size={14} /></button>}{sets.length > prescription.target_sets && <button className="icon-button" type="button" aria-label="Remove set" onClick={() => deleteSet(draft)}><Trash2 size={14} /></button>}</div></td></tr>)}</tbody></table></div><div className="session-actions"><Button variant="ghost" type="button" onClick={() => addSet(prescription)}><Plus size={15} /> Add set</Button></div></Card>; })}</div>
      <aside className="session-side"><Card className="timer-card"><span className="eyebrow">Rest timer</span><div className="timer-display">{formatTimer}</div><div style={{ display: "flex", gap: 7, justifyContent: "center" }}><Button variant="ghost" onClick={() => setRest((value) => value + 30)}>+30s</Button><Button variant="ghost" onClick={() => setRest(0)}>Skip</Button></div></Card><Card className="sync-status"><span className={`dot ${pendingCount ? "pending" : ""}`} />{online ? <Wifi size={15} /> : <WifiOff size={15} />}<span>{!online ? "Offline · inputs remain on this device" : pendingCount ? `${pendingCount} set${pendingCount === 1 ? "" : "s"} waiting to sync` : "All completed sets synced"}</span>{pendingCount > 0 && online && <button className="text-link" onClick={syncPending}>Retry</button>}</Card><Card className="card-pad"><span className="eyebrow">Gym mode</span><p className="tiny" style={{ margin: "12px 0 0" }}>Use the large inputs between sets. Values are numeric-keypad friendly and previous performance is pre-filled where available.</p></Card></aside>
    </div>
  </>;
}
