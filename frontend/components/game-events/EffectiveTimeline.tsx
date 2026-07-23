"use client";

import { EventCard } from "@/components/game-events/EventCard";
import { useI18n } from "@/components/language-provider";
import type { GameEventRecord } from "@/lib/api";
import type { ParticipantOption } from "@/lib/game-events/form-types";


type TimelineProps = {
  events: GameEventRecord[];
  participants: ParticipantOption[];
  editable: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  onCorrect: (event: GameEventRecord) => void;
  onVoid: (event: GameEventRecord) => void;
  onInspectState: (event: GameEventRecord) => void;
  highlightedEventId?: number | null;
};

export function EffectiveTimeline(props: TimelineProps) {
  const { t, enumLabel } = useI18n();
  const groups = props.events.reduce<Array<{ key: string; round: number; phase: GameEventRecord["phase"]; events: GameEventRecord[] }>>((items, event) => {
    const key = `${event.round_no}-${event.phase}`;
    const group = items.at(-1);
    if (!group || group.key !== key) items.push({ key, round: event.round_no, phase: event.phase, events: [event] });
    else group.events.push(event);
    return items;
  }, []);

  if (props.events.length === 0) return <div className="border border-dashed border-slate-300 p-6 text-sm text-slate-600">{t("eventWorkbench.noEffectiveEvents")}</div>;
  return (
    <div className="space-y-5">
      {groups.map((group) => (
        <section key={group.key} aria-labelledby={`group-${group.key}`}>
          <h3 className="mb-2 border-b border-slate-300 pb-2 text-sm font-bold text-slate-700" id={`group-${group.key}`}>
            {t("eventWorkbench.roundLabel", { round: group.round })} · {enumLabel("gameEventPhase", group.phase)}
          </h3>
          <div className="space-y-2">
            {group.events.map((event) => <EventCard editable={props.editable} event={event} highlighted={props.highlightedEventId === event.id} key={event.id} onCorrect={props.onCorrect} onInspectState={props.onInspectState} onVoid={props.onVoid} participants={props.participants} />)}
          </div>
        </section>
      ))}
      {props.hasMore ? <button className="w-full rounded-md border border-slate-300 px-4 py-3 text-sm font-semibold" disabled={props.loadingMore} onClick={props.onLoadMore} type="button">{props.loadingMore ? t("common.loading") : t("eventWorkbench.loadMore")}</button> : null}
    </div>
  );
}
