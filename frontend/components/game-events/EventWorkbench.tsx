"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { CorrectEventDialog } from "@/components/game-events/CorrectEventDialog";
import { EffectiveTimeline } from "@/components/game-events/EffectiveTimeline";
import { EventLedger } from "@/components/game-events/EventLedger";
import { GameEventComposer } from "@/components/game-events/GameEventComposer";
import { VoidEventDialog } from "@/components/game-events/VoidEventDialog";
import { WorkbenchStatusBanner } from "@/components/game-events/WorkbenchStatusBanner";
import { useI18n } from "@/components/language-provider";
import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import {
  correctGameEvent,
  createGameEvent,
  endGame,
  getGame,
  getGameFormatContext,
  getGameResultDraft,
  listGameEventDefinitions,
  listGameEvents,
  startGame,
  voidGameEvent,
  type CurrentUserResponse,
  type GameDetail,
  type GameEventBodyPayload,
  type GameEventDefinition,
  type GameEventRecord,
  type GameFormatContext,
  type GameResultDraftResponse,
} from "@/lib/api";
import { compareDefinitionRegistries } from "@/lib/game-events/definitions";
import { eventDraftStorageKey } from "@/lib/game-events/draft-storage";
import { parseWorkbenchError } from "@/lib/game-events/errors";
import type { ParticipantOption } from "@/lib/game-events/form-types";
import { resolveWorkbenchMode } from "@/lib/game-events/lifecycle";


const PAGE_SIZE = 100;
let definitionCache: { token: string; value: GameEventDefinition[] } | null = null;

async function getCachedDefinitions(token: string): Promise<GameEventDefinition[]> {
  if (definitionCache?.token === token) return definitionCache.value;
  const value = await listGameEventDefinitions(token);
  definitionCache = { token, value };
  return value;
}

type WorkbenchData = {
  game: GameDetail;
  format: GameFormatContext;
  draft: GameResultDraftResponse;
  definitions: GameEventDefinition[];
  effective: GameEventRecord[];
  ledger: GameEventRecord[];
};

