"use client";

/**
 * Global language state for the frontend.
 *
 * Chinese is the default experience, while English remains available through a
 * simple toggle that persists to localStorage for subsequent visits.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  DEFAULT_LANGUAGE,
  getLocaleForLanguage,
  getStoredLanguage,
  persistLanguage,
  translate,
  translateEnum,
  type Language,
} from "@/lib/i18n";

type LanguageContextValue = {
  language: Language;
  locale: string;
  setLanguage: (language: Language) => void;
  t: (key: string, values?: Record<string, string | number>) => string;
  enumLabel: (
    group: Parameters<typeof translateEnum>[1],
    value: string | null | undefined,
  ) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(DEFAULT_LANGUAGE);

  useEffect(() => {
    // Client preference is resolved after hydration so the server can keep the
    // default Chinese shell stable for first render.
    setLanguageState(getStoredLanguage());
  }, []);

  useEffect(() => {
    persistLanguage(language);
    // Keeping the root lang attribute in sync improves screen-reader behavior
    // and helps the browser pick the correct locale-specific defaults.
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  }, [language]);

  const contextValue = useMemo<LanguageContextValue>(
    () => ({
      language,
      locale: getLocaleForLanguage(language),
      setLanguage: setLanguageState,
      t: (key, values) => translate(language, key, values),
      enumLabel: (group, value) => translateEnum(language, group, value),
    }),
    [language],
  );

  return (
    <LanguageContext.Provider value={contextValue}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useI18n(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useI18n must be used within a LanguageProvider.");
  }

  return context;
}
