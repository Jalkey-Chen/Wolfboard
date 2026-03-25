"use client";

/** Shared loading and error blocks for data-driven pages. */

import { useI18n } from "@/components/language-provider";

export function PageLoading({ message }: { message?: string }) {
  const { t } = useI18n();

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="rounded-2xl border border-slate-200 bg-white/90 px-8 py-6 shadow-lg shadow-slate-200/60">
        <p className="text-sm font-medium text-slate-600">{message ?? t("common.loading")}</p>
      </div>
    </main>
  );
}


export function PageError({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {message}
    </div>
  );
}
