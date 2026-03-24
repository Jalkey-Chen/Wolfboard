"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { LogoutButton } from "@/components/logout-button";
import { getCurrentUser, type CurrentUserResponse } from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";


const roleCards: Record<string, { title: string; description: string; links: string[] }> = {
  admin: {
    title: "Admin Dashboard (placeholder)",
    description: "Management entry point for administration, approvals, and system operations.",
    links: ["Backend Home", "Season Management", "Audit Logs"],
  },
  judge: {
    title: "Judge Dashboard (placeholder)",
    description: "Work queue entry point for the games owned by the current judge.",
    links: ["My Assigned Games", "Result Entry", "Submission Status"],
  },
  player: {
    title: "Player Dashboard (placeholder)",
    description: "Public-facing area for sign-ups, standings, and confirmed match history.",
    links: ["Current Season", "Leaderboard", "My Match History"],
  },
};

const roleOrder = ["admin", "judge", "player"];


export function DashboardShell() {
  const router = useRouter();
  const [profile, setProfile] = useState<CurrentUserResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    void getCurrentUser(token)
      .then((response) => {
        setProfile(response);
        setStatus("ready");
      })
      .catch(() => {
        clearStoredAccessToken();
        setErrorMessage("Your session is invalid or expired. Please sign in again.");
        setStatus("error");
        router.replace("/login");
      });
  }, [router]);

  const orderedRoles = useMemo(() => {
    if (!profile) {
      return [];
    }
    return [...profile.roles].sort((left, right) => roleOrder.indexOf(left) - roleOrder.indexOf(right));
  }, [profile]);

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="rounded-2xl border border-slate-200 bg-white/90 px-8 py-6 shadow-lg shadow-slate-200/60">
          <p className="text-sm font-medium text-slate-600">Loading your dashboard...</p>
        </div>
      </main>
    );
  }

  if (!profile) {
    return null;
  }

  return (
    <main className="min-h-screen px-6 py-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <header className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white/90 p-8 shadow-xl shadow-slate-200/50 md:flex-row md:items-end md:justify-between">
          <div className="space-y-3">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-accent">Wolfboard</p>
            <div>
              <h1 className="text-3xl font-bold text-ink">{profile.user.display_name}</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-600">
                Milestone 1 is active. Authentication is live and the navigation below is derived from your assigned role set.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {orderedRoles.map((role) => (
                <span
                  key={role}
                  className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-gold"
                >
                  {role}
                </span>
              ))}
            </div>
          </div>
          <LogoutButton />
        </header>

        {errorMessage ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {orderedRoles.map((role) => {
            const card = roleCards[role];
            if (!card) {
              return null;
            }

            return (
              <article
                key={role}
                className="rounded-3xl border border-slate-200 bg-white/85 p-6 shadow-lg shadow-slate-200/50"
              >
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">{role}</p>
                <h2 className="mt-3 text-2xl font-bold text-ink">{card.title}</h2>
                <p className="mt-3 text-sm leading-6 text-slate-600">{card.description}</p>
                <ul className="mt-5 space-y-2 text-sm text-slate-700">
                  {card.links.map((link) => (
                    <li key={link} className="rounded-xl bg-slate-50 px-3 py-2">
                      {link}
                    </li>
                  ))}
                </ul>
              </article>
            );
          })}
        </section>
      </div>
    </main>
  );
}
