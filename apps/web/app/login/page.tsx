"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/primitives";
import { AuthShell } from "@/features/auth/auth-shell";
import { api } from "@/lib/api";
import type { User } from "@/types/api";

const schema = z.object({ email: z.email("Enter a valid email"), password: z.string().min(1, "Enter your password") });
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState("");
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (values) => {
    setServerError("");
    try {
      const result = await api<{ user: User }>("/auth/login", { method: "POST", body: JSON.stringify(values) });
      queryClient.setQueryData(["me"], result);
      queryClient.removeQueries({ queryKey: ["onboarding"] });
      router.replace(result.user.onboarding_completed ? "/dashboard" : "/onboarding");
      router.refresh();
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Unable to sign in.");
    }
  });

  return (
    <AuthShell title="Welcome back!" subtitle="Log in to continue your fitness journey" footer={<>Don&apos;t have an account? <Link href="/register">Sign up</Link></>}>
      <form className="form-stack" onSubmit={onSubmit}>
        <label className="field"><span>Email</span><input className="input" type="email" autoComplete="email" placeholder="you@example.com" {...register("email")} />{errors.email && <small className="field-error">{errors.email.message}</small>}</label>
        <label className="field"><span>Password</span><div className="input-suffix"><input className="input" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Your password" {...register("password")} /><button className="icon-button" style={{ position: "absolute", right: 4, top: 4 }} type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></div>{errors.password && <small className="field-error">{errors.password.message}</small>}<span className="form-helper"><span /><Link className="text-link" href="/forgot-password">Forgot password?</Link></span></label>
        {serverError && <div className="field-error" role="alert">{serverError}</div>}
        <Button className="button-wide" disabled={isSubmitting}>{isSubmitting ? "Signing in…" : "Login"}</Button>
      </form>
    </AuthShell>
  );
}
