"use client";

/**
 * Admin game management page for a single event day.
 *
 * The page keeps creation and editing on one surface so admins can schedule
 * several rounds quickly without losing event-day context.
 */

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { formatDate, toDateTimeLocalValue } from "@/lib/date";
import {
  createGame,
  getEventDay,
  getFormats,
  getJudgeOptions,
  updateGame,
  type EventDayDetail,
  type GameCreatePayload,
  type GameStatus,
  type GameSummary,
  type GameType,
  type JudgeOptionRecord,
  type GameFormatRecord,
} from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


const gameTypes: GameType[] = ["official", "fun", "practice"];
const gameStatuses: GameStatus[] = ["draft", "in_progress", "submitted", "confirmed", "revised", "cancelled"];


type FormState = {
  game_number: string;
  table_number: string;
  format_id: string;
  judge_user_id: string;
  game_type: GameType;
  status: GameStatus;
  notes: string;
  started_at: string;
  ended_at: string;
};


function emptyFormState(): FormState {
  return {
    game_number: "",
    table_number: "",
    format_id: "",
    judge_user_id: "",
    game_type: "official",
    status: "draft",
    notes: "",
    started_at: "",
    ended_at: "",
  };
}


function buildFormState(game: GameSummary | null): FormState {
  if (!game) {
    return emptyFormState();
  }

  return {
    game_number: String(game.game_number),
    table_number: String(game.table_number),
    format_id: String(game.format_id),
    judge_user_id: String(game.judge_user_id),
    game_type: game.game_type,
    status: game.status,
    notes: game.notes ?? "",
    started_at: toDateTimeLocalValue(game.started_at),
    ended_at: toDateTimeLocalValue(game.ended_at),
  };
}


