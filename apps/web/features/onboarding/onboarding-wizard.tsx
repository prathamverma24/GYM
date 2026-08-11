"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowLeft, ArrowRight, Camera, Check, Dumbbell, HeartPulse, ShieldCheck, Sparkles, Target } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { Brand, Button, LoadingState } from "@/components/primitives";
import { ApiError, api } from "@/lib/api";
import type { User } from "@/types/api";

type Profile = {
  date_of_birth: string | null; height_cm: number | null; weight_kg: number | null; unit_system: string; country: string; gender: string | null;
  activity_level: string | null; sleep_hours: number | null; water_target_ml: number | null;
  experience_level: string | null; training_type: string | null; primary_goal: string | null;
  equipment: string[]; schedule: Record<string, unknown>; onboarding_step: number; onboarding_completed: boolean;
};

const stepMeta = [
  ["Basic information", "The essentials used for units and your starting point."],
  ["Lifestyle baseline", "Give recovery and hydration guidance a sensible baseline."],
  ["Experience level", "We’ll keep complexity and progression appropriate."],
  ["Training type", "Choose the discipline that should lead your program."],
  ["Primary outcome", "Tell AthleteOS what success should emphasize."],
  ["Available equipment", "Your program will never assume equipment you don’t have."],
  ["Weekly schedule", "Fit training into the week you can consistently execute."],
  ["Measurements", "Optional baseline measurements are stored as history, never overwritten."],
  ["Optional body scan", "Use visual progress assistance or skip it without losing any core feature."],
] as const;

const equipmentOptions = ["full_gym", "bodyweight", "dumbbells", "barbell", "bench", "pull_up_bar", "resistance_bands", "cable_machine", "kettlebells", "dip_bars", "squat_rack", "plyo_box", "open_space"];

