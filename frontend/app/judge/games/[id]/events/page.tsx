"use client";

import { useParams } from "next/navigation";

import { EventWorkbench } from "@/components/game-events/EventWorkbench";
import { PageLoading } from "@/components/page-state";
import { useI18n } from "@/components/language-provider";
import { useAuthenticatedSession } from "@/lib/use-authenticated-session";


export default function JudgeGameEventsPage() {
  const params = useParams<{ id: string }>();
  const gameId = Number(params.id);
  const { t } = useI18n();
  const { token, profile, isLoading } = useAuthenticatedSession({ requiredRoles: ["judge", "admin"] });

  if (isLoading) return <PageLoading message={t("eventWorkbench.loading")} />;
  if (!token || !profile || Number.isNaN(gameId)) return null;
  return <EventWorkbench gameId={gameId} profile={profile} token={token} />;
}
