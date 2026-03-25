"use client";

/** Compact language toggle shared by login and authenticated pages. */

import { useI18n } from "@/components/language-provider";

export function LanguageSwitcher() {
  const { language, setLanguage, t } = useI18n();

  return (
    <div className="inline-flex rounded-full border border-slate-300 bg-white p-1 shadow-sm">
      {(["zh", "en"] as const).map((option) => {
        const isActive = language === option;
        return (
          <button
            key={option}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
              isActive
                ? "bg-ink text-white"
                : "text-slate-600 hover:bg-slate-100"
            }`}
            onClick={() => setLanguage(option)}
            type="button"
          >
            {t(`language.${option}`)}
          </button>
        );
      })}
    </div>
  );
}
