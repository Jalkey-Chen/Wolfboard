"use client";

import { EventProvenanceLink } from "@/components/game-state/EventProvenanceLink";
import { useI18n } from "@/components/language-provider";
import type { GameDerivedBallotState, GameDerivedParticipantState } from "@/lib/api";
import { selectBallots, uniqueProvenanceEventIds } from "@/lib/game-state/selectors";


function participantLabel(participants: GameDerivedParticipantState[], id: number | null): string {
  if (id === null) return "-";
  const participant = participants.find((item) => item.participant_id === id);
  return participant ? `${participant.seat_number ?? "?"} · ${participant.display_name_snapshot ?? `#${id}`}` : `#${id}`;
}

function tallyText(entries: GameDerivedBallotState["raw_tally"], participants: GameDerivedParticipantState[]): string {
  return entries.map((entry) => `${participantLabel(participants, entry.participant_id)}: ${entry.vote_weight}`).join(" · ");
}

export function BallotSummaryList({
  ballots,
  participants,
  onOpenEvent,
}: {
  ballots: GameDerivedBallotState[];
  participants: GameDerivedParticipantState[];
  onOpenEvent: (eventId: number) => void;
}) {
  const { t } = useI18n();
  const ordered = selectBallots(ballots);
  return (
    <section aria-labelledby="derived-ballots-heading" className="border-b border-slate-200 py-5">
      <h3 className="text-base font-bold text-slate-950" id="derived-ballots-heading">{t("derivedState.ballots.title")}</h3>
      <div className="mt-4 space-y-3">
        {ordered.map((ballot) => {
          const provenance = uniqueProvenanceEventIds(
            ballot.vote_event_ids,
            ballot.explicit_tie_records.map((item) => item.event_id),
            ballot.revote_records.map((item) => item.event_id),
            ballot.explicit_outcome_event_ids,
          );
          return (
            <details className="rounded-md border border-slate-200 p-4" key={`${ballot.vote_kind}-${ballot.round_no}-${ballot.ballot_no}`}>
              <summary className="cursor-pointer font-bold text-slate-900">
                {t("derivedState.ballots.summary", {
                  kind: t(`derivedState.ballots.kind.${ballot.vote_kind}`),
                  round: ballot.round_no,
                  ballot: ballot.ballot_no,
                })}
              </summary>
              <div className="mt-4 space-y-3 text-sm">
                <div>
                  <p className="font-semibold text-slate-600">{t("derivedState.ballots.rawTally")}</p>
                  <p className="mt-1">{tallyText(ballot.raw_tally, participants) || t("common.none")}</p>
                </div>
                <div>
                  <p className="font-semibold text-slate-600">{t("derivedState.ballots.computedTally")}</p>
                  {ballot.tally_is_unambiguous && ballot.computed_tally ? (
                    <p className="mt-1">{t("derivedState.ballots.computedHint")}: {tallyText(ballot.computed_tally, participants) || t("common.none")}</p>
                  ) : (
                    <p className="mt-1 border-l-4 border-amber-500 bg-amber-50 px-3 py-2 font-semibold text-amber-950">{t("derivedState.ballots.duplicateWarning")}</p>
                  )}
                </div>
                <div>
                  <p className="font-semibold text-slate-600">{t("derivedState.ballots.votes")}</p>
                  <ul className="mt-1 space-y-1">
                    {ballot.vote_records.map((vote) => (
                      <li key={vote.event_id}>
                        {participantLabel(participants, vote.voter_participant_id)} → {vote.target_participant_id === null ? t("derivedState.ballots.abstain") : participantLabel(participants, vote.target_participant_id)} ({vote.vote_weight})
                      </li>
                    ))}
                  </ul>
                </div>
                <div><span className="font-semibold text-slate-600">{t("derivedState.ballots.explicitOutcome")}</span><div className="mt-1 flex flex-wrap gap-1">{ballot.explicit_outcome_event_ids.length ? ballot.explicit_outcome_event_ids.map((id) => <EventProvenanceLink eventId={id} key={id} onOpenEvent={onOpenEvent} />) : t("common.none")}</div></div>
                {ballot.duplicate_voter_participant_ids.length ? <p className="text-amber-950">{t("derivedState.ballots.duplicateVoters")}: {ballot.duplicate_voter_participant_ids.map((id) => participantLabel(participants, id)).join(", ")}</p> : null}
                <div className="flex flex-wrap items-center gap-1 border-t border-slate-100 pt-3">
                  <span className="text-xs font-semibold text-slate-500">{t("derivedState.provenance")}</span>
                  {provenance.map((id) => <EventProvenanceLink eventId={id} key={id} onOpenEvent={onOpenEvent} />)}
                </div>
              </div>
            </details>
          );
        })}
      </div>
      {ordered.length === 0 ? <p className="mt-3 border border-dashed border-slate-300 p-4 text-sm text-slate-600">{t("derivedState.ballots.empty")}</p> : null}
    </section>
  );
}
