/**
 * Typed frontend API client for authentication, season, event-day, and
 * registration flows used by Milestones 1 and 2.
 */
export type RoleKey = "admin" | "judge" | "player";
export type SeasonStatus = "draft" | "active" | "completed" | "archived";
export type EventDayCategory = "official" | "fun" | "mixed";
export type EventDayStatus =
  | "draft"
  | "open_for_registration"
  | "registration_closed"
  | "ongoing"
  | "completed"
  | "archived";
export type RegistrationStatus = "registered" | "waitlisted" | "cancelled";
export type CheckInStatus = "not_checked_in" | "checked_in" | "absent";
export type RegistrationType = "main" | "substitute" | "guest";

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
  roles: RoleKey[];
};

export type CurrentUserResponse = {
  user: UserPayload;
  roles: RoleKey[];
};

export type SeasonRecord = {
  id: number;
  name: string;
  description: string | null;
  start_date: string;
  end_date: string;
  status: SeasonStatus;
  created_by: number;
  created_at: string;
  updated_at: string;
};

export type EventDaySummary = {
  id: number;
  season_id: number;
  title: string;
  event_date: string;
  venue: string;
  category: EventDayCategory;
  registration_open_at: string | null;
  registration_close_at: string | null;
  status: EventDayStatus;
  created_at: string;
  updated_at: string;
};

export type SeasonDetail = SeasonRecord & {
  event_days: EventDaySummary[];
};

export type RegistrationRecord = {
  id: number;
  event_day_id: number;
  user_id: number;
  username: string;
  display_name: string;
  registration_status: RegistrationStatus;
  check_in_status: CheckInStatus;
  registration_type: RegistrationType;
  note: string | null;
  created_at: string;
  updated_at: string;
};

export type EventDayDetail = EventDaySummary & {
  notes: string | null;
  season_name: string;
  registration_count: number;
  viewer_registration: RegistrationRecord | null;
};

export type SeasonCreatePayload = {
  name: string;
  description?: string | null;
  start_date: string;
  end_date: string;
  status: SeasonStatus;
};

export type SeasonUpdatePayload = Partial<SeasonCreatePayload>;

export type EventDayCreatePayload = {
  season_id: number;
  title: string;
  event_date: string;
  venue: string;
  category: EventDayCategory;
  notes?: string | null;
  registration_open_at?: string | null;
  registration_close_at?: string | null;
  status: EventDayStatus;
};

export type EventDayUpdatePayload = Partial<Omit<EventDayCreatePayload, "season_id">>;

export type RegistrationCreatePayload = {
  registration_type?: RegistrationType;
  note?: string | null;
};

export type RegistrationAdminUpdatePayload = {
  registration_status?: RegistrationStatus;
  check_in_status?: CheckInStatus;
  registration_type?: RegistrationType;
  note?: string | null;
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


function withAuth(token: string, init?: RequestInit): RequestInit {
  return {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  };
}


export function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}


export function getCurrentUser(token: string): Promise<CurrentUserResponse> {
  return request<CurrentUserResponse>("/auth/me", withAuth(token));
}


export function getSeasons(token: string): Promise<SeasonRecord[]> {
  return request<SeasonRecord[]>("/seasons", withAuth(token));
}


export function getSeason(token: string, seasonId: number): Promise<SeasonDetail> {
  return request<SeasonDetail>(`/seasons/${seasonId}`, withAuth(token));
}


export function createSeason(token: string, payload: SeasonCreatePayload): Promise<SeasonRecord> {
  return request<SeasonRecord>("/seasons", withAuth(token, {
    method: "POST",
    body: JSON.stringify(payload),
  }));
}


export function updateSeason(
  token: string,
  seasonId: number,
  payload: SeasonUpdatePayload,
): Promise<SeasonRecord> {
  return request<SeasonRecord>(`/seasons/${seasonId}`, withAuth(token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }));
}


export function getEventDay(token: string, eventDayId: number): Promise<EventDayDetail> {
  return request<EventDayDetail>(`/event-days/${eventDayId}`, withAuth(token));
}


export function createEventDay(
  token: string,
  payload: EventDayCreatePayload,
): Promise<EventDayDetail> {
  return request<EventDayDetail>("/event-days", withAuth(token, {
    method: "POST",
    body: JSON.stringify(payload),
  }));
}


export function updateEventDay(
  token: string,
  eventDayId: number,
  payload: EventDayUpdatePayload,
): Promise<EventDayDetail> {
  return request<EventDayDetail>(`/event-days/${eventDayId}`, withAuth(token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }));
}


export function getEventDayRegistrations(
  token: string,
  eventDayId: number,
): Promise<RegistrationRecord[]> {
  return request<RegistrationRecord[]>(`/event-days/${eventDayId}/registrations`, withAuth(token));
}


export function registerForEventDay(
  token: string,
  eventDayId: number,
  payload: RegistrationCreatePayload = {},
): Promise<RegistrationRecord> {
  return request<RegistrationRecord>(`/event-days/${eventDayId}/registrations`, withAuth(token, {
    method: "POST",
    body: JSON.stringify(payload),
  }));
}


export function cancelRegistration(
  token: string,
  registrationId: number,
): Promise<RegistrationRecord> {
  return request<RegistrationRecord>(`/registrations/${registrationId}/cancel`, withAuth(token, {
    method: "PATCH",
  }));
}


export function updateRegistration(
  token: string,
  registrationId: number,
  payload: RegistrationAdminUpdatePayload,
): Promise<RegistrationRecord> {
  return request<RegistrationRecord>(`/registrations/${registrationId}`, withAuth(token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }));
}
