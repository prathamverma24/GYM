"use client";

import { useQuery } from "@tanstack/react-query";
import { Database, Dumbbell, ShieldAlert, UsersRound } from "lucide-react";

import { Card, ErrorState, LoadingState, MetricCard } from "@/components/primitives";
import { api } from "@/lib/api";

export default function AdminPage() {
  const admin = useQuery({ queryKey: ["admin-overview"], queryFn: () => api<{ users: number; foods: number; exercises: number; catalogue_version: string; jobs: { failed: number; queued: number } }>("/admin/overview"), retry: false });
  if (admin.isLoading) return <LoadingState label="Validating administrator scope…" />; if (admin.isError || !admin.data) return <ErrorState message={admin.error instanceof Error ? admin.error.message : "Administrator access is required."} />;
  return <><header className="page-head"><div><span className="eyebrow">Restricted operations</span><h1>Admin dashboard</h1><p>Catalogue and job diagnostics. Sensitive media is never visible by default.</p></div></header><section className="grid metric-grid"><MetricCard label="Athletes" value={admin.data.users} /><MetricCard label="Foods" value={admin.data.foods} accent="orange" /><MetricCard label="Exercises" value={admin.data.exercises} accent="pink" /><MetricCard label="Failed jobs" value={admin.data.jobs.failed} accent="blue" /></section><div className="report-grid" style={{ marginTop: 16 }}><Card className="report-card"><span className="eyebrow"><Database size={13} style={{ display: "inline" }} /> Catalogue</span><p className="tiny" style={{ marginTop: 15 }}>Published snapshot: {admin.data.catalogue_version}. Food imports require licensing metadata, validation and reviewed publish.</p></Card><Card className="report-card"><span className="eyebrow"><ShieldAlert size={13} style={{ display: "inline" }} /> Access boundary</span><p className="tiny" style={{ marginTop: 15 }}><UsersRound size={13} style={{ display: "inline" }} /> User support, catalogue publishing and operations roles should be separated before production. <Dumbbell size={13} style={{ display: "inline" }} /></p></Card></div></>;
}

