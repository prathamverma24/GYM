"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/primitives";
import { AuthShell } from "@/features/auth/auth-shell";
import { api } from "@/lib/api";
import type { User } from "@/types/api";

const schema = z.object({
  full_name: z.string().min(2, "Enter your full name").max(120),
  email: z.email("Enter a valid email"),
  password: z.string().min(10, "Use at least 10 characters").regex(/[A-Z]/, "Add an uppercase letter").regex(/\d/, "Add a number"),
  confirm_password: z.string(),
  accept_terms: z.literal(true, { error: "Accept the Terms and Privacy Notice" }),
}).refine((value) => value.password === value.confirm_password, { path: ["confirm_password"], message: "Passwords do not match" });
type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState("");
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({ resolver: zodResolver(schema) });
  const onSubmit = handleSubmit(async (values) => {
    setServerError("");
    try {
      const result = await api<{ user: User }>("/auth/register", { method: "POST", body: JSON.stringify(values) });
      queryClient.setQueryData(["me"], result);
      queryClient.removeQueries({ queryKey: ["onboarding"] });
      router.replace("/onboarding");
      router.refresh();
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Unable to create your account.");
    }
  });
  return (
    <AuthShell title="Create your account" subtitle="Start your transformation today" footer={<>Already have an account? <Link href="/login">Login</Link></>}>
      <form className="form-stack" onSubmit={onSubmit}>
        <label className="field"><span>Full name</span><input className="input" autoComplete="name" placeholder="Your name" {...register("full_name")} />{errors.full_name && <small className="field-error">{errors.full_name.message}</small>}</label>
        <label className="field"><span>Email</span><input className="input" type="email" autoComplete="email" placeholder="you@example.com" {...register("email")} />{errors.email && <small className="field-error">{errors.email.message}</small>}</label>
        <label className="field"><span>Password</span><input className="input" type="password" autoComplete="new-password" placeholder="10+ characters, uppercase and number" {...register("password")} />{errors.password && <small className="field-error">{errors.password.message}</small>}</label>
        <label className="field"><span>Confirm password</span><input className="input" type="password" autoComplete="new-password" placeholder="Repeat your password" {...register("confirm_password")} />{errors.confirm_password && <small className="field-error">{errors.confirm_password.message}</small>}</label>
        <label className="checkbox"><input type="checkbox" {...register("accept_terms")} /><span>I agree to the Terms and Privacy Notice. Optional analytics and body-scan consent are handled separately.</span></label>
        {errors.accept_terms && <small className="field-error">{errors.accept_terms.message}</small>}
        {serverError && <div className="field-error" role="alert">{serverError}</div>}
        <Button className="button-wide" disabled={isSubmitting}>{isSubmitting ? "Creating account…" : "Sign up"}</Button>
      </form>
    </AuthShell>
  );
}