export default function AdminEventDayGamesPage() {
  const params = useParams<{ id: string }>();
  const eventDayId = Number(params.id);
  const { token, profile, isLoading } = useAuthenticatedSession({ requiredRole: "admin" });
  const [eventDay, setEventDay] = useState<EventDayDetail | null>(null);
  const [formats, setFormats] = useState<GameFormatRecord[]>([]);
  const [judges, setJudges] = useState<JudgeOptionRecord[]>([]);
  const [selectedGameId, setSelectedGameId] = useState<number | null>(null);
  const [formState, setFormState] = useState<FormState>(emptyFormState());
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !profile || Number.isNaN(eventDayId)) {
      return;
    }

    async function loadPage() {
      try {
        const [eventDayResponse, formatResponse, judgeResponse] = await Promise.all([
          getEventDay(token, eventDayId),
          getFormats(token),
          getJudgeOptions(token),
        ]);
        setEventDay(eventDayResponse);
        setFormats(formatResponse);
        setJudges(judgeResponse);
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load game management data.");
      }
    }

    void loadPage();
  }, [eventDayId, profile, token]);

  const selectedGame = useMemo(
    () => eventDay?.games.find((game) => game.id === selectedGameId) ?? null,
    [eventDay, selectedGameId],
  );

  if (isLoading) {
    return <PageLoading message="Loading event-day games..." />;
  }

  if (!profile || Number.isNaN(eventDayId)) {
    return null;
  }

  async function refreshPage() {
    if (!token) {
      return;
    }
    const refreshed = await getEventDay(token, eventDayId);
    setEventDay(refreshed);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);

    const payload: GameCreatePayload = {
      event_day_id: eventDayId,
      game_number: Number(formState.game_number),
      table_number: Number(formState.table_number),
      format_id: Number(formState.format_id),
      judge_user_id: Number(formState.judge_user_id),
      game_type: formState.game_type,
      status: formState.status,
      notes: formState.notes || null,
      started_at: formState.started_at || null,
      ended_at: formState.ended_at || null,
    };

    try {
      if (selectedGame) {
        await updateGame(token, selectedGame.id, {
          game_number: payload.game_number,
          table_number: payload.table_number,
          format_id: payload.format_id,
          judge_user_id: payload.judge_user_id,
          game_type: payload.game_type,
          status: payload.status,
          notes: payload.notes,
          started_at: payload.started_at,
          ended_at: payload.ended_at,
        });
      } else {
        await createGame(token, payload);
      }

      await refreshPage();
      setSelectedGameId(null);
      setFormState(emptyFormState());
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to save the game.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <SiteShell
      profile={profile}
      title={eventDay ? `${eventDay.title} · Games` : "Manage Games"}
      description="Create and edit scheduled games under a single event day."
      actions={
        eventDay ? (
          <div className="flex flex-wrap gap-3">
            <Link
              className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
              href={`/event-days/${eventDay.id}`}
            >
              Public View
            </Link>
            <Link
              className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
              href={`/admin/event-days/${eventDay.id}`}
            >
              Edit Event Day
            </Link>
          </div>
        ) : null
      }
    >
      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-2xl font-bold text-ink">Scheduled Games</h2>
            <button
              className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
              onClick={() => {
                setSelectedGameId(null);
                setFormState(emptyFormState());
              }}
              type="button"
            >
              Create New
            </button>
          </div>

          {eventDay ? (
            <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-4 text-sm text-slate-700">
              {formatDate(eventDay.event_date)} · {eventDay.venue} · {eventDay.game_count} games
            </div>
          ) : null}

          {errorMessage ? <div className="mt-4"><PageError message={errorMessage} /></div> : null}

          <div className="mt-5 grid gap-4">
            {eventDay?.games.map((game) => (
              <div key={game.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-ink">
                      Table {game.table_number} · Game {game.game_number}
                    </h3>
                    <p className="mt-2 text-sm text-slate-600">
                      {game.format_name} · Judge: {game.judge_display_name}
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      Type: {game.game_type} · Status: {game.status}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Link
                      className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
                      href={`/games/${game.id}`}
                    >
                      View
                    </Link>
                    <button
                      className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                      onClick={() => {
                        setSelectedGameId(game.id);
                        setFormState(buildFormState(game));
                      }}
                      type="button"
                    >
                      Edit
                    </button>
                  </div>
                </div>
              </div>
            ))}

            {eventDay && eventDay.games.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
                No games are scheduled for this event day yet.
              </div>
            ) : null}
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
          <h2 className="text-2xl font-bold text-ink">{selectedGame ? "Edit Game" : "Create Game"}</h2>

          <form className="mt-5 grid gap-4" onSubmit={handleSubmit}>
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              min={1}
              onChange={(event) => setFormState((current) => ({ ...current, table_number: event.target.value }))}
              placeholder="Table number"
              required
              type="number"
              value={formState.table_number}
            />
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              min={1}
              onChange={(event) => setFormState((current) => ({ ...current, game_number: event.target.value }))}
              placeholder="Game number"
              required
              type="number"
              value={formState.game_number}
            />
            <select
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, format_id: event.target.value }))}
              required
              value={formState.format_id}
            >
              <option value="">Select format</option>
              {formats.map((gameFormat) => (
                <option key={gameFormat.id} value={gameFormat.id}>
                  {gameFormat.format_name} ({gameFormat.player_count})
                </option>
              ))}
            </select>
            <select
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, judge_user_id: event.target.value }))}
              required
              value={formState.judge_user_id}
            >
              <option value="">Select judge</option>
              {judges.map((judge) => (
                <option key={judge.id} value={judge.id}>
                  {judge.display_name} ({judge.username})
                </option>
              ))}
            </select>
            <select
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, game_type: event.target.value as GameType }))}
              value={formState.game_type}
            >
              {gameTypes.map((gameType) => (
                <option key={gameType} value={gameType}>
                  {gameType}
                </option>
              ))}
            </select>
            <select
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, status: event.target.value as GameStatus }))}
              value={formState.status}
            >
              {gameStatuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, started_at: event.target.value }))}
              type="datetime-local"
              value={formState.started_at}
            />
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, ended_at: event.target.value }))}
              type="datetime-local"
              value={formState.ended_at}
            />
            <textarea
              className="min-h-28 rounded-2xl border border-slate-200 px-4 py-3 text-sm"
              onChange={(event) => setFormState((current) => ({ ...current, notes: event.target.value }))}
              placeholder="Notes"
              value={formState.notes}
            />
            <button
              className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
              disabled={isSaving}
              type="submit"
            >
              {isSaving ? "Saving..." : selectedGame ? "Save Game" : "Create Game"}
            </button>
          </form>
        </section>
      </div>
    </SiteShell>
  );
}
