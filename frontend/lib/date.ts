/** Small date helpers for display and form binding. */

import { getLocaleForLanguage, getStoredLanguage } from "@/lib/i18n";

function parseDateValue(value: string): Date {
  const dateOnlyMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnlyMatch) {
    return new Date(
      Number(dateOnlyMatch[1]),
      Number(dateOnlyMatch[2]) - 1,
      Number(dateOnlyMatch[3]),
    );
  }

  return new Date(value);
}

function resolveLocale(): string {
  return getLocaleForLanguage(getStoredLanguage());
}

export function formatDate(value: string | null): string {
  if (!value) {
    return getStoredLanguage() === "zh" ? "未设置" : "Not set";
  }

  return new Intl.DateTimeFormat(resolveLocale(), {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(parseDateValue(value));
}


export function formatDateTime(value: string | null): string {
  if (!value) {
    return getStoredLanguage() === "zh" ? "未设置" : "Not set";
  }

  return new Intl.DateTimeFormat(resolveLocale(), {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(parseDateValue(value));
}


export function toDateInputValue(value: string | null): string {
  return value ? value.slice(0, 10) : "";
}


export function toDateTimeLocalValue(value: string | null): string {
  return value ? value.slice(0, 16) : "";
}
