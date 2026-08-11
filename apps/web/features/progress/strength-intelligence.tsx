"use client";

import Link from "next/link";
import { ArrowDownRight, ArrowUpRight, BarChart3, ChevronRight, Dumbbell, FileText, LockKeyhole, Sparkles, Target, X } from "lucide-react";
import { KeyboardEvent, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button, Card } from "@/components/primitives";
import { formatNumber } from "@/lib/api";
import type { MusclePerformance, StrengthAnalysis, StrengthPeriod, StrengthReport } from "@/types/api";

import styles from "./strength-intelligence.module.css";

type SortMode = "strongest" | "improved" | "attention" | "region";

const PERIODS: Array<{ id: StrengthPeriod; label: string }> = [
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
  { id: "3_months", label: "3 Months" },
];

const MUSCLE_SHAPES: Array<{ slug: string; view: "front" | "back"; d: string }> = [
  { slug: "traps", view: "front", d: "M97 70 L120 82 L143 70 L137 96 L103 96 Z" },
  { slug: "upper-chest", view: "front", d: "M91 95 Q120 82 149 95 L144 111 Q120 101 96 111 Z" },
  { slug: "chest", view: "front", d: "M92 111 Q120 101 148 111 L143 145 Q120 153 97 145 Z" },
  { slug: "front-delts", view: "front", d: "M78 91 Q91 78 102 95 L94 119 Q78 119 73 106 Z M162 91 Q149 78 138 95 L146 119 Q162 119 167 106 Z" },
  { slug: "side-delts", view: "front", d: "M68 101 Q75 88 83 91 L78 124 Q66 123 63 113 Z M172 101 Q165 88 157 91 L162 124 Q174 123 177 113 Z" },
  { slug: "biceps", view: "front", d: "M64 127 Q78 121 83 132 L78 176 Q67 181 59 170 Z M176 127 Q162 121 157 132 L162 176 Q173 181 181 170 Z" },
  { slug: "forearms", view: "front", d: "M58 178 L77 181 L68 229 L51 227 Z M182 178 L163 181 L172 229 L189 227 Z" },
  { slug: "core", view: "front", d: "M101 150 Q120 157 139 150 L136 225 Q120 236 104 225 Z" },
  { slug: "hip-flexors", view: "front", d: "M101 221 L119 235 L108 254 L94 239 Z M139 221 L121 235 L132 254 L146 239 Z" },
  { slug: "adductors", view: "front", d: "M111 250 L120 243 L118 326 L101 315 Z M129 250 L120 243 L122 326 L139 315 Z" },
  { slug: "quadriceps", view: "front", d: "M87 246 Q105 240 113 257 L107 326 Q93 343 82 322 Z M153 246 Q135 240 127 257 L133 326 Q147 343 158 322 Z" },
  { slug: "calves", view: "front", d: "M83 335 Q99 327 107 344 L101 398 L86 398 L78 360 Z M157 335 Q141 327 133 344 L139 398 L154 398 L162 360 Z" },
  { slug: "traps", view: "back", d: "M91 79 L120 63 L149 79 L137 119 L103 119 Z" },
  { slug: "rear-delts", view: "back", d: "M72 96 Q86 80 103 95 L95 121 Q76 124 67 110 Z M168 96 Q154 80 137 95 L145 121 Q164 124 173 110 Z" },
  { slug: "upper-back", view: "back", d: "M94 99 L120 116 L146 99 L143 151 Q120 164 97 151 Z" },
  { slug: "lats", view: "back", d: "M92 126 Q104 151 107 205 L88 225 Q75 173 78 122 Z M148 126 Q136 151 133 205 L152 225 Q165 173 162 122 Z" },
  { slug: "triceps", view: "back", d: "M61 126 Q75 119 83 132 L77 179 Q65 182 58 169 Z M179 126 Q165 119 157 132 L163 179 Q175 182 182 169 Z" },
  { slug: "forearms", view: "back", d: "M57 178 L77 182 L68 229 L51 227 Z M183 178 L163 182 L172 229 L189 227 Z" },
  { slug: "lower-back", view: "back", d: "M106 180 L120 169 L134 180 L138 225 L120 235 L102 225 Z" },
  { slug: "glutes", view: "back", d: "M91 230 Q108 218 120 237 L116 270 Q98 279 88 260 Z M149 230 Q132 218 120 237 L124 270 Q142 279 152 260 Z" },
  { slug: "hamstrings", view: "back", d: "M87 273 Q103 265 115 276 L108 333 Q93 344 82 326 Z M153 273 Q137 265 125 276 L132 333 Q147 344 158 326 Z" },
  { slug: "calves", view: "back", d: "M82 339 Q99 328 107 347 L101 399 L86 399 L78 363 Z M158 339 Q141 328 133 347 L139 399 L154 399 L162 363 Z" },
];

