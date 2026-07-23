"use client";

import { useI18n } from "@/components/language-provider";


export function EventProvenanceLink({
  eventId,
  onOpenEvent,
}: {
  eventId: number;
  onOpenEvent: (eventId: number) => void;
}) {
  const { t } = useI18n();
  return (
    <button
      className="rounded px-1 py-0.5 font-mono text-xs font-semibold text-sky-800 underline decoration-sky-300 underline-offset-2 focus:outline-none focus:ring-2 focus:ring-sky-500"
      onClick={() => onOpenEvent(eventId)}
      type="button"
    >
      {t("derivedState.openEvent", { id: eventId })}
    </button>
  );
}
