"use client";

import { useEffect, useRef, useState } from "react";

import { useI18n } from "@/components/language-provider";
import type { GameEventRecord } from "@/lib/api";


type VoidEventDialogProps = {
  event: GameEventRecord;
  busy: boolean;
  error: string | null;
  onConfirm: (reason: string) => void;
  onClose: () => void;
};

export function VoidEventDialog({ event, busy, error, onConfirm, onClose }: VoidEventDialogProps) {
  const { t, enumLabel } = useI18n();
  const [reason, setReason] = useState("");
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    reasonRef.current?.focus();
    function escape(keyEvent: KeyboardEvent) {
      if (keyEvent.key === "Escape" && !busy) onClose();
    }
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [busy, onClose]);
  const highImpact = ["player_died", "player_exiled", "wolf_king_shot"].includes(event.event_type);

  return (
    <div aria-labelledby="void-event-title" aria-modal="true" className="fixed inset-0 z-50 flex items-end bg-slate-950/60 p-0 sm:items-center sm:justify-center sm:p-6" role="dialog">
      <div className="w-full max-w-lg bg-white p-5 shadow-2xl sm:rounded-lg">
        <h2 className="text-xl font-bold text-slate-900" id="void-event-title">{t("eventWorkbench.voidEvent")}</h2>
        <p className="mt-2 text-sm text-slate-600">#{event.sequence_no} · {enumLabel("gameEventType", event.event_type)}</p>
        <div className="mt-4 border-l-4 border-amber-500 bg-amber-50 px-3 py-3 text-sm text-amber-900">
          {t("eventWorkbench.voidWarning")}{highImpact ? ` ${t("eventWorkbench.highImpactWarning")}` : ""}
        </div>
        {error ? <div className="mt-3 bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</div> : null}
        <label className="mt-4 block text-sm font-semibold text-slate-800" htmlFor="void-reason">
          {t("common.reason")} <span className="text-red-600">*</span>
          <textarea className="mt-2 min-h-24 w-full rounded-md border border-slate-300 px-3 py-2 text-base" disabled={busy} id="void-reason" onChange={(changeEvent) => setReason(changeEvent.target.value)} ref={reasonRef} value={reason} />
        </label>
        <div className="mt-5 flex justify-end gap-2">
          <button className="min-h-11 rounded-md border border-slate-300 px-4 text-sm font-semibold" disabled={busy} onClick={onClose} type="button">{t("common.cancel")}</button>
          <button className="min-h-11 rounded-md bg-red-800 px-4 text-sm font-bold text-white disabled:bg-slate-400" disabled={busy || !reason.trim()} onClick={() => onConfirm(reason.trim())} type="button">{busy ? t("eventWorkbench.saving") : t("eventWorkbench.confirmVoid")}</button>
        </div>
      </div>
    </div>
  );
}
