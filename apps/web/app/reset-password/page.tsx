"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { Button } from "@/components/primitives";
import { AuthShell } from "@/features/auth/auth-shell";
import { api } from "@/lib/api";

function ResetForm() {
  const params = useSearchParams();
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true);
    try { const result = await api<{ message: string }>("/auth/reset-password", { method: "POST", body: JSON.stringify({ token: params.get("token") ?? "", password }) }); setMessage(result.message); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Unable to reset password."); }
    finally { setLoading(false); }
  }
  return <form className="form-stack" onSubmit={submit}><label className="field"><span>New password</span><input className="input" type="password" minLength={10} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="10+ characters" /></label>{message && <p className="tiny">{message}</p>}<Button className="button-wide" disabled={loading}>{loading ? "Updating…" : "Update password"}</Button></form>;
}

export default function ResetPasswordPage() {
  return <AuthShell title="Choose a new password" subtitle="This will sign out your existing sessions" footer={<Link href="/login">Back to login</Link>}><Suspense fallback={<p className="tiny">Loading secure reset…</p>}><ResetForm /></Suspense></AuthShell>;
}

