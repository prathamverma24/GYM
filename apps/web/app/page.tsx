import {
  Activity,
  ArrowRight,
  BarChart3,
  Check,
  Dumbbell,
  Flame,
  LockKeyhole,
  Salad,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";
import Link from "next/link";

import { Brand, Button, Card, Eyebrow } from "@/components/primitives";

const features = [
  { icon: Dumbbell, title: "Training that fits your reality", copy: "Your mode, level, schedule and equipment become a deterministic weekly program with a clear reason behind every choice." },
  { icon: Salad, title: "Indian-first nutrition logging", copy: "Find aloo matar, bhindi, dal, poha and regional aliases quickly—with household servings and transparent estimate labels." },
  { icon: Target, title: "Consistency you can see", copy: "A schedule-aware habit matrix, water tracker and streaks that understand planned rest days rather than punishing them." },
  { icon: BarChart3, title: "Progress without noise", copy: "Weekly and monthly views connect completed sessions, body metrics, nutrition and habits without turning missing data into zero." },
  { icon: ScanLine, title: "Privacy-first visual progress", copy: "Optional browser-side pose analysis stores derived ratios by default. It is never presented as a diagnosis or medical body-fat scan." },
  { icon: Sparkles, title: "Recommendations you can audit", copy: "Performance and recovery evidence comes first. Every suggestion carries a version, confidence, safety checks and plain-language reason." },
];

export default function LandingPage() {
  return (
    <main className="marketing">
      <nav className="marketing-nav" aria-label="Marketing navigation">
        <Brand />
        <div className="marketing-links">
          <a href="#features">Platform</a>
          <a href="#how">How it works</a>
          <a href="#privacy">Privacy</a>
          <Link href="/login">Sign in</Link>
          <Link href="/register"><Button>Start your journey</Button></Link>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-copy">
          <Eyebrow>The athlete operating system</Eyebrow>
          <h1>Train smarter.<br />Track everything.<br /><span className="gradient-text">Become stronger.</span></h1>
          <p>A personalized command center for bodybuilding, calisthenics, athletic performance, aesthetics and hybrid training—grounded in what you actually do.</p>
          <div className="hero-actions">
            <Link href="/register"><Button>Start your journey <ArrowRight size={17} /></Button></Link>
            <a href="#features"><Button variant="secondary">Explore AthleteOS</Button></a>
          </div>
          <div className="hero-trust">
            <span><ShieldCheck size={15} /> Privacy-first</span>
            <span><Activity size={15} /> Explainable rules</span>
            <span><Check size={15} /> Built for mobile</span>
          </div>
        </div>

        <Card className="product-visual" aria-label="AthleteOS dashboard preview">
          <div className="visual-head"><Brand compact /><span className="pill pill-success"><span className="dot" /> All systems ready</span></div>
          <div className="visual-metrics">
            <div className="visual-metric"><span>Weight trend</span><strong>72.5 <small>kg</small></strong></div>
            <div className="visual-metric"><span>Workout streak</span><strong>22 <small>days</small></strong></div>
            <div className="visual-metric"><span>Water</span><strong>2.6 <small>/ 3 L</small></strong></div>
          </div>
          <div className="visual-grid">
            <Card className="mini-workout">
              <Eyebrow>Today&apos;s workout</Eyebrow><h3 style={{ margin: "8px 0 5px" }}>Push Day</h3><p className="tiny">Chest · shoulders · triceps</p>
              {["Bench Press", "Incline Dumbbell Press", "Shoulder Press", "Triceps Pushdown"].map((exercise, index) => <div className="mini-exercise" key={exercise}><span><i>{index + 1}</i>{exercise}</span><span>{index === 0 ? "4 × 8–10" : "3 × 10–12"}</span></div>)}
            </Card>
            <Card className="mini-ring"><Eyebrow>Fuel</Eyebrow><div className="ring"><strong>78%</strong></div><p className="tiny" style={{ textAlign: "center" }}>1,820 / 2,300 kcal</p></Card>
          </div>
        </Card>
      </section>

      <section className="marketing-section" id="features">
        <div className="section-heading"><Eyebrow>One connected system</Eyebrow><h2>Every log strengthens your next decision.</h2><p>AthleteOS is built around a single loop: assess, plan, execute, log, analyze and adapt.</p></div>
        <div className="feature-grid">
          {features.map(({ icon: Icon, title, copy }) => <Card className="feature-card" key={title}><div className="feature-icon"><Icon size={21} /></div><h3>{title}</h3><p>{copy}</p></Card>)}
        </div>
      </section>

      <section className="marketing-section" id="how">
        <div className="section-heading"><Eyebrow>How it works</Eyebrow><h2>Clarity from day one.</h2></div>
        <div className="how-grid">
          <div className="how-step"><h3>Build your athlete profile</h3><p>Choose your training mode, goal, level, schedule, equipment and baseline metrics in a resumable setup.</p></div>
          <div className="how-step"><h3>Execute the next action</h3><p>Open Today, log sets between exercises, add meals and water, and tick the habits that matter.</p></div>
          <div className="how-step"><h3>Understand what changed</h3><p>See real trends and accept or reject progression suggestions with evidence—not opaque AI instructions.</p></div>
        </div>
      </section>

      <section className="marketing-section" id="privacy">
        <Card className="cta-band">
          <div><Eyebrow>Privacy is part of the product</Eyebrow><h2 style={{ margin: "8px 0" }}>Your body data stays under your control.</h2><p style={{ margin: 0 }}>Visual analysis is optional, derived-only by default and never used for medical claims.</p></div>
          <div className="hero-actions" style={{ marginTop: 0 }}><Link href="/register"><Button>Build my plan <ArrowRight size={17} /></Button></Link><span className="pill"><LockKeyhole size={14} /> No public photos</span></div>
        </Card>
      </section>

      <footer className="marketing-footer"><Brand /><span>© 2026 AthleteOS · Fitness guidance, not medical advice.</span><span><Flame size={14} style={{ display: "inline", verticalAlign: "middle" }} /> Built for consistent athletes.</span></footer>
    </main>
  );
}
