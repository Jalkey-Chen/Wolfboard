"use client";

import { EventProvenanceLink } from "@/components/game-state/EventProvenanceLink";
import { useI18n } from "@/components/language-provider";
import type { GameDerivedParticipantState, GameDerivedSheriffState } from "@/lib/api";


function participantLabel(participants: GameDerivedParticipantState[], id: number | null): string {
  const participant = participants.find((item) => item.participant_id === id);
  if (!participant) return id === null ? "" : `#${id}`;
  return `${participant.seat_number ?? "?"} · ${participant.display_name_snapshot ?? `#${id}`}`;
}

export function SheriffStateCard({
  sheriff,
  participants,
  onOpenEvent,
}: {
  sheriff: GameDerivedSheriffState;
  participants: GameDerivedParticipantState[];
  onOpenEvent: (eventId: number) => void;
}) {
  const { t } = useI18n();
  const holder = participantLabel(participants, sheriff.current_sheriff_participant_id);
  const status = sheriff.badge_status === "held"
    ? t("derivedState.sheriff.held", { participant: holder })
    : sheriff.badge_status === "destroyed"
      ? t("derivedState.sheriff.destroyed")
      : t("derivedState.sheriff.unassigned");
  return (
    <section aria-labelledby="derived-sheriff-heading" className="border-b border-slate-200 py-5">
      <h3 className="text-base font-bold text-slate-950" id="derived-sheriff-heading">{t("derivedState.sheriff.title")}</h3>
      <p className="mt-3 text-lg font-bold text-slate-900">{status}</p>
      <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
        <div><span className="font-semibold text-slate-500">{t("derivedState.sheriff.electedEvent")}</span><div className="mt-1">{sheriff.elected_event_id ? <EventProvenanceLink eventId={sheriff.elected_event_id} onOpenEvent={onOpenEvent} /> : t("common.none")}</div></div>
        <div><span className="font-semibold text-slate-500">{t("derivedState.sheriff.transferEvent")}</span><div className="mt-1">{sheriff.last_transfer_event_id ? <EventProvenanceLink eventId={sheriff.last_transfer_event_id} onOpenEvent={onOpenEvent} /> : t("common.none")}</div></div>
        <div><span className="font-semibold text-slate-500">{t("derivedState.sheriff.destroyedEvent")}</span><div className="mt-1">{sheriff.destroyed_event_id ? <EventProvenanceLink eventId={sheriff.destroyed_event_id} onOpenEvent={onOpenEvent} /> : t("common.none")}</div></div>
        <div><span className="font-semibold text-slate-500">{t("derivedState.sheriff.candidates")}</span><div className="mt-1">{sheriff.current_candidate_participant_ids.map((id) => participantLabel(participants, id)).join(", ") || t("common.none")}</div></div>
        <div><span className="font-semibold text-slate-500">{t("derivedState.sheriff.withdrawn")}</span><div className="mt-1">{sheriff.withdrawn_participant_ids.map((id) => participantLabel(participants, id)).join(", ") || t("common.none")}</div></div>
      </div>
      <p className="mt-3 text-xs text-slate-600">{t("derivedState.sheriff.explicitOnly")}</p>
    </section>
  );
}
