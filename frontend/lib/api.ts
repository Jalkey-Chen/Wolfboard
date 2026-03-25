/**
 * Typed frontend API client for the current Wolfboard MVP surface.
 *
 * Milestone 4 expands the client with result-draft reads, saves, and final
 * submission while preserving the earlier auth, season, registration, format,
 * and game-management flows.
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
export type FormatCategory = "standard" | "special" | "fun";
export type FormatRoleFaction = "good" | "wolf" | "third_party" | "special";
export type GameType = "official" | "fun" | "practice";
export type GamePlayerFaction = "good" | "wolf" | "third_party";
export type GamePlayerFinalStatus = "alive" | "eliminated" | "unknown";
export type ScoreAdjustmentType =
  | "late_penalty"
  | "conduct_penalty"
  | "judge_bonus"
  | "manual_adjustment";
export type GameStatus =
  | "draft"
  | "in_progress"
  | "submitted"
  | "confirmed"
  | "revised"
  | "cancelled";

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

export type GameFormatRecord = {
  id: number;
  format_name: string;
  format_key: string;
  player_count: number;
  category: FormatCategory;
  description: string | null;
  is_active: boolean;
  is_system_preset: boolean;
  created_at: string;
  updated_at: string;
};

export type FormatRoleRecord = {
  id: number;
  format_id: number;
  role_name: string;
  faction: FormatRoleFaction;
  role_count: number;
  display_order: number;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type GameFormatDetail = GameFormatRecord & {
  roles: FormatRoleRecord[];
};

export type JudgeOptionRecord = {
  id: number;
  username: string;
  display_name: string;
};

export type GameSummary = {
  id: number;
  event_day_id: number;
  season_id: number;
  season_name: string;
  event_day_title: string;
  event_day_date: string;
  game_number: number;
  table_number: number;
  format_id: number;
  format_name: string;
  judge_user_id: number;
  judge_display_name: string;
  game_type: GameType;
  status: GameStatus;
  started_at: string | null;
  ended_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type GameDetail = GameSummary & {
  event_day_venue: string;
  format: Pick<GameFormatRecord, "id" | "format_name" | "format_key" | "player_count">;
  judge: JudgeOptionRecord;
  has_result_draft: boolean;
  submitted_at: string | null;
  submitted_by: number | null;
  confirmed_at: string | null;
  confirmed_by: number | null;
};

export type ValidationMessage = {
  code: string;
  message: string;
  field: string | null;
};

export type ValidationSummary = {
  errors: ValidationMessage[];
  warnings: ValidationMessage[];
};

export type SelectablePlayerRecord = {
  user_id: number;
  username: string;
  display_name: string;
  registration_status: string | null;
  check_in_status: string | null;
};

export type GameResultPlayerDraftPayload = {
  user_id: number | null;
  seat_number: number | null;
  role_name: string | null;
  faction: GamePlayerFaction | null;
  final_status: GamePlayerFinalStatus;
  is_winner: boolean | null;
  remarks: string | null;
};

export type GameResultAdjustmentPayload = {
  target_seat_number: number;
  adjustment_type: ScoreAdjustmentType;
  delta: number;
  reason: string | null;
};

export type GameResultDraftWritePayload = {
  players: GameResultPlayerDraftPayload[];
  adjustments: GameResultAdjustmentPayload[];
};

export type GameResultPlayerRecord = {
  id: number;
  game_id: number;
  user_id: number | null;
  username: string;
  display_name: string;
  seat_number: number | null;
  role_name: string | null;
  faction: GamePlayerFaction | null;
  final_status: GamePlayerFinalStatus;
  is_winner: boolean | null;
  base_score: number;
  adjustment_score: number;
  final_score: number;
  judge_bonus_note: string | null;
  penalty_note: string | null;
  remarks: string | null;
  created_at: string;
  updated_at: string;
};

export type GameResultAdjustmentRecord = {
  id: number;
  game_player_id: number;
  target_seat_number: number | null;
  adjustment_type: ScoreAdjustmentType;
  delta: number;
  reason: string | null;
  created_by: number;
  created_at: string;
};

export type GameResultDraftResponse = {
  game: GameDetail;
  players: GameResultPlayerRecord[];
  adjustments: GameResultAdjustmentRecord[];
  format_roles: FormatRoleRecord[];
  selectable_players: SelectablePlayerRecord[];
  validation: ValidationSummary;
  editable: boolean;
};

export type EventDayDetail = EventDaySummary & {
  notes: string | null;
  season_name: string;
  registration_count: number;
  game_count: number;
  games: GameSummary[];
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

export type GameCreatePayload = {
  event_day_id: number;
  game_number: number;
  table_number: number;
  format_id: number;
  judge_user_id: number;
  game_type: GameType;
  status: GameStatus;
  notes?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
};

export type GameUpdatePayload = Partial<Omit<GameCreatePayload, "event_day_id">>;

export type GameFormatUpdatePayload = {
  is_active?: boolean;
  description?: string | null;
};


export class ApiRequestError extends Error {
  detail: unknown;

  constructor(message: string, detail: unknown) {
    super(message);
    this.name = "ApiRequestError";
    this.detail = detail;
  }
}

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
    let message = "Request failed.";
    let detail: unknown = null;
    try {
      // Result-entry validation returns structured details, so callers keep the
      // original payload for field-level feedback instead of flattening it.
      const body = (await response.json()) as { detail?: unknown; message?: string };
      detail = body.detail ?? body;
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (
        body.detail &&
        typeof body.detail === "object" &&
        "message" in body.detail &&
        typeof body.detail.message === "string"
      ) {
        message = body.detail.message;
      } else if (body.message) {
        message = body.message;
      }
    } catch {
      detail = "Request failed.";
      message = "Request failed.";
    }
    throw new ApiRequestError(message, detail);
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


export function getFormats(token: string): Promise<GameFormatRecord[]> {
  return request<GameFormatRecord[]>("/formats", withAuth(token));
}


export function getFormat(token: string, formatId: number): Promise<GameFormatDetail> {
  return request<GameFormatDetail>(`/formats/${formatId}`, withAuth(token));
}


export function updateFormat(
  token: string,
  formatId: number,
  payload: GameFormatUpdatePayload,
): Promise<GameFormatDetail> {
  return request<GameFormatDetail>(`/formats/${formatId}`, withAuth(token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }));
}


export function getEventDayGames(token: string, eventDayId: number): Promise<GameSummary[]> {
  return request<GameSummary[]>(`/event-days/${eventDayId}/games`, withAuth(token));
}


export function createGame(token: string, payload: GameCreatePayload): Promise<GameDetail> {
  return request<GameDetail>("/games", withAuth(token, {
    method: "POST",
    body: JSON.stringify(payload),
  }));
}


export function getGame(token: string, gameId: number): Promise<GameDetail> {
  return request<GameDetail>(`/games/${gameId}`, withAuth(token));
}


export function getGameResultDraft(
  token: string,
  gameId: number,
): Promise<GameResultDraftResponse> {
  return request<GameResultDraftResponse>(`/games/${gameId}/result-draft`, withAuth(token));
}


export function saveGameResultDraft(
  token: string,
  gameId: number,
  payload: GameResultDraftWritePayload,
): Promise<GameResultDraftResponse> {
  return request<GameResultDraftResponse>(`/games/${gameId}/result-draft`, withAuth(token, {
    method: "PUT",
    body: JSON.stringify(payload),
  }));
}


export function submitGameResult(
  token: string,
  gameId: number,
): Promise<GameResultDraftResponse> {
  return request<GameResultDraftResponse>(`/games/${gameId}/submit-result`, withAuth(token, {
    method: "POST",
  }));
}


export function updateGame(
  token: string,
  gameId: number,
  payload: GameUpdatePayload,
): Promise<GameDetail> {
  return request<GameDetail>(`/games/${gameId}`, withAuth(token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }));
}


export function getJudgeOwnedGames(
  token: string,
  status?: GameStatus,
): Promise<GameSummary[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<GameSummary[]>(`/judges/me/games${query}`, withAuth(token));
}


export function getJudgeOptions(token: string): Promise<JudgeOptionRecord[]> {
  return request<JudgeOptionRecord[]>("/users/judges", withAuth(token));
}
