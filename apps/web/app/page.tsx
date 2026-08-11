import {
  ArrowRight,
  BarChart3,
  CirclePlay,
  Dumbbell,
  Footprints,
  LockKeyhole,
  Salad,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Target,
  Trophy,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { LandingDashboard } from "@/components/landing-dashboard";
import { Brand, Button, Card, Eyebrow } from "@/components/primitives";

const features = [
  { icon: Dumbbell, title: "Training that fits your reality", copy: "Your mode, level, schedule and equipment become a deterministic weekly program with a clear reason behind every choice." },
  { icon: Salad, title: "Indian-first nutrition logging", copy: "Find aloo matar, bhindi, dal, poha and regional aliases quickly—with household servings and transparent estimate labels." },
  { icon: Target, title: "Consistency you can see", copy: "A schedule-aware habit matrix, water tracker and streaks that understand planned rest days rather than punishing them." },
  { icon: BarChart3, title: "Progress without noise", copy: "Weekly and monthly views connect completed sessions, body metrics, nutrition and habits without turning missing data into zero." },
  { icon: ScanLine, title: "Privacy-first visual progress", copy: "Optional browser-side pose analysis stores derived ratios by default. It is never presented as a diagnosis or medical body-fat scan." },
  { icon: Sparkles, title: "Recommendations you can audit", copy: "Performance and recovery evidence comes first. Every suggestion carries a version, confidence, safety checks and plain-language reason." },
];

const heroFeatures = [
  { icon: Target, title: "Personalized workouts", copy: "Plans that adapt to you" },
  { icon: Salad, title: "Nutrition tracking", copy: "Log meals. Hit goals." },
  { icon: Trophy, title: "Habit builder", copy: "Stay consistent daily" },
  { icon: BarChart3, title: "Progress insights", copy: "Data that drives results" },
  { icon: ScanLine, title: "Body scan", copy: "Visualize your transformation" },
  { icon: Sparkles, title: "Smart recommendations", copy: "Evidence-led guidance" },
];

export default function LandingPage() {
  return (
    <main className="marketing">
      <section className="landing-hero" aria-labelledby="landing-title">
        <Image
          alt=""
          className="landing-hero-bg"
          fill
          priority
          sizes="100vw"
          src="/assets/landing-hero-bg-v2.png"
        />
        <div className="landing-hero-shade" />

        <nav className="landing-nav" aria-label="Marketing navigation">
          <Link className="landing-brand" href="/" aria-label="AthleteOS home">
            <Image src="/icon.svg" width={42} height={42} alt="" />
            <span>Athlete<span>OS</span></span>
          </Link>
          <div className="landing-nav-links">
            <a href="#features">Features</a>
            <a href="#how">How it works</a>
            <Link href="/register">Pricing</Link>
            <a href="#how">Testimonials</a>
            <a href="#privacy">About us</a>
          </div>
          <div className="landing-nav-actions">
            <Link href="/login">Log in</Link>
            <Link className="landing-nav-cta" href="/register">Start free trial</Link>
          </div>
        </nav>

        <div className="landing-hero-content">
          <div className="landing-copy">
            <span className="landing-kicker">Your fitness. Your data. Your best self.</span>
            <h1 id="landing-title">
              Train Smarter.<br />
              Track Everything.<br />
              <span>Become Elite.</span>
            </h1>
            <p>AthleteOS is your all-in-one fitness operating system. Personalized workouts, nutrition tracking, habit building and advanced progress insights—all in one place.</p>
            <div className="landing-actions">
              <Link className="landing-primary-cta" href="/register">Start your journey <ArrowRight size={18} /></Link>
              <a className="landing-secondary-cta" href="#features">Explore AthleteOS <CirclePlay size={17} /></a>
            </div>
            <div className="landing-trust">
              <span><Target size={18} /> Personalized plans</span>
              <span><BarChart3 size={18} /> Smart tracking</span>
              <span><Trophy size={18} /> Real progress</span>
              <span><ShieldCheck size={18} /> Backed by science</span>
            </div>
          </div>

          <LandingDashboard />
        </div>

        <div className="landing-feature-rail" aria-label="AthleteOS platform highlights">
          {heroFeatures.map(({ icon: Icon, title, copy }) => (
            <a href="#features" key={title}>
              <span className="landing-feature-icon"><Icon size={22} /></span>
              <span><strong>{title}</strong><small>{copy}</small></span>
            </a>
          ))}
        </div>
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

      <footer className="marketing-footer"><Brand /><span>© 2026 AthleteOS · Fitness guidance, not medical advice.</span><span><Footprints size={14} style={{ display: "inline", verticalAlign: "middle" }} /> Built for consistent athletes.</span></footer>
    </main>
  );
}
