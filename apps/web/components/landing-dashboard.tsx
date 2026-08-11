"use client";

import {
  Activity,
  Bell,
  CheckCircle2,
  Circle,
  Droplets,
  Dumbbell,
  Flame,
  Gauge,
  Scale,
} from "lucide-react";
import Link from "next/link";
import { Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, XAxis, YAxis } from "recharts";

const progress = [
  { day: "Mon", kg: 72.8 },
  { day: "Tue", kg: 72.4 },
  { day: "Wed", kg: 71.9 },
  { day: "Thu", kg: 72.5 },
  { day: "Fri", kg: 72.1 },
  { day: "Sat", kg: 72.9 },
  { day: "Sun", kg: 73.2 },
];

const macros = [
  { name: "Protein", value: 132, color: "#8b5cf6" },
  { name: "Carbs", value: 210, color: "#ffad43" },
  { name: "Fats", value: 58, color: "#ff247d" },
];

const workout = [
  ["Bench Press", "4 × 8–10"],
  ["Incline Dumbbell Press", "3 × 10–12"],
  ["Shoulder Press", "3 × 8–10"],
  ["Tricep Pushdown", "3 × 12–15"],
];

const habits = [
  ["Gym workout", 6],
  ["10k steps", 5],
  ["Drink 3L water", 5],
  ["Meditate", 4],
  ["Read 20 pages", 5],
  ["No sugar", 4],
  ["Early sleep", 5],
];

export function LandingDashboard() {
  return (
    <div className="landing-dashboard" aria-label="AthleteOS dashboard preview">
      <div className="landing-dashboard-head">
        <strong>Today&apos;s overview</strong>
        <div className="landing-dashboard-tools">
          <span><Flame size={14} /> <b>22</b> day streak</span>
          <Bell size={16} aria-label="Notifications" />
        </div>
      </div>

      <div className="landing-overview-grid">
        <div className="landing-overview-card overview-yellow">
          <Scale size={17} /><span>Weight</span><strong>72.5 <small>kg</small></strong><small>↓ 0.8 kg this week</small>
        </div>
        <div className="landing-overview-card overview-orange">
          <Gauge size={17} /><span>Body fat</span><strong>14.2<small>%</small></strong><small>↓ 1.3% this week</small>
        </div>
        <div className="landing-overview-card overview-lime">
          <Activity size={17} /><span>Muscle mass</span><strong>59.3 <small>kg</small></strong><small>↑ 1.2 kg this week</small>
        </div>
        <div className="landing-overview-card overview-blue">
          <Droplets size={17} /><span>Water intake</span><strong>2.6 <small>/ 3 L</small></strong><small>Keep going!</small>
        </div>
      </div>

      <div className="landing-dashboard-grid">
        <section className="landing-dash-card landing-workout-card">
          <span className="landing-dash-label">Today&apos;s workout</span>
          <h3>Push Day</h3>
          <div className="landing-workout-list">
            {workout.map(([name, target]) => (
              <div key={name}><span><Dumbbell size={13} />{name}</span><small>{target}</small></div>
            ))}
          </div>
          <Link href="/workouts" className="landing-start-workout">Start workout <span aria-hidden="true">→</span></Link>
        </section>

        <section className="landing-dash-card landing-nutrition-card">
          <span className="landing-dash-label">Nutrition summary</span>
          <div className="landing-nutrition-layout">
            <div className="landing-macro-chart">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={macros} dataKey="value" innerRadius={39} outerRadius={54} isAnimationActive={false} strokeWidth={0}>
                    {macros.map((macro) => <Cell fill={macro.color} key={macro.name} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div><strong>1820</strong><span>/ 2,200 kcal</span></div>
            </div>
            <div className="landing-macro-list">
              {macros.map((macro) => <div key={macro.name}><i style={{ background: macro.color }} /><span>{macro.name}</span><strong>{macro.value}g</strong></div>)}
            </div>
          </div>
          <Link href="/nutrition">See full breakdown <span aria-hidden="true">→</span></Link>
        </section>

        <section className="landing-dash-card landing-progress-card">
          <span className="landing-dash-label">Weekly progress</span>
          <div className="landing-progress-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={progress} margin={{ top: 10, right: 8, left: -25, bottom: 0 }}>
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#77809b", fontSize: 8 }} />
                <YAxis domain={[71, 74]} axisLine={false} tickLine={false} tick={{ fill: "#77809b", fontSize: 8 }} />
                <Line isAnimationActive={false} type="monotone" dataKey="kg" stroke="#ff247d" strokeWidth={2} dot={{ r: 2.5, fill: "#080b18", stroke: "#ff247d", strokeWidth: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="landing-dash-card landing-habit-card">
          <span className="landing-dash-label">Habit tracker</span>
          <div className="landing-habit-days"><span /><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span></div>
          {habits.map(([name, complete]) => (
            <div className="landing-habit-row" key={name}>
              <span>{name}</span>
              {[0, 1, 2, 3, 4, 5, 6].map((day) => day < Number(complete)
                ? <CheckCircle2 size={11} key={day} />
                : <Circle size={11} key={day} />)}
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
