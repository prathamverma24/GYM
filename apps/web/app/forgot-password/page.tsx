"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { Button } from "@/components/primitives";
import { AuthShell } from "@/features/auth/auth-shell";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [debugToken, setDebugToken] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true);
    try {
      const result = await api<{ message: string; development_reset_token?: string }>("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
      setMessage(result.message); setDebugToken(result.development_reset_token ?? "");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to submit request."); }
    finally { setLoading(false); }
  }
  return <AuthShell title="Reset your password" subtitle="We’ll send secure instructions if the account exists" footer={<Link href="/login">Back to login</Link>}><form className="form-stack" onSubmit={submit}><label className="field"><span>Email</span><input className="input" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>{message && <p className="tiny" role="status">{message}</p>}{debugToken && <Link className="text-link" href={`/reset-password?token=${encodeURIComponent(debugToken)}`}>Open local development reset link</Link>}<Button className="button-wide" disabled={loading}>{loading ? "Sending…" : "Send reset instructions"}</Button></form></AuthShell>;
}

