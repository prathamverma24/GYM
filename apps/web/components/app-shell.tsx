"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, CalendarDays, Dumbbell, LayoutDashboard, LogOut, ScanLine, Settings, SlidersHorizontal, Sparkles, UtensilsCrossed } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { api, ApiError } from "@/lib/api";
import type { User } from "@/types/api";
import { Brand, ErrorState, LoadingState } from "./primitives";

const navigation = [
  ["/dashboard", "Dashboard", LayoutDashboard],
  ["/workouts", "Workouts", Dumbbell],
  ["/exercises", "Exercise library", Sparkles],
  ["/nutrition", "Nutrition", UtensilsCrossed],
  ["/habits", "Habits", SlidersHorizontal],
  ["/progress", "Progress", BarChart3],
  ["/body-scan", "Body Scan", ScanLine],
  ["/calendar", "Calendar", CalendarDays],
  ["/settings", "Settings", Settings],
] as const;

const mobileNavigation = navigation.filter(([href]) => ["/dashboard", "/workouts", "/nutrition", "/progress", "/settings"].includes(href));

function initials(name: string) { return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase(); }

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const userQuery = useQuery({ queryKey: ["me"], queryFn: () => api<{ user: User }>("/auth/me"), retry: false });
  useEffect(() => {
    if (userQuery.error instanceof ApiError && userQuery.error.status === 401) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
    else if (userQuery.data && !userQuery.data.user.onboarding_completed) router.replace("/onboarding");
  }, [userQuery.error, userQuery.data, pathname, router]);
  async function logout() {
    await api("/auth/logout", { method: "POST" });
    queryClient.clear();
    router.replace("/login");
    router.refresh();
  }
  if (userQuery.isLoading || (userQuery.error instanceof ApiError && userQuery.error.status === 401)) {
    return <main className="auth-page"><LoadingState label="Opening AthleteOS…" /></main>;
  }
  if (userQuery.isError) {
    return <main className="auth-page"><ErrorState message={userQuery.error.message} onRetry={() => userQuery.refetch()} /></main>;
  }
  if (!userQuery.data) return <main className="auth-page"><LoadingState label="Opening AthleteOS…" /></main>;
  const user = userQuery.data.user;
  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link href="/dashboard"><Brand /></Link>
        <nav className="nav-group" aria-label="Application navigation">
          {navigation.map(([href, label, Icon]) => <Link href={href} className={`nav-link ${isActive(href) ? "active" : ""}`} key={href}><Icon size={18} />{label}</Link>)}
        </nav>
        <div className="sidebar-spacer" />
        <button className="nav-link" onClick={logout}><LogOut size={18} />Logout</button>
        <div className="sidebar-user"><span className="avatar">{initials(user.full_name)}</span><div><strong>{user.full_name}</strong><small>{user.experience_level?.replaceAll("_", " ") ?? "Athlete"}</small></div></div>
      </aside>
      <nav className="mobile-nav" aria-label="Mobile navigation">{mobileNavigation.map(([href, label, Icon]) => <Link href={href} className={`mobile-link ${isActive(href) ? "active" : ""}`} key={href}><Icon size={19} />{href === "/settings" ? "More" : label}</Link>)}</nav>
      <div className="app-main">{children}</div>
    </div>
  );
}