export function EventWorkbench({
  gameId,
  token,
  profile,
}: {
  gameId: number;
  token: string;
  profile: CurrentUserResponse;
}) {
  const { t } = useI18n();
  const [data, setData] = useState<WorkbenchData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [effectiveHasMore, setEffectiveHasMore] = useState(false);
  const [ledgerHasMore, setLedgerHasMore] = useState(false);
  const [tab, setTab] = useState<"effective" | "ledger">("effective");
  const [correcting, setCorrecting] = useState<GameEventRecord | null>(null);
  const [voiding, setVoiding] = useState<GameEventRecord | null>(null);
  const [voidBusy, setVoidBusy] = useState(false);
  const [voidError, setVoidError] = useState<string | null>(null);
  const [otherTabNotice, setOtherTabNotice] = useState(false);

  const loadAll = useCallback(async () => {
    const [game, format, draft, definitions, effective, ledger] = await Promise.all([
      getGame(token, gameId),
      getGameFormatContext(token, gameId),
      getGameResultDraft(token, gameId),
      getCachedDefinitions(token),
      listGameEvents(token, gameId, { view: "effective", limit: PAGE_SIZE }),
      listGameEvents(token, gameId, { view: "ledger", limit: PAGE_SIZE }),
    ]);
    setData({ game, format, draft, definitions, effective, ledger });
    setEffectiveHasMore(effective.length === PAGE_SIZE);
    setLedgerHasMore(ledger.length === PAGE_SIZE);
    setError(null);
    setOtherTabNotice(false);
  }, [gameId, token]);

  useEffect(() => {
    void loadAll().catch((loadError) => setError(parseWorkbenchError(loadError).message));
  }, [loadAll]);

  const refreshEvents = useCallback(async () => {
    setRefreshing(true);
    try {
      const [game, effective, ledger] = await Promise.all([
        getGame(token, gameId),
        listGameEvents(token, gameId, { view: "effective", limit: PAGE_SIZE }),
        listGameEvents(token, gameId, { view: "ledger", limit: PAGE_SIZE }),
      ]);
      setData((current) => current ? { ...current, game, effective, ledger } : current);
      setEffectiveHasMore(effective.length === PAGE_SIZE);
      setLedgerHasMore(ledger.length === PAGE_SIZE);
      setOtherTabNotice(false);
    } catch (refreshError) {
      setError(parseWorkbenchError(refreshError).message);
    } finally {
      setRefreshing(false);
    }
  }, [gameId, token]);

  useEffect(() => {
    function onFocus() { void refreshEvents(); }
    function onStorage(storageEvent: StorageEvent) {
      if (storageEvent.key === eventDraftStorageKey(gameId)) setOtherTabNotice(true);
    }
    window.addEventListener("focus", onFocus);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("storage", onStorage);
    };
  }, [gameId, refreshEvents]);

  const participants = useMemo<ParticipantOption[]>(() => (data?.draft.players ?? []).map((player) => ({
    participantId: player.participant_id,
    userId: player.user_id,
    username: player.username,
    displayName: player.display_name,
    seatNumber: player.seat_number,
    roleName: player.role_name,
  })).sort((left, right) => (left.seatNumber ?? 999) - (right.seatNumber ?? 999)), [data?.draft.players]);

  if (!data && !error) return <PageLoading message={t("eventWorkbench.loading")} />;
  if (!data) return <PageError message={error ?? t("eventWorkbench.loadError")} />;

  const mode = resolveWorkbenchMode(data.game);
  const loadedData = data;
  const drift = compareDefinitionRegistries(data.definitions);
  const registryValid = drift.missingRenderers.length === 0 && drift.unsupportedClientTypes.length === 0;
  const editable = mode.editable && registryValid;
  const recentEvent = data.effective.at(-1);

  async function refreshAfterWrite() {
    await refreshEvents();
  }

  async function loadMore(view: "effective" | "ledger") {
    setLoadingMore(true);
    try {
      const current = view === "effective" ? loadedData.effective : loadedData.ledger;
      const last = current.at(-1);
      const next = await listGameEvents(token, gameId, {
        view,
        limit: PAGE_SIZE,
        afterLogicalSequence: view === "effective" ? last?.logical_sequence_no : undefined,
        afterLedgerSequence: view === "ledger" ? last?.sequence_no : undefined,
      });
      setData((value) => value ? {
        ...value,
        [view]: [...value[view], ...next.filter((event) => !value[view].some((existing) => existing.id === event.id))],
      } : value);
      if (view === "effective") setEffectiveHasMore(next.length === PAGE_SIZE);
      else setLedgerHasMore(next.length === PAGE_SIZE);
    } finally {
      setLoadingMore(false);
    }
  }

  async function changePlay(action: "start" | "end") {
    if (action === "end" && !window.confirm(t("eventWorkbench.endConfirm"))) return;
    setRefreshing(true);
    try {
      if (action === "start") await startGame(token, gameId);
      else await endGame(token, gameId);
      await loadAll();
    } catch (stateError) {
      setError(parseWorkbenchError(stateError).message);
    } finally {
      setRefreshing(false);
    }
  }

  async function confirmVoid(reason: string) {
    if (!voiding) return;
    setVoidBusy(true);
    setVoidError(null);
    try {
      await voidGameEvent(token, gameId, voiding.id, reason);
      setVoiding(null);
      await refreshAfterWrite();
    } catch (mutationError) {
      const parsed = parseWorkbenchError(mutationError);
      setVoidError(parsed.message);
      if (parsed.status === 409) await refreshAfterWrite();
    } finally {
      setVoidBusy(false);
    }
  }

  return (
    <SiteShell
      actions={
        <div className="flex flex-wrap gap-2">
          <Link className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold" href={`/games/${gameId}`}>{t("common.details")}</Link>
          <Link className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold" href={`/judge/games/${gameId}/result`}>{t("games.viewResult")}</Link>
          {data.game.play_status === "scheduled" ? <button className="rounded-md bg-slate-900 px-3 py-2 text-sm font-bold text-white" disabled={refreshing} onClick={() => void changePlay("start")} type="button">{t("common.start")}</button> : null}
          {data.game.play_status === "in_progress" ? <button className="rounded-md bg-slate-900 px-3 py-2 text-sm font-bold text-white" disabled={refreshing} onClick={() => void changePlay("end")} type="button">{t("common.end")}</button> : null}
        </div>
      }
      description={`${data.game.event_day_title} · ${data.format.format_name}`}
      profile={profile}
      title={`${t("eventWorkbench.title")} · ${data.game.table_number}桌 / 第${data.game.game_number}局`}
    >
      <div className="space-y-4">
        {error ? <PageError message={error} /> : null}
        {otherTabNotice ? (
          <button className="w-full border-l-4 border-amber-500 bg-amber-50 px-4 py-3 text-left text-sm text-amber-900" onClick={() => void refreshEvents()} type="button">{t("eventWorkbench.otherTabNotice")}</button>
        ) : null}
        {!registryValid ? (
          <div className="border-l-4 border-red-700 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            {t("eventWorkbench.unsupportedDefinitions")}: {[...drift.missingRenderers, ...drift.unsupportedClientTypes].join(", ")}
          </div>
        ) : null}
        <WorkbenchStatusBanner game={data.game} mode={mode} />

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <div><div className="text-xs font-semibold text-slate-500">{t("common.eventDay")}</div><div className="mt-1 text-sm font-bold">{data.game.event_day_title}</div></div>
            <div><div className="text-xs font-semibold text-slate-500">{t("common.table")}</div><div className="mt-1 text-sm font-bold">{data.game.table_number} / {data.game.game_number}</div></div>
            <div><div className="text-xs font-semibold text-slate-500">{t("common.judge")}</div><div className="mt-1 text-sm font-bold">{data.game.judge_display_name}</div></div>
            <div><div className="text-xs font-semibold text-slate-500">{t("common.format")}</div><div className="mt-1 text-sm font-bold">{data.format.format_name}</div><div className="text-xs text-slate-500">{data.format.snapshot_origin ?? t("games.formatNotFrozen")}</div></div>
            <div><div className="text-xs font-semibold text-slate-500">{t("eventWorkbench.participants")}</div><div className="mt-1 text-sm font-bold">{participants.length}</div></div>
            <div><div className="text-xs font-semibold text-slate-500">{t("eventWorkbench.loadedEvents")}</div><div className="mt-1 text-sm font-bold">{data.ledger.length}{ledgerHasMore ? "+" : ""}</div></div>
          </div>
        </section>

        {participants.length === 0 ? (
          <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            <p>{t("eventWorkbench.noParticipants")}</p>
            <Link className="mt-2 inline-block font-bold underline" href={`/judge/games/${gameId}/result`}>{t("eventWorkbench.setupParticipants")}</Link>
          </div>
        ) : null}

        <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(320px,0.85fr)_minmax(0,1.5fr)] lg:items-start">
          <section className="min-w-0 rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:sticky lg:top-4">
            <h2 className="text-lg font-bold text-slate-900">{t("eventWorkbench.composer")}</h2>
            <div className="mt-4">
              <GameEventComposer
                definitions={data.definitions}
                disabled={!editable}
                events={data.ledger}
                gameId={gameId}
                onConflict={() => void refreshEvents()}
                onSubmit={async (request) => {
                  await createGameEvent(token, gameId, request);
                  await refreshAfterWrite();
                }}
                participants={participants}
                recentEvent={recentEvent}
              />
            </div>
          </section>

          <section className="min-w-0 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
              <div className="flex gap-1" role="tablist">
                <button aria-selected={tab === "effective"} className={`rounded-md px-3 py-2 text-sm font-bold ${tab === "effective" ? "bg-slate-900 text-white" : "text-slate-600"}`} onClick={() => setTab("effective")} role="tab" type="button">{t("eventWorkbench.effectiveTimeline")}</button>
                <button aria-selected={tab === "ledger"} className={`rounded-md px-3 py-2 text-sm font-bold ${tab === "ledger" ? "bg-slate-900 text-white" : "text-slate-600"}`} onClick={() => setTab("ledger")} role="tab" type="button">{t("eventWorkbench.fullLedger")}</button>
              </div>
              <button className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold" disabled={refreshing} onClick={() => void refreshEvents()} type="button">{refreshing ? t("common.loading") : t("eventWorkbench.refresh")}</button>
            </div>
            <div className="mt-4" role="tabpanel">
              {tab === "effective" ? (
                <EffectiveTimeline editable={editable} events={data.effective} hasMore={effectiveHasMore} loadingMore={loadingMore} onCorrect={setCorrecting} onLoadMore={() => void loadMore("effective")} onVoid={setVoiding} participants={participants} />
              ) : (
                <EventLedger editable={editable} events={data.ledger} hasMore={ledgerHasMore} loadingMore={loadingMore} onCorrect={setCorrecting} onLoadMore={() => void loadMore("ledger")} onVoid={setVoiding} participants={participants} />
              )}
            </div>
          </section>
        </div>
      </div>

      {correcting ? (
        <CorrectEventDialog
          definitions={data.definitions}
          event={correcting}
          events={data.ledger}
          gameId={gameId}
          onClose={() => setCorrecting(null)}
          onConflict={() => void refreshEvents()}
          onSubmit={async (request: GameEventBodyPayload, reason: string) => {
            await correctGameEvent(token, gameId, correcting.id, { ...request, reason });
            await refreshAfterWrite();
          }}
          participants={participants}
        />
      ) : null}
      {voiding ? <VoidEventDialog busy={voidBusy} error={voidError} event={voiding} onClose={() => { setVoiding(null); setVoidError(null); }} onConfirm={(reason) => void confirmVoid(reason)} /> : null}
    </SiteShell>
  );
}
