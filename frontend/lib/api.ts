/**
 * Minimal frontend API client for Milestone 1 authentication flows.
 *
 * Later milestones can expand this into a shared fetch wrapper with typed
 * domain clients, but the current version intentionally stays small.
 */
export type UserPayload = {
  id: number;
  username: string;
  display_name: string;
  email: string | null;
  account_status: string;
  created_at: string;
  updated_at: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: UserPayload;
  roles: string[];
};

export type CurrentUserResponse = {
  user: UserPayload;
  roles: string[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";


async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = "Request failed.";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      detail = "Request failed.";
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}


export function login(username: string, password: string): Promise<LoginResponse> {
  /** Exchange username and password credentials for a bearer token. */
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}


export function getCurrentUser(token: string): Promise<CurrentUserResponse> {
  /** Resolve the current user profile from an existing bearer token. */
  return request<CurrentUserResponse>("/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
