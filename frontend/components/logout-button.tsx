"use client";

/** Sign-out control that clears the locally stored access token. */
import { useRouter } from "next/navigation";

import { useI18n } from "@/components/language-provider";
import { clearStoredAccessToken } from "@/lib/auth";


export function LogoutButton() {
  const router = useRouter();
  const { t } = useI18n();

  function handleLogout() {
    clearStoredAccessToken();
    router.replace("/login");
  }

  return (
    <button
      className="rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
      onClick={handleLogout}
      type="button"
    >
      {t("auth.signOut")}
    </button>
  );
}