export function OnboardingWizard() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const stateQuery = useQuery({ queryKey: ["onboarding"], queryFn: () => api<{ profile: Profile }>("/onboarding"), retry: false });
  const userQuery = useQuery({ queryKey: ["me"], queryFn: () => api<{ user: User }>("/auth/me"), retry: false });
  const [step, setStep] = useState(1);
  const [data, setData] = useState<Record<string, unknown>>({
    full_name: "", date_of_birth: "", height_cm: 178, weight_kg: 72.5, gender: "", unit_system: "metric", country: "India", timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kolkata",
    water_target_ml: 3000, sleep_hours: 7.5, activity_level: "moderately_active", experience_level: "intermediate", training_type: "bodybuilding", primary_goal: "aesthetic_physique",
    equipment: ["full_gym"], days_per_week: 5, preferred_weekdays: [0, 1, 2, 4, 5], session_minutes: 60, preferred_time: "evening", cv_consent: false, skip_scan: true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  /* eslint-disable react-hooks/set-state-in-effect -- hydrate resumable server state */
  useEffect(() => {
    const profile = stateQuery.data?.profile;
    if (!profile) return;
    if (profile.onboarding_completed) {
      router.replace("/dashboard");
      return;
    }
    setStep(profile.onboarding_step || 1);
    setData((current) => ({ ...current, full_name: userQuery.data?.user.full_name ?? current.full_name, date_of_birth: profile.date_of_birth ?? current.date_of_birth, height_cm: profile.height_cm ?? current.height_cm, weight_kg: profile.weight_kg ?? current.weight_kg, unit_system: profile.unit_system, country: profile.country, gender: profile.gender ?? current.gender, water_target_ml: profile.water_target_ml ?? current.water_target_ml, sleep_hours: profile.sleep_hours ?? current.sleep_hours, activity_level: profile.activity_level ?? current.activity_level, experience_level: profile.experience_level ?? current.experience_level, training_type: profile.training_type ?? current.training_type, primary_goal: profile.primary_goal ?? current.primary_goal, equipment: profile.equipment.length ? profile.equipment : current.equipment, ...profile.schedule }));
  }, [stateQuery.data, userQuery.data, router]);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    const queryError = stateQuery.error ?? userQuery.error;
    if (queryError instanceof ApiError && queryError.status === 401) {
      router.replace("/login?reason=session-expired");
    }
  }, [stateQuery.error, userQuery.error, router]);

  const progressLabel = useMemo(() => `${Math.round((step / 9) * 100)}% complete`, [step]);
  function update(key: string, value: unknown) { setData((current) => ({ ...current, [key]: value })); }
  function toggleList(key: string, value: string | number) {
    const current = (data[key] as Array<string | number>) ?? [];
    update(key, current.includes(value) ? current.filter((item) => item !== value) : [...current, value]);
  }
  async function next(event?: FormEvent) {
    event?.preventDefault(); setSaving(true); setError("");
    const keys: Record<number, string[]> = {
      1: ["full_name", "date_of_birth", "height_cm", "weight_kg", "gender", "unit_system", "country", "timezone"],
      2: ["water_target_ml", "sleep_hours", "activity_level"], 3: ["experience_level"], 4: ["training_type"], 5: ["primary_goal"], 6: ["equipment"],
      7: ["days_per_week", "preferred_weekdays", "session_minutes", "preferred_time"], 8: ["chest_cm", "waist_cm", "shoulders_cm", "arms_cm", "thighs_cm", "hips_cm", "neck_cm"], 9: ["cv_consent", "skip_scan"],
    };
    const payload = Object.fromEntries(keys[step].filter((key) => data[key] !== "" && data[key] !== undefined).map((key) => [key, data[key]]));
    try {
      const result = await api<{ profile: Profile }>("/onboarding", { method: "PUT", body: JSON.stringify({ step, data: payload }) });
      queryClient.setQueryData(["onboarding"], result);
      if (result.profile.onboarding_completed) {
        queryClient.setQueryData<{ user: User }>(["me"], (current) => current ? {
          user: {
            ...current.user,
            onboarding_completed: true,
            onboarding_step: 9,
            experience_level: result.profile.experience_level,
          },
        } : current);
        await queryClient.invalidateQueries({ queryKey: ["me"], refetchType: "none" });
        router.replace("/dashboard");
        router.refresh();
      } else {
        setStep(result.profile.onboarding_step || Math.min(9, step + 1));
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to save this step."); }
    finally { setSaving(false); }
  }

  if (stateQuery.isLoading || userQuery.isLoading || stateQuery.isError || userQuery.isError) return <main className="auth-page"><LoadingState label="Restoring your secure setup…" /></main>;
  const [title, subtitle] = stepMeta[step - 1];
  return (
    <main className="onboarding-page">
      <aside className="onboarding-aside"><Brand /><div className="onboarding-art" aria-hidden="true"><Image src="/assets/onboarding-system.png" alt="" fill priority sizes="(max-width: 767px) 1px, 36vw" /></div><h1>Build the system around <span className="gradient-text">your life.</span></h1><p>Nine focused steps create your first real training week. Everything can be changed later.</p><span className="pill" style={{ width: "fit-content" }}><ShieldCheck size={14} /> {progressLabel}</span></aside>
      <section className="onboarding-main"><form className="onboarding-panel" onSubmit={next}>
        <div className="stepper" aria-label={`Step ${step} of 9`}>{Array.from({ length: 9 }, (_, index) => <span key={index} style={{ display: "contents" }}><i className={`step-dot ${index + 1 < step ? "done" : index + 1 === step ? "active" : ""}`} />{index < 8 && <i className={`step-line ${index + 1 < step ? "done" : ""}`} />}</span>)}</div>
        <div className="step-copy"><span className="eyebrow">Step {step} of 9</span><h1>{title}</h1><p>{subtitle}</p></div>

        {step === 1 && <div className="form-stack"><div className="form-row"><label className="field"><span>Full name</span><input className="input" required value={String(data.full_name)} onChange={(e) => update("full_name", e.target.value)} /></label><label className="field"><span>Date of birth</span><input className="input" type="date" required value={String(data.date_of_birth)} onChange={(e) => update("date_of_birth", e.target.value)} /></label></div><div className="form-row"><label className="field"><span>Height</span><div className="input-suffix"><input className="input" type="number" min="100" max="250" required value={Number(data.height_cm)} onChange={(e) => update("height_cm", Number(e.target.value))} /><span>cm</span></div></label><label className="field"><span>Weight</span><div className="input-suffix"><input className="input" type="number" step="0.1" min="25" max="400" required value={Number(data.weight_kg)} onChange={(e) => update("weight_kg", Number(e.target.value))} /><span>kg</span></div></label></div><div className="form-row"><label className="field"><span>Gender (optional)</span><select className="select" value={String(data.gender)} onChange={(e) => update("gender", e.target.value)}><option value="">Prefer not to say</option><option value="male">Male</option><option value="female">Female</option><option value="non_binary">Non-binary</option><option value="other">Other</option></select></label><label className="field"><span>Display units</span><select className="select" value={String(data.unit_system)} onChange={(e) => update("unit_system", e.target.value)}><option value="metric">Metric · kg / cm</option><option value="imperial">Imperial · lb / in</option></select></label></div></div>}
        {step === 2 && <div className="form-stack"><label className="field"><span>Daily water target</span><div className="input-suffix"><input className="input" type="number" min="1000" max="10000" step="250" value={Number(data.water_target_ml)} onChange={(e) => update("water_target_ml", Number(e.target.value))} /><span>ml</span></div></label><label className="field"><span>Typical sleep duration</span><div className="input-suffix"><input className="input" type="number" min="0" max="16" step="0.5" value={Number(data.sleep_hours)} onChange={(e) => update("sleep_hours", Number(e.target.value))} /><span>hours</span></div></label><label className="field"><span>Daily activity</span><select className="select" value={String(data.activity_level)} onChange={(e) => update("activity_level", e.target.value)}><option value="sedentary">Sedentary</option><option value="lightly_active">Lightly active</option><option value="moderately_active">Moderately active</option><option value="very_active">Very active</option></select></label></div>}
        {step === 3 && <ChoiceGrid value={String(data.experience_level)} onChange={(value) => update("experience_level", value)} options={[["beginner", "Beginner", "New to structured training"], ["early_beginner", "Early Beginner", "Patterns established; building consistency"], ["intermediate", "Intermediate", "Consistent history and meaningful plateaus"], ["advanced", "Advanced", "High training age and specialized goals"]]} icon={<Activity size={19} />} />}
        {step === 4 && <ChoiceGrid value={String(data.training_type)} onChange={(value) => update("training_type", value)} options={[["bodybuilding", "Bodybuilding", "Hypertrophy, volume and muscle-group progression"], ["calisthenics", "Calisthenics", "Skills, bodyweight strength and prerequisites"], ["athletic", "Athletic", "Strength, speed, power and conditioning"], ["aesthetic", "Aesthetic", "Balanced proportions and physique priorities"], ["hybrid", "Hybrid", "A deliberate blend across training modes"]]} icon={<Dumbbell size={19} />} />}
        {step === 5 && <ChoiceGrid value={String(data.primary_goal)} onChange={(value) => update("primary_goal", value)} options={[["muscle_gain", "Muscle gain", "Build lean tissue with progressive training"], ["fat_loss", "Fat loss", "Preserve performance while reducing bodyweight"], ["recomposition", "Recomposition", "Improve performance and body trend together"], ["strength", "Strength", "Prioritize performance in key movements"], ["endurance", "Endurance", "Build sustainable work capacity"], ["skill_development", "Skill development", "Unlock progression-aware movement skills"], ["aesthetic_physique", "Aesthetic physique", "Emphasize balanced muscular development"], ["general_fitness", "General fitness", "Build a durable all-round routine"]]} icon={<Target size={19} />} />}
        {step === 6 && <div className="chip-grid">{equipmentOptions.map((item) => <button type="button" key={item} className={`choice-chip ${(data.equipment as string[]).includes(item) ? "selected" : ""}`} onClick={() => item === "full_gym" ? update("equipment", ["full_gym"]) : toggleList("equipment", item)}>{item.replaceAll("_", " ")}</button>)}</div>}
        {step === 7 && <div className="form-stack"><label className="field"><span>Training days per week</span><input className="input" type="range" min="2" max="6" value={Number(data.days_per_week)} onChange={(e) => update("days_per_week", Number(e.target.value))} /><strong>{String(data.days_per_week)} days</strong></label><div className="field"><span>Preferred weekdays</span><div className="chip-grid">{["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((label, index) => <button type="button" className={`choice-chip ${(data.preferred_weekdays as number[]).includes(index) ? "selected" : ""}`} key={label} onClick={() => toggleList("preferred_weekdays", index)}>{label}</button>)}</div></div><div className="form-row"><label className="field"><span>Session duration</span><select className="select" value={Number(data.session_minutes)} onChange={(e) => update("session_minutes", Number(e.target.value))}><option value="30">30 minutes</option><option value="45">45 minutes</option><option value="60">60 minutes</option><option value="75">75 minutes</option><option value="90">90 minutes</option></select></label><label className="field"><span>Preferred time</span><select className="select" value={String(data.preferred_time)} onChange={(e) => update("preferred_time", e.target.value)}><option value="morning">Morning</option><option value="afternoon">Afternoon</option><option value="evening">Evening</option></select></label></div></div>}
        {step === 8 && <div className="form-row">{["chest", "waist", "shoulders", "arms", "thighs", "hips", "neck"].map((measurement) => <label className="field" key={measurement}><span style={{ textTransform: "capitalize" }}>{measurement}</span><div className="input-suffix"><input className="input" type="number" step="0.1" min="10" max="250" value={data[`${measurement}_cm`] === undefined ? "" : Number(data[`${measurement}_cm`])} onChange={(e) => update(`${measurement}_cm`, e.target.value ? Number(e.target.value) : undefined)} placeholder="Optional" /><span>cm</span></div></label>)}</div>}
        {step === 9 && <div className="form-stack"><div className="choice-grid"><button className={`choice-card ${data.cv_consent ? "selected" : ""}`} type="button" onClick={() => setData((current) => ({ ...current, cv_consent: true, skip_scan: false }))}><span className="choice-icon"><Camera size={20} /></span><strong>Enable visual analysis</strong><span>Run privacy-first browser analysis now or later from Body Scan.</span></button><button className={`choice-card ${data.skip_scan ? "selected" : ""}`} type="button" onClick={() => setData((current) => ({ ...current, cv_consent: false, skip_scan: true }))}><span className="choice-icon"><Sparkles size={20} /></span><strong>Skip for now</strong><span>Your full training plan works without images or computer vision.</span></button></div><div className="scan-safety"><HeartPulse size={34} /><span>Visual analysis is approximate. It is not a medical device, does not diagnose conditions, and does not provide clinically validated body-fat measurements. Camera distance, clothing, pose, lighting and lens distortion affect results.</span></div></div>}
        {error && <p className="field-error" role="alert" style={{ marginTop: 18 }}>{error}</p>}
        <div className="onboarding-actions"><Button type="button" variant="ghost" disabled={step === 1 || saving} onClick={() => setStep((value) => Math.max(1, value - 1))}><ArrowLeft size={16} /> Back</Button><Button disabled={saving}>{saving ? "Saving…" : step === 9 ? <><Check size={17} /> Generate my plan</> : <>Continue <ArrowRight size={17} /></>}</Button></div>
      </form></section>
    </main>
  );
}

function ChoiceGrid({ value, onChange, options, icon }: { value: string; onChange: (value: string) => void; options: readonly (readonly [string, string, string])[]; icon: React.ReactNode }) {
  return <div className="choice-grid">{options.map(([id, label, description]) => <button type="button" className={`choice-card ${value === id ? "selected" : ""}`} key={id} onClick={() => onChange(id)}><span className="choice-icon">{icon}</span><strong>{label}</strong><span>{description}</span></button>)}</div>;
}