function statusClass(status: string) {
  if (status === "Very Strong") return styles.veryStrong;
  if (status === "Strong") return styles.strong;
  if (status === "Improving") return styles.improving;
  if (status === "Developing" || status === "Progressing") return styles.developing;
  if (status === "Needs Attention") return styles.attention;
  return styles.insufficient;
}

function scoreText(value: number | null) {
  return value == null ? "Not Enough Data" : `${formatNumber(value)} / 100`;
}

function Change({ value }: { value: number | null }) {
  if (value == null) return <span className={styles.muted}>No comparison yet</span>;
  const positive = value >= 0;
  return <span className={positive ? styles.positive : styles.negative}>{positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{positive ? "+" : ""}{formatNumber(value)}%</span>;
}

function ConfidenceBadge({ value }: { value: MusclePerformance["confidence"] }) {
  return <span className={`${styles.confidence} ${styles[`confidence${value[0].toUpperCase()}${value.slice(1)}`]}`}>{value === "insufficient" ? "Insufficient confidence" : `${value} confidence`}</span>;
}

function StrengthKpis({ data }: { data: StrengthAnalysis }) {
  const cards = [
    { label: "Overall Strength", value: scoreText(data.overall.score), change: data.overall.change_percent, note: `vs previous ${data.period.type.replace("3_months", "3 months")}` },
    { label: "Strongest Area", value: data.strongest?.muscle ?? "Not Enough Data", detail: data.strongest ? `${formatNumber(data.strongest.score)} / 100` : "Keep logging relevant sets" },
    { label: "Most Improved", value: data.most_improved?.muscle ?? "Not Enough Data", change: data.most_improved?.change_percent ?? null, note: "current vs equivalent prior period" },
    { label: "Needs Attention", value: data.needs_attention?.muscle ?? "Not Enough Data", detail: data.needs_attention ? `${formatNumber(data.needs_attention.score)} / 100 relative performance` : "No reliable low area yet" },
  ];
  return <section className={styles.kpiGrid} aria-label="Strength summary">{cards.map((card) => <Card className={styles.kpi} key={card.label}><span className={styles.kpiLabel}>{card.label}</span><strong>{card.value}</strong>{card.change !== undefined ? <Change value={card.change} /> : <span>{card.detail}</span>} {card.note && <small>{card.note}</small>}</Card>)}</section>;
}

function BodyFigure({ view, muscles, onSelect }: { view: "front" | "back"; muscles: Map<string, MusclePerformance>; onSelect: (slug: string) => void }) {
  return <div className={styles.figure}><span>{view === "front" ? "Front" : "Back"}</span><svg viewBox="0 0 240 430" role="img" aria-label={`${view} body strength map`}>
    <circle className={styles.silhouette} cx="120" cy="37" r="25" />
    <path className={styles.silhouette} d="M91 74 Q120 57 149 74 Q174 87 181 126 L193 227 Q185 238 171 230 L158 177 L160 326 L154 409 L132 409 L120 272 L108 409 L86 409 L80 326 L82 177 L69 230 Q55 238 47 227 L59 126 Q66 87 91 74 Z" />
    {MUSCLE_SHAPES.filter((shape) => shape.view === view).map((shape, index) => { const muscle = muscles.get(shape.slug); const label = muscle ? `${muscle.name}: ${muscle.score == null ? "Insufficient Data" : `${muscle.score} out of 100, ${muscle.status}`}` : `${shape.slug}: Insufficient Data`; return <g key={`${shape.slug}-${index}`} role="button" tabIndex={0} aria-label={label} onClick={() => onSelect(shape.slug)} onKeyDown={(event: KeyboardEvent<SVGGElement>) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(shape.slug); } }}><title>{label}</title><path id={`muscle-${shape.slug}-${view}-${index}`} className={`${styles.muscleShape} ${statusClass(muscle?.status ?? "Insufficient Data")}`} d={shape.d} /></g>; })}
  </svg></div>;
}

