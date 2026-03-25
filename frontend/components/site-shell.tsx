"use client";

/** Shared layout shell for authenticated pages in Milestone 2.
 *
 * The shell keeps navigation, role badges, and sign-out behavior consistent
 * across player-facing and admin-facing surfaces.
 */
import Link from "next/link";
import type { ReactNode } from "react";

import { LanguageSwitcher } from "@/components/language-switcher";
import { useI18n } from "@/components/language-provider";
import { LogoutButton } from "@/components/logout-button";
import type { CurrentUserResponse } from "@/lib/api";
import { getBadgeTextClass, getOverlineTextClass } from "@/lib/i18n";


type SiteShellProps = {
  profile: CurrentUserResponse;
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
};


export function SiteShell({
  profile,
  title,
  description,
  actions,
  children,
}: SiteShellProps) {
  const { t, enumLabel, language } = useI18n();
  const isAdmin = profile.roles.includes("admin");
  const isJudge = profile.roles.includes("judge");
  const canOpenJudgeQueue = isAdmin || isJudge;
  const overlineClass = `${getOverlineTextClass(language)} text-accent`;
  const roleBadgeClass = `rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-gold ${getBadgeTextClass(language)}`;

  return (
    <main className="min-h-screen px-6 py-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <header className="rounded-[2rem] border border-slate-200 bg-white/90 p-8 shadow-xl shadow-slate-200/50">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <p className={overlineClass}>{t("brand.name")}</p>
                {profile.roles.map((role) => (
                  <span
                    key={role}
                    className={roleBadgeClass}
                  >
                    {enumLabel("role", role)}
                  </span>
                ))}
              </div>
              <div>
                <h1 className="text-3xl font-bold text-ink">{title}</h1>
                <p className="mt-2 max-w-3xl text-sm text-slate-600">{description}</p>
              </div>
              <nav className="flex flex-wrap gap-3 text-sm font-medium text-slate-700">
                <Link className="rounded-full bg-slate-100 px-4 py-2 hover:bg-slate-200" href="/">
                  {t("nav.home")}
                </Link>
                <Link className="rounded-full bg-slate-100 px-4 py-2 hover:bg-slate-200" href="/seasons">
                  {t("nav.seasons")}
                </Link>
                <Link className="rounded-full bg-slate-100 px-4 py-2 hover:bg-slate-200" href="/formats">
                  {t("nav.formats")}
                </Link>
                <Link className="rounded-full bg-slate-100 px-4 py-2 hover:bg-slate-200" href="/leaderboard">
                  {t("nav.leaderboard")}
                </Link>
                <Link className="rounded-full bg-slate-100 px-4 py-2 hover:bg-slate-200" href={`/players/${profile.user.id}`}>
                  {t("nav.myProfile")}
                </Link>
                {/* Judge navigation is intentionally role-aware because the page
                    represents an owned work queue rather than a public index. */}
                {canOpenJudgeQueue ? (
                  <Link className="rounded-full bg-slate-100 px-4 py-2 hover:bg-slate-200" href="/judge/games">
                    {t("nav.judgeGames")}
                  </Link>
                ) : null}
                {isAdmin ? (
                  <>
                    <Link className="rounded-full bg-slate-100 px-4 py-2 hover:bg-slate-200" href="/admin/seasons">
                      {t("nav.adminSeasons")}
                    </Link>
                    <Link className="rounded-full bg-slate-100 px-4 py-2 hover:bg-slate-200" href="/admin/games/review">
                      {t("nav.reviewResults")}
                    </Link>
                  </>
                ) : null}
              </nav>
            </div>

            <div className="flex flex-col items-start gap-3 lg:items-end">
              <div className="text-sm text-slate-500">
                {t("common.signedInAs")} <span className="font-semibold text-slate-700">{profile.user.display_name}</span>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <LanguageSwitcher />
                {actions}
                <LogoutButton />
              </div>
            </div>
          </div>
        </header>

        {children}
      </div>
    </main>
  );
}
