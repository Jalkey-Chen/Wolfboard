"use client";

/**
 * Shared client-side auth hook for protected pages.
 *
 * The hook resolves the current user from localStorage and `/auth/me`, then
 * optionally enforces a required system role before a page renders.
 */
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import { getCurrentUser, type CurrentUserResponse, type RoleKey } from "@/lib/api";


type UseAuthenticatedSessionOptions = {
  requiredRole?: RoleKey;
  requiredRoles?: RoleKey[];
};


export function useAuthenticatedSession(options: UseAuthenticatedSessionOptions = {}) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<CurrentUserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const requiredRolesKey = (options.requiredRoles ?? []).join(",");

  useEffect(() => {
    const requiredRoles = options.requiredRoles ?? (
      options.requiredRole ? [options.requiredRole] : []
    );
    const storedToken = getStoredAccessToken();
    if (!storedToken) {
      router.replace("/login");
      return;
    }

    setToken(storedToken);

    void getCurrentUser(storedToken)
      .then((response) => {
        if (
          requiredRoles.length > 0 &&
          !requiredRoles.some((role) => response.roles.includes(role))
        ) {
          // Client-side route protection improves UX, but server-side role checks
          // remain the authoritative enforcement mechanism.
          router.replace("/");
          return;
        }
        setProfile(response);
        setIsLoading(false);
      })
      .catch(() => {
        clearStoredAccessToken();
        setErrorMessage("Your session is invalid or expired. Please sign in again.");
        setIsLoading(false);
        router.replace("/login");
      });
  }, [options.requiredRole, requiredRolesKey, router]);

  return {
    token,
    profile,
    isLoading,
    errorMessage,
    hasRole: (role: RoleKey) => profile?.roles.includes(role) ?? false,
  };
}