function MuscleDetail({ muscle, trend, onClose }: { muscle: MusclePerformance; trend: StrengthAnalysis["trend"]; onClose: () => void }) {
  return <div className={styles.overlay} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside className={styles.detailPanel} role="dialog" aria-modal="true" aria-labelledby="muscle-detail-title"><button className={styles.close} onClick={onClose} aria-label="Close muscle detail"><X size={19} /></button><span className="eyebrow">Muscle performance</span><h2 id="muscle-detail-title">{muscle.name}</h2><div className={styles.detailScore}><strong>{scoreText(muscle.score)}</strong><span className={`${styles.statusBadge} ${statusClass(muscle.status)}`}>{muscle.status}</span></div><Change value={muscle.change_percent} /><ConfidenceBadge value={muscle.confidence} />
    <div className={styles.detailMetrics}><div><span>Sessions</span><strong>{muscle.sessions}</strong></div><div><span>Working sets</span><strong>{muscle.working_sets}</strong></div><div><span>Training volume</span><strong>{formatNumber(muscle.training_volume_kg, 0)} kg</strong></div><div><span>Exercise drivers</span><strong>{muscle.exercise_diversity}</strong></div></div>
    <div className={styles.miniChart}><ResponsiveContainer width="100%" height="100%"><LineChart data={trend}><CartesianGrid stroke="#242d50" vertical={false} /><XAxis dataKey="date" tickFormatter={(value) => new Date(`${value}T12:00:00`).toLocaleDateString("en", { month: "short", day: "numeric" })} stroke="#7783a5" fontSize={10} axisLine={false} tickLine={false} /><YAxis domain={[0, 100]} stroke="#7783a5" fontSize={10} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: "#0f1730", border: "1px solid #344065", borderRadius: 12 }} /><Line type="monotone" dataKey={muscle.slug} name={`${muscle.name} score`} stroke="#ff2079" strokeWidth={3} connectNulls dot={{ r: 3 }} /></LineChart></ResponsiveContainer></div>
    <h3>Top exercise drivers</h3><div className={styles.exerciseList}>{muscle.exercises.length ? muscle.exercises.slice(0, 5).map((exercise) => <div key={exercise.id}><span><strong>{exercise.name}</strong><small>{exercise.sets} sets · {formatNumber(exercise.volume, 0)} kg volume</small></span><span>{exercise.best_e1rm ? <><strong>{formatNumber(exercise.best_e1rm)} kg</strong><small>Estimated Strength</small></> : <><strong>{formatNumber(exercise.best)}</strong><small>Performance score</small></>}</span></div>) : <p className={styles.muted}>Complete relevant sets to identify exercise drivers.</p>}</div>
    <p className={styles.methodNote}>This panel describes recorded performance and training exposure, not isolated biological muscle strength.</p>
  </aside></div>;
}

