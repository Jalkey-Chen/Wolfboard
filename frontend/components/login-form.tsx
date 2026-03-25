"use client";

/**
 * Login form for Milestone 1.
 *
 * The browser stores the JWT in localStorage for simplicity. This is adequate
 * for the scaffold phase and can later be replaced with a more hardened cookie
 * strategy without changing the backend auth contract.
 */
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { LanguageSwitcher } from "@/components/language-switcher";
import { useI18n } from "@/components/language-provider";
import { login } from "@/lib/api";
import { getStoredAccessToken, setStoredAccessToken } from "@/lib/auth";


export function LoginForm() {
  const router = useRouter();
  const { t } = useI18n();
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
      setErrorMessage(error instanceof Error ? error.message : t("auth.loginFailed"));
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="grid w-full max-w-5xl gap-8 rounded-[2rem] border border-slate-200 bg-white/90 p-8 shadow-2xl shadow-slate-200/60 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-[1.5rem] bg-gradient-to-br from-slate-950 via-slate-900 to-red-950 p-8 text-white">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-amber-300">{t("brand.name")}</p>
            <LanguageSwitcher />
          </div>
          <h1 className="mt-6 max-w-md text-4xl font-bold leading-tight">
            {t("login.heroTitle")}
          </h1>
          <p className="mt-4 max-w-lg text-sm leading-6 text-slate-200">
            {t("login.heroDescription")}
          </p>
          <div className="mt-8 grid gap-3 text-sm text-slate-100">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              {t("login.seedAdmin")}
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              {t("login.seedJudge")}
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              {t("login.seedPlayer")}
            </div>
          </div>
        </section>

        <section className="flex flex-col justify-center rounded-[1.5rem] bg-slate-50 p-8">
          <div className="mb-8">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-accent">{t("auth.signIn")}</p>
            <h2 className="mt-3 text-3xl font-bold text-ink">{t("auth.signInTitle")}</h2>
            <p className="mt-2 text-sm text-slate-600">
              {t("login.subtitle")}
            </p>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">{t("auth.username")}</span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder={t("auth.usernamePlaceholder")}
                required
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">{t("auth.password")}</span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={t("auth.passwordPlaceholder")}
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
              {submitting ? t("auth.signingIn") : t("auth.signIn")}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
