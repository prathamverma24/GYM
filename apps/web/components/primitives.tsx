import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

export function Button({ className = "", variant = "primary", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" }) {
  return <button className={`button button-${variant} ${className}`} {...props} />;
}

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`card ${className}`} {...props} />;
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <span className="eyebrow">{children}</span>;
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <span className={`brand ${compact ? "brand-compact" : ""}`}>
      <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /><i /></span>
      {!compact && <span>Athlete<span>OS</span></span>}
    </span>
  );
}

export function LoadingState({ label = "Loading your data…" }: { label?: string }) {
  return <div className="state-card" role="status"><span className="spinner" />{label}</div>;
}

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return <div className="state-card state-error"><p>{message ?? "Something went wrong."}</p>{onRetry && <Button variant="secondary" onClick={onRetry}>Try again</Button>}</div>;
}

export function EmptyState({ icon, title, message, action }: { icon?: ReactNode; title: string; message: string; action?: ReactNode }) {
  return <Card className="empty-state"><div className="empty-icon">{icon}</div><h3>{title}</h3><p>{message}</p>{action}</Card>;
}

export function MetricCard({ label, value, unit, note, accent = "violet" }: { label: string; value: ReactNode; unit?: string; note?: string; accent?: "violet" | "pink" | "orange" | "blue" }) {
  return <Card className={`metric-card accent-${accent}`}><span>{label}</span><strong>{value}<small>{unit}</small></strong>{note && <p>{note}</p>}</Card>;
}