function ReportDrawer({ report, onClose }: { report: StrengthReport; onClose: () => void }) {
  const analysis = report.report.analysis; const training = report.report.training_summary; const recovery = report.report.recovery;
  return <div className={styles.overlay} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside className={`${styles.detailPanel} ${styles.reportPanel}`} role="dialog" aria-modal="true" aria-labelledby="strength-report-title"><button className={styles.close} onClick={onClose} aria-label="Close strength report"><X size={19} /></button><span className="eyebrow">AthleteOS · {report.analytics_version}</span><h2 id="strength-report-title">Strength Report</h2><p>{new Date(`${report.period_start}T12:00:00`).toLocaleDateString()} – {new Date(`${report.period_end}T12:00:00`).toLocaleDateString()}</p>
    <div className={styles.reportHero}><span>Overall Strength</span><strong>{scoreText(analysis.overall.score)}</strong><Change value={analysis.overall.change_percent} /></div>
    <div className={styles.reportColumns}><section><h3>Strongest areas</h3>{analysis.muscles.filter((muscle) => muscle.score != null).sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).slice(0, 3).map((muscle) => <p key={muscle.id}><span>{muscle.name}</span><strong>{muscle.score} / 100</strong></p>)}</section><section><h3>Most improved</h3>{analysis.muscles.filter((muscle) => muscle.change_percent != null && muscle.change_percent > 0).sort((a, b) => (b.change_percent ?? 0) - (a.change_percent ?? 0)).slice(0, 3).map((muscle) => <p key={muscle.id}><span>{muscle.name}</span><strong>+{muscle.change_percent}%</strong></p>)}</section></div>
    <section className={styles.reportSection}><h3>Training summary</h3><div className={styles.detailMetrics}><div><span>Sessions</span><strong>{training.sessions}</strong></div><div><span>Working sets</span><strong>{training.working_sets}</strong></div><div><span>Volume</span><strong>{formatNumber(training.training_volume_kg, 0)} kg</strong></div><div><span>Completion</span><strong>{training.workout_completion_percent}%</strong></div></div></section>
    <section className={styles.reportSection}><h3>Recovery context</h3><p>Average sleep: <strong>{recovery.average_sleep_hours == null ? "Not logged" : `${recovery.average_sleep_hours} hours`}</strong></p><p>Average readiness: <strong>{recovery.average_readiness == null ? "Not logged" : `${recovery.average_readiness}%`}</strong></p></section>
    <section className={styles.reportSection}><h3>Recommendations</h3>{report.report.recommendations.map((item, index) => <div className={styles.recommendation} key={`${item.action}-${index}`}><Target size={17} /><span><strong>{item.action}</strong><small>{item.reason}</small></span></div>)}</section><p className={styles.methodNote}>{analysis.methodology_note}</p>
  </aside></div>;
}

