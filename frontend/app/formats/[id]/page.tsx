"use client";

/**
 * Format detail page showing role composition and admin toggle controls.
 */

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { PageError, PageLoading } from "@/components/page-state";
import { SiteShell } from "@/components/site-shell";
import { getFormat, updateFormat, type GameFormatDetail } from "@/lib/api";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function FormatDetailPage() {
  const params = useParams<{ id: string }>();
  const formatId = Number(params.id);
  const { token, profile, isLoading, hasRole } = useAuthenticatedSession();
  const [gameFormat, setGameFormat] = useState<GameFormatDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isToggling, setIsToggling] = useState(false);

  useEffect(() => {
    if (!token || !profile || Number.isNaN(formatId)) {
      return;
    }

    void getFormat(token, formatId)
      .then((response) => setGameFormat(response))
      .catch((error) => {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load the format.");
      });
  }, [formatId, profile, token]);

  if (isLoading) {
    return <PageLoading message="Loading format details..." />;
  }

  if (!profile || Number.isNaN(formatId)) {
    return null;
  }

  async function handleToggleActive() {
    if (!token || !gameFormat) {
      return;
    }

    setIsToggling(true);
    setErrorMessage(null);
    try {
      const updated = await updateFormat(token, gameFormat.id, {
        is_active: !gameFormat.is_active,
      });
      setGameFormat(updated);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to update the format.");
    } finally {
      setIsToggling(false);
    }
  }

  return (
    <SiteShell
      profile={profile}
      title={gameFormat?.format_name ?? "Format"}
      description={gameFormat?.description ?? "Preset format detail and role composition."}
      actions={
        hasRole("admin") && gameFormat ? (
          <button
            className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
            disabled={isToggling}
            onClick={handleToggleActive}
            type="button"
          >
            {isToggling
              ? "Saving..."
              : gameFormat.is_active
                ? "Disable Format"
                : "Enable Format"}
          </button>
        ) : null
      }
    >
      <div className="flex flex-col gap-5">
        {errorMessage ? <PageError message={errorMessage} /> : null}

        {gameFormat ? (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <div className="grid gap-4 md:grid-cols-4">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Players</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{gameFormat.player_count}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Category</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{gameFormat.category}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Preset</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">
                    {gameFormat.is_system_preset ? "System preset" : "Custom"}
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Status</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">
                    {gameFormat.is_active ? "active" : "inactive"}
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg shadow-slate-200/50">
              <h2 className="text-2xl font-bold text-ink">Role Composition</h2>
              <div className="mt-5 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="px-3 py-3 font-semibold">Role</th>
                      <th className="px-3 py-3 font-semibold">Faction</th>
                      <th className="px-3 py-3 font-semibold">Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {gameFormat.roles.map((role) => (
                      <tr key={role.id}>
                        <td className="px-3 py-4 font-semibold text-ink">{role.role_name}</td>
                        <td className="px-3 py-4 text-slate-700">{role.faction}</td>
                        <td className="px-3 py-4 text-slate-700">{role.role_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </SiteShell>
  );
}
