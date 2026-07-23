"use client";

import { useMemo, useState } from "react";

import { EventCard } from "@/components/game-events/EventCard";
import { useI18n } from "@/components/language-provider";
import type { GameEventPhase, GameEventRecord, GameEventStatus, GameEventType } from "@/lib/api";
import type { ParticipantOption } from "@/lib/game-events/form-types";


type LedgerProps = {
  events: GameEventRecord[];
  participants: ParticipantOption[];
  editable: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  onCorrect: (event: GameEventRecord) => void;
  onVoid: (event: GameEventRecord) => void;
};

function referencesParticipant(event: GameEventRecord, participantId: number): boolean {
  if ([event.actor_participant_id, event.target_participant_id, event.secondary_target_participant_id].includes(participantId)) {
    return true;
  }
  return ["candidate_participant_ids", "eligible_participant_ids"].some((field) => {
    const value = event.payload[field];
    return Array.isArray(value) && value.includes(participantId);
  });
}

export function EventLedger(props: LedgerProps) {
  const { t, enumLabel } = useI18n();
  const [status, setStatus] = useState<GameEventStatus | "all">("all");
  const [phase, setPhase] = useState<GameEventPhase | "all">("all");
  const [type, setType] = useState<GameEventType | "all">("all");
  const [participant, setParticipant] = useState<number | "all">("all");
  const [round, setRound] = useState("");
  const filtered = useMemo(() => props.events.filter((event) =>
    (status === "all" || event.status === status) &&
    (phase === "all" || event.phase === phase) &&
    (type === "all" || event.event_type === type) &&
    (!round || event.round_no === Number(round)) &&
    (participant === "all" || referencesParticipant(event, participant)),
  ), [participant, phase, props.events, round, status, type]);

  return (
    <div>
      <p className="mb-3 text-xs text-slate-500">{t("eventWorkbench.loadedFilterHint")}</p>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
        <select aria-label={t("common.status")} className="rounded-md border border-slate-300 px-2 py-2 text-sm" onChange={(event) => setStatus(event.target.value as GameEventStatus | "all")} value={status}>
          <option value="all">{t("common.status")}</option>
          {(["active", "superseded", "voided"] as GameEventStatus[]).map((item) => <option key={item} value={item}>{enumLabel("gameEventStatus", item)}</option>)}
        </select>
        <select aria-label={t("eventWorkbench.phase")} className="rounded-md border border-slate-300 px-2 py-2 text-sm" onChange={(event) => setPhase(event.target.value as GameEventPhase | "all")} value={phase}>
          <option value="all">{t("eventWorkbench.phase")}</option>
          {(["night", "day"] as GameEventPhase[]).map((item) => <option key={item} value={item}>{enumLabel("gameEventPhase", item)}</option>)}
        </select>
        <select aria-label={t("eventWorkbench.eventType")} className="rounded-md border border-slate-300 px-2 py-2 text-sm" onChange={(event) => setType(event.target.value as GameEventType | "all")} value={type}>
          <option value="all">{t("eventWorkbench.eventType")}</option>
          {[...new Set(props.events.map((event) => event.event_type))].map((item) => <option key={item} value={item}>{enumLabel("gameEventType", item)}</option>)}
        </select>
        <select aria-label={t("common.player")} className="rounded-md border border-slate-300 px-2 py-2 text-sm" onChange={(event) => setParticipant(event.target.value ? Number(event.target.value) : "all")} value={participant === "all" ? "" : participant}>
          <option value="">{t("common.player")}</option>
          {props.participants.map((item) => <option key={item.participantId} value={item.participantId}>{item.seatNumber ?? "?"} · {item.displayName}</option>)}
        </select>
        <input aria-label={t("eventWorkbench.round")} className="rounded-md border border-slate-300 px-2 py-2 text-sm" min={1} onChange={(event) => setRound(event.target.value)} placeholder={t("eventWorkbench.round")} type="number" value={round} />
      </div>
      <div className="mt-4 space-y-2">
        {filtered.map((event) => <EventCard editable={props.editable} event={event} key={event.id} ledger onCorrect={props.onCorrect} onVoid={props.onVoid} participants={props.participants} />)}
        {filtered.length === 0 ? <div className="border border-dashed border-slate-300 p-6 text-sm text-slate-600">{t("common.noData")}</div> : null}
      </div>
      {props.hasMore ? <button className="mt-4 w-full rounded-md border border-slate-300 px-4 py-3 text-sm font-semibold" disabled={props.loadingMore} onClick={props.onLoadMore} type="button">{props.loadingMore ? t("common.loading") : t("eventWorkbench.loadMore")}</button> : null}
    </div>
  );
}