export function StrengthIntelligence({ data, period, onPeriodChange, onGenerateReport, report, onCloseReport, generatingReport }: { data: StrengthAnalysis; period: StrengthPeriod; onPeriodChange: (period: StrengthPeriod) => void; onGenerateReport: () => void; report: StrengthReport | null; onCloseReport: () => void; generatingReport: boolean }) {
  const [sortMode, setSortMode] = useState<SortMode>("strongest"); const [selectedSlug, setSelectedSlug] = useState<string | null>(null); const [trendKey, setTrendKey] = useState("overall");
  const musclesBySlug = useMemo(() => new Map(data.muscles.map((muscle) => [muscle.slug, muscle])), [data.muscles]);
  const selectedMuscle = selectedSlug ? musclesBySlug.get(selectedSlug) ?? null : null;
  const sortedMuscles = useMemo(() => [...data.muscles].sort((a, b) => { if (sortMode === "improved") return (b.change_percent ?? -1000) - (a.change_percent ?? -1000); if (sortMode === "attention") return (a.score ?? 1000) - (b.score ?? 1000); if (sortMode === "region") return `${a.body_region}-${a.name}`.localeCompare(`${b.body_region}-${b.name}`); return (b.score ?? -1) - (a.score ?? -1); }), [data.muscles, sortMode]);
  const sufficient = data.muscles.filter((muscle) => muscle.score != null); const improved = [...sufficient].filter((muscle) => (muscle.change_percent ?? 0) > 0).sort((a, b) => (b.change_percent ?? 0) - (a.change_percent ?? 0)); const attention = [...sufficient].filter((muscle) => muscle.score! < 70).sort((a, b) => a.score! - b.score!);
  return <section className={styles.root}><div className={styles.strengthHeader}><div><span className="eyebrow">Body strength intelligence</span><h2>Recorded Strength Profile</h2><p>Understand how your strength, training balance and muscle performance are changing over time.</p></div><div className={styles.headerControls}><div className={styles.periodSelector} aria-label="Strength analytics period">{PERIODS.map((item) => <button className={period === item.id ? styles.activePeriod : ""} aria-pressed={period === item.id} onClick={() => onPeriodChange(item.id)} key={item.id}>{item.label}</button>)}</div><Button onClick={onGenerateReport} disabled={generatingReport}><FileText size={16} /> {generatingReport ? "Generating…" : "Generate Strength Report"}</Button></div></div>
    {data.period.partial && <div className={styles.partialNote}><Sparkles size={15} /> Partial period · compared with {data.period.comparison_start} through {data.period.comparison_end}, the same elapsed duration.</div>}
    {data.profile_state === "empty" ? <Card className={styles.emptyState}><div className={styles.emptyIcon}><Dumbbell size={28} /></div><span className="eyebrow">Build your strength profile</span><h3>Complete your first few workouts.</h3><p>AthleteOS will start identifying strength trends across your body using your actual completed sets.</p><Link className="button button-primary" href="/workouts">Start Workout <ChevronRight size={16} /></Link></Card> : <>
      {data.profile_state === "building" && <Card className={styles.buildingState}><LockKeyhole size={22} /><div><span className="eyebrow">Strength profile building</span><h3>{data.sessions_recorded} of {data.unlock_target_sessions} recommended sessions recorded</h3><p>Keep training to unlock reliable strong-area, balance and report classifications.</p></div><div className={styles.progressTrack}><i style={{ width: `${Math.min(100, data.sessions_recorded / data.unlock_target_sessions * 100)}%` }} /></div></Card>}
      <StrengthKpis data={data} />
      <div className={styles.primaryGrid}><Card className={styles.mapCard}><div className={styles.sectionHeading}><div><span className="eyebrow">Body strength map</span><h3>Recorded performance by area</h3></div><span className={styles.mapHint}>Select a muscle for detail</span></div><div className={styles.figures}><BodyFigure view="front" muscles={musclesBySlug} onSelect={setSelectedSlug} /><BodyFigure view="back" muscles={musclesBySlug} onSelect={setSelectedSlug} /></div><div className={styles.legend}>{["Very Strong", "Strong", "Improving", "Developing", "Needs Attention", "Insufficient Data"].map((label) => <span key={label}><i className={statusClass(label)} />{label}</span>)}</div></Card>
        <Card className={styles.performanceCard}><div className={styles.sectionHeading}><div><span className="eyebrow">Muscle performance</span><h3>Comparison</h3></div><select aria-label="Sort muscle performance" value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)}><option value="strongest">Strongest</option><option value="improved">Most improved</option><option value="attention">Needs attention</option><option value="region">Body region</option></select></div><div className={styles.muscleRows}>{sortedMuscles.map((muscle) => <button key={muscle.id} onClick={() => setSelectedSlug(muscle.slug)}><span className={`${styles.scoreDot} ${statusClass(muscle.status)}`} /><span className={styles.muscleName}><strong>{muscle.name}</strong><small>{muscle.status} · {muscle.confidence} confidence</small></span><strong>{muscle.score ?? "—"}</strong><Change value={muscle.change_percent} /></button>)}</div></Card></div>
      <Card className={styles.trendCard}><div className={styles.sectionHeading}><div><span className="eyebrow"><BarChart3 size={13} /> Strength trend</span><h3>User-relative score over time</h3></div><select aria-label="Strength trend area" value={trendKey} onChange={(event) => setTrendKey(event.target.value)}><option value="overall">Overall</option>{data.muscles.map((muscle) => <option value={muscle.slug} key={muscle.id}>{muscle.name}</option>)}</select></div><div className={styles.trendChart}><ResponsiveContainer width="100%" height="100%"><LineChart data={data.trend}><CartesianGrid stroke="#242d50" vertical={false} /><XAxis dataKey="date" tickFormatter={(value) => new Date(`${value}T12:00:00`).toLocaleDateString("en", { month: "short", day: "numeric" })} stroke="#7783a5" fontSize={11} axisLine={false} tickLine={false} /><YAxis domain={[0, 100]} stroke="#7783a5" fontSize={11} axisLine={false} tickLine={false} /><Tooltip labelFormatter={(value) => new Date(`${value}T12:00:00`).toLocaleDateString("en", { month: "short", day: "numeric" })} contentStyle={{ background: "#0f1730", border: "1px solid #344065", borderRadius: 12 }} /><Line type="monotone" dataKey={trendKey} name={trendKey === "overall" ? "Overall score" : musclesBySlug.get(trendKey)?.name} stroke="#ff2079" strokeWidth={3} connectNulls dot={{ fill: "#ff2079", r: 4 }} /></LineChart></ResponsiveContainer></div></Card>
      <div className={styles.insightGrid}><Card><span className="eyebrow">Strong areas</span>{[...sufficient].sort((a, b) => b.score! - a.score!).slice(0, 3).map((muscle) => <button className={styles.insightRow} key={muscle.id} onClick={() => setSelectedSlug(muscle.slug)}><span><strong>{muscle.name}</strong><small>{muscle.sessions} sessions · {muscle.working_sets} sets</small></span><span><strong>{muscle.score} / 100</strong><small>{muscle.top_exercise?.name ?? "Building driver data"}</small></span></button>)}{!sufficient.length && <p className={styles.muted}>More history is needed before a strong area is assigned.</p>}</Card><Card><span className="eyebrow">Most improved</span>{improved.slice(0, 3).map((muscle, index) => <button className={styles.insightRow} key={muscle.id} onClick={() => setSelectedSlug(muscle.slug)}><b>{index + 1}</b><span><strong>{muscle.name}</strong><small>{muscle.confidence} confidence</small></span><Change value={muscle.change_percent} /></button>)}{!improved.length && <p className={styles.muted}>Complete an equivalent prior period to unlock improvement rankings.</p>}</Card><Card><span className="eyebrow">Needs attention</span>{attention.slice(0, 3).map((muscle) => <button className={styles.insightRow} key={muscle.id} onClick={() => setSelectedSlug(muscle.slug)}><span><strong>{muscle.name}</strong><small>{muscle.working_sets} weighted sets · {muscle.status}</small></span><strong>{muscle.score} / 100</strong></button>)}{!attention.length && <p className={styles.muted}>No reliable lower-performance area is available for this period.</p>}</Card></div>
      <Card className={styles.balanceCard}><div className={styles.sectionHeading}><div><span className="eyebrow">Muscle balance analysis</span><h3>Performance and exposure comparisons</h3></div></div><div className={styles.balanceGrid}>{data.balance.map((balance) => <div key={balance.name}><h4>{balance.name}</h4><div className={styles.balanceScores}><span><small>{balance.left_label}</small><strong>{balance.left.score ?? "—"}</strong><i style={{ width: `${balance.left.score ?? 0}%` }} /></span><span><small>{balance.right_label}</small><strong>{balance.right.score ?? "—"}</strong><i style={{ width: `${balance.right.score ?? 0}%` }} /></span></div><p>{balance.insight}</p></div>)}</div></Card>
      <Card className={styles.reportCta}><div><span className="eyebrow">AthleteOS strength report</span><h3>Turn this period into a reproducible training report.</h3><p>Includes performance areas, exercise improvements, exposure, recovery context and deterministic recommendations.</p></div><Button onClick={onGenerateReport} disabled={generatingReport}><FileText size={17} /> {generatingReport ? "Generating report…" : `Generate ${PERIODS.find((item) => item.id === period)?.label} Report`}</Button></Card>
    </>}
    <p className={styles.methodNote}>{data.methodology_note}</p>{selectedMuscle && <MuscleDetail muscle={selectedMuscle} trend={data.trend} onClose={() => setSelectedSlug(null)} />}{report && <ReportDrawer report={report} onClose={onCloseReport} />}
  </section>;
}
