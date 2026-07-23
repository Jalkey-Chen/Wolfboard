"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  getGameDerivedState,
  type GameDerivedState,
  type GameEventRecord,
} from "@/lib/api";
import { parseWorkbenchError } from "@/lib/game-events/errors";


export type DerivedStateSelection = {
  logicalSequence: number;
  event: GameEventRecord | null;
};

export type DerivedStateController = {
  state: GameDerivedState | null;
  selection: DerivedStateSelection | null;
  loading: boolean;
  error: string | null;
  refreshedAt: Date | null;
  stale: boolean;
  announcement: string | null;
  inspectEvent: (event: GameEventRecord) => Promise<void>;
  showLatest: () => Promise<void>;
  refresh: (options?: {
    ledgerUpdated?: boolean;
    selectedEvent?: GameEventRecord | null;
  }) => Promise<void>;
  markStale: () => void;
};

export function useDerivedState({
  gameId,
  token,
}: {
  gameId: number;
  token: string;
}): DerivedStateController {
  const [state, setState] = useState<GameDerivedState | null>(null);
  const [selection, setSelection] = useState<DerivedStateSelection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null);
  const [stale, setStale] = useState(false);
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const selectionRef = useRef<DerivedStateSelection | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  const load = useCallback(async (
    nextSelection: DerivedStateSelection | null,
    options: { ledgerUpdated?: boolean } = {},
  ) => {
    const requestId = ++requestIdRef.current;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    selectionRef.current = nextSelection;
    setSelection(nextSelection);
    setLoading(true);
    setError(null);
    if (options.ledgerUpdated && nextSelection) {
      setAnnouncement(`ledger-updated-prefix:${nextSelection.logicalSequence}`);
    } else {
      setAnnouncement(null);
    }
    try {
      const projected = await getGameDerivedState(
        token,
        gameId,
        nextSelection?.logicalSequence,
        controller.signal,
      );
      if (requestId !== requestIdRef.current) return;
      setState(projected);
      setRefreshedAt(new Date());
      setStale(false);
    } catch (loadError) {
      if (controller.signal.aborted || requestId !== requestIdRef.current) return;
      setError(parseWorkbenchError(loadError).message);
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  }, [gameId, token]);

  useEffect(() => {
    void load(null);
    return () => abortRef.current?.abort();
  }, [load]);

  const inspectEvent = useCallback(async (event: GameEventRecord) => {
    await load({ logicalSequence: event.logical_sequence_no, event });
  }, [load]);

  const showLatest = useCallback(async () => {
    await load(null);
  }, [load]);

  const refresh = useCallback(async (options: {
    ledgerUpdated?: boolean;
    selectedEvent?: GameEventRecord | null;
  } = {}) => {
    const current = selectionRef.current;
    const nextSelection = current
      ? {
          logicalSequence: current.logicalSequence,
          event: options.selectedEvent === undefined ? current.event : options.selectedEvent,
        }
      : null;
    await load(nextSelection, { ledgerUpdated: options.ledgerUpdated });
  }, [load]);

  const markStale = useCallback(() => setStale(true), []);

  return {
    state,
    selection,
    loading,
    error,
    refreshedAt,
    stale,
    announcement,
    inspectEvent,
    showLatest,
    refresh,
    markStale,
  };
}
