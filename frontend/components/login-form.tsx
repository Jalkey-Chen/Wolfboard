"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { login } from "@/lib/api";
import { getStoredAccessToken, setStoredAccessToken } from "@/lib/auth";


export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (getStoredAccessToken()) {
      router.replace("/");
    }
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await login(username, password);
      setStoredAccessToken(response.access_token);
      router.replace("/");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Login failed.");
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="grid w-full max-w-5xl gap-8 rounded-[2rem] border border-slate-200 bg-white/90 p-8 shadow-2xl shadow-slate-200/60 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-[1.5rem] bg-gradient-to-br from-slate-950 via-slate-900 to-red-950 p-8 text-white">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-amber-300">Wolfboard</p>
          <h1 className="mt-6 max-w-md text-4xl font-bold leading-tight">
            Werewolf tournament operations, starting with secure multi-role access.
          </h1>
          <p className="mt-4 max-w-lg text-sm leading-6 text-slate-200">
            Milestone 1 provides the project scaffold, PostgreSQL-backed authentication, JWT access tokens, and role-aware entry points for admins, judges, and players.
          </p>
          <div className="mt-8 grid gap-3 text-sm text-slate-100">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <code className="rounded bg-white/10 px-1.5 py-0.5">admin_user</code> includes admin, judge, and player permissions.
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <code className="rounded bg-white/10 px-1.5 py-0.5">judge_user</code> includes judge and player permissions.
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <code className="rounded bg-white/10 px-1.5 py-0.5">player_user</code> includes player permissions only.
            </div>
          </div>
        </section>

        <section className="flex flex-col justify-center rounded-[1.5rem] bg-slate-50 p-8">
          <div className="mb-8">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-accent">Sign In</p>
            <h2 className="mt-3 text-3xl font-bold text-ink">Access the platform</h2>
            <p className="mt-2 text-sm text-slate-600">
              Use one of the seeded accounts or create more users through the backend later.
            </p>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">Username</span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="admin_user"
                required
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">Password</span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="password123"
                required
              />
            </label>

            {errorMessage ? (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {errorMessage}
              </div>
            ) : null}

            <button
              className="w-full rounded-2xl bg-ink px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-500"
              disabled={submitting}
              type="submit"
            >
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
