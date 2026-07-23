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
export type FormatSnapshotOrigin = "runtime_freeze" | "legacy_backfill";
export type GameType = "official" | "fun" | "practice";
export type GamePlayerFaction = "good" | "wolf" | "third_party";
export type GamePlayerFinalStatus = "alive" | "eliminated" | "unknown";
export type ScoreAdjustmentType =
  | "late_penalty"
  | "conduct_penalty"
  | "judge_bonus"
  | "manual_adjustment";
export type GamePlayStatus =
  | "scheduled"
  | "in_progress"
  | "ended"
  | "cancelled";
export type GameResultStatus =
  | "empty"
  | "draft"
  | "submitted"
  | "rejected"
  | "confirmed"
  | "revised";
export type GameEventPhase = "night" | "day";
export type GameEventSource = "manual" | "system" | "imported";
export type GameEventVisibility = "public" | "postgame_full" | "judge_only";
export type GameEventStatus = "active" | "superseded" | "voided";
export type GameEventType =
  | "phase_started"
  | "phase_completed"
  | "wolf_kill_selected"
  | "seer_checked"
  | "witch_saved"
  | "witch_poisoned"
  | "guard_protected"
  | "night_resolved"
  | "sheriff_candidate_declared"
  | "sheriff_candidate_withdrew"
  | "sheriff_vote_cast"
  | "sheriff_elected"
  | "exile_vote_cast"
  | "vote_tied"
  | "exile_revote_started"
  | "player_exiled"
  | "hunter_shot"
  | "wolf_self_exploded"
  | "wolf_king_shot"
  | "sheriff_badge_transferred"
  | "sheriff_badge_destroyed"
  | "player_died";
export type GameDeathCause =
  | "wolf_kill"
  | "witch_poison"
  | "exile"
  | "hunter_shot"
  | "wolf_king_shot"
  | "self_explosion"
  | "other";

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
  play_status: GamePlayStatus;
  result_status: GameResultStatus;
  started_at: string | null;
  ended_at: string | null;
  cancelled_at: string | null;
  cancelled_by: number | null;
  cancellation_reason: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  has_format_snapshot: boolean;
  format_snapshot_id: number | null;
};

export type GameFormatContextRole = {
  id: number | null;
  source_format_role_id: number | null;
  role_name: string;
  faction: FormatRoleFaction;
  role_count: number;
  display_order: number;
  metadata_json: Record<string, unknown> | null;
};

export type GameFormatContext = {
  is_frozen: boolean;
  source_format_id: number | null;
  snapshot_id: number | null;
  snapshot_origin: FormatSnapshotOrigin | null;
  snapshot_schema_version: number | null;
  format_key: string;
  format_name: string;
  player_count: number;
  category: FormatCategory;
  description: string | null;
  is_system_preset: boolean;
  frozen_at: string | null;
  frozen_by_user_id: number | null;
  roles: GameFormatContextRole[];
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

export type GameReviewSummary = GameSummary & {
  submitted_at: string | null;
  submitted_by: number | null;
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
  participant_id?: number | null;
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

export type GameRevisionWritePayload = GameResultDraftWritePayload & {
  reason: string;
};

export type GameResultPlayerRecord = {
  id: number;
  game_id: number;
  participant_id: number;
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
  format_context: GameFormatContext;
  format_roles: GameFormatContextRole[];
  selectable_players: SelectablePlayerRecord[];
  validation: ValidationSummary;
  editable: boolean;
};

export type GameEventBodyPayload = {
  phase: GameEventPhase;
  round_no: number;
  event_type: GameEventType;
  actor_participant_id?: number | null;
  target_participant_id?: number | null;
  secondary_target_participant_id?: number | null;
  payload?: Record<string, unknown>;
  occurred_at?: string | null;
  client_event_id?: string | null;
};

export type GameEventCorrectionPayload = GameEventBodyPayload & {
  reason: string;
};

export type GameEventParticipantSummary = {
  participant_id: number;
  seat_number: number | null;
  display_name_snapshot: string | null;
};

export type GameEventUserSummary = {
  user_id: number;
  username: string;
  display_name: string;
};

export type GameEventRecord = {
  id: number;
  game_id: number;
  sequence_no: number;
  logical_sequence_no: number;
  phase: GameEventPhase;
  round_no: number;
  event_type: GameEventType;
  actor_participant_id: number | null;
  target_participant_id: number | null;
  secondary_target_participant_id: number | null;
  actor: GameEventParticipantSummary | null;
  target: GameEventParticipantSummary | null;
  secondary_target: GameEventParticipantSummary | null;
  payload: Record<string, unknown>;
  visibility: GameEventVisibility;
  source: GameEventSource;
  schema_version: number;
  status: GameEventStatus;
  supersedes_event_id: number | null;
  revision_reason: string | null;
  invalidated_at: string | null;
  invalidated_by_user_id: number | null;
  invalidation_reason: string | null;
  created_by_user_id: number;
  created_by: GameEventUserSummary;
  created_at: string;
  occurred_at: string | null;
  client_event_id: string | null;
};

export type GameEventPayloadFieldSemantic =
  | "participant_id"
  | "participant_id_list"
  | "event_id"
  | "event_id_list";

export type JsonSchemaNode = {
  type?: string | string[];
  enum?: Array<string | number | boolean | null>;
  const?: string | number | boolean | null;
  default?: unknown;
  minimum?: number;
  exclusiveMinimum?: number;
  maxLength?: number;
  minItems?: number;
  uniqueItems?: boolean;
  additionalProperties?: boolean | JsonSchemaNode;
  properties?: Record<string, JsonSchemaNode>;
  required?: string[];
  items?: JsonSchemaNode;
  anyOf?: JsonSchemaNode[];
};

export type GameEventDefinition = {
  event_type: GameEventType;
  allowed_phases: GameEventPhase[];
  default_visibility: GameEventVisibility;
  required_actor: boolean;
  required_target: boolean;
  allows_actor: boolean;
  allows_target: boolean;
  allows_secondary_target: boolean;
  allowed_sources: GameEventSource[];
  schema_version: number;
  payload_schema: JsonSchemaNode;
  payload_field_semantics: Record<string, GameEventPayloadFieldSemantic>;
};

export type ProjectionIssueSeverity = "info" | "warning";

export type GameProjectionIssue = {
  code: string;
  severity: ProjectionIssueSeverity;
  message_key: string;
  event_ids: number[];
  participant_ids: number[];
  round_no: number | null;
  phase: GameEventPhase | null;
  details: Record<string, unknown>;
};

export type GameDerivedPhaseState = {
  current_phase: GameEventPhase | null;
  current_round_no: number | null;
  phase_is_open: boolean;
  phase_started_event_id: number | null;
  last_completed_phase: GameEventPhase | null;
  last_completed_round_no: number | null;
  last_completed_event_id: number | null;
  last_observed_phase: GameEventPhase | null;
  last_observed_round_no: number | null;
  last_observed_event_id: number | null;
};

export type GameDerivedParticipantState = {
  participant_id: number;
  user_id: number | null;
  seat_number: number | null;
  display_name_snapshot: string | null;
  recorded_role_name: string | null;
  recorded_faction: GamePlayerFaction | null;
  is_active_in_game: boolean;
  has_exile_record: boolean;
  has_death_record: boolean;
  exile_event_ids: number[];
  death_event_ids: number[];
  exit_event_ids: number[];
  first_exit_logical_sequence: number | null;
  latest_exit_logical_sequence: number | null;
};

export type GameDerivedSheriffState = {
  badge_status: "unassigned" | "held" | "destroyed";
  current_sheriff_participant_id: number | null;
  elected_event_id: number | null;
  last_transfer_event_id: number | null;
  destroyed_event_id: number | null;
  current_candidate_participant_ids: number[];
  withdrawn_participant_ids: number[];
  declaration_provenance: Array<{ participant_id: number; event_ids: number[] }>;
  withdrawal_provenance: Array<{ participant_id: number; event_ids: number[] }>;
};

export type GameDerivedVoteRecord = {
  event_id: number;
  voter_participant_id: number | null;
  target_participant_id: number | null;
  vote_weight: number;
  logical_sequence_no: number;
};

export type GameDerivedTallyEntry = {
  participant_id: number;
  vote_weight: number;
};

export type GameDerivedBallotState = {
  vote_kind: "sheriff" | "exile";
  round_no: number;
  ballot_no: number;
  vote_event_ids: number[];
  vote_records: GameDerivedVoteRecord[];
  abstention_records: GameDerivedVoteRecord[];
  voter_participant_ids: number[];
  duplicate_voter_participant_ids: number[];
  raw_tally: GameDerivedTallyEntry[];
  computed_tally: GameDerivedTallyEntry[] | null;
  tally_is_unambiguous: boolean;
  explicit_tie_records: Array<{
    event_id: number;
    candidate_participant_ids: number[];
  }>;
  revote_records: Array<{
    event_id: number;
    eligible_participant_ids: number[];
  }>;
  explicit_outcome_event_ids: number[];
};

export type GameRecordedActionUsage = {
  participant_id: number;
  recorded_seer_check_count: number;
  recorded_witch_antidote_count: number;
  recorded_witch_poison_count: number;
  recorded_guard_protection_count: number;
  recorded_hunter_shot_count: number;
  recorded_wolf_king_shot_count: number;
  recorded_wolf_self_explosion_count: number;
  recorded_sheriff_vote_count: number;
  recorded_exile_vote_count: number;
};

export type GameRecordedActionSummary = {
  event_type: string;
  phase: GameEventPhase;
  round_no: number;
  actor_participant_id: number | null;
  event_ids: number[];
  recorded_count: number;
  latest_recorded_target_participant_id: number | null;
};

export type GameDerivedRoundSummary = {
  round_no: number;
  phase: GameEventPhase;
  event_count: number;
  event_ids: number[];
  phase_started_event_ids: number[];
  phase_completed_event_ids: number[];
  night_resolved_event_ids: number[];
  event_type_counts: Array<{ event_type: string; count: number }>;
};

export type GameDerivedState = {
  projection_version: 1;
  projection_kind: "effective_event_projection";
  game_id: number;
  through_logical_sequence: number | null;
  event_ledger_head_sequence: number;
  effective_event_count: number;
  last_applied_logical_sequence: number | null;
  has_format_snapshot: boolean;
  is_rule_engine_result: false;
  format_snapshot_id: number | null;
  format_key: string | null;
  format_name: string | null;
  snapshot_schema_version: number | null;
  phase: GameDerivedPhaseState;
  participants: GameDerivedParticipantState[];
  sheriff: GameDerivedSheriffState;
  ballots: GameDerivedBallotState[];
  recorded_action_usage: GameRecordedActionUsage[];
  recorded_actions: GameRecordedActionSummary[];
  round_summaries: GameDerivedRoundSummary[];
  night_resolutions: Array<{
    event_id: number;
    round_no: number;
    no_public_death: boolean;
    note: string | null;
  }>;
  issues: GameProjectionIssue[];
};

export type GameConfirmPayload = {
  comment?: string | null;
};

export type GameRejectPayload = {
  comment: string;
};

export type LeaderboardEntry = {
  ranking: number;
  user_id: number;
  username: string;
  display_name: string;
  total_score: number;
  games_played: number;
  wins: number;
};

export type PlayerProfileHistoryRecord = {
  game_id: number;
  season_id: number;
  season_name: string;
  event_day_id: number;
  event_day_title: string;
  event_day_date: string;
  table_number: number;
  game_number: number;
  game_type: GameType;
  play_status: GamePlayStatus;
  result_status: GameResultStatus;
  delta: number;
  balance_after: number;
  effective_status: "pending" | "effective" | "voided";
  created_at: string;
};

export type PlayerProfileRecord = {
  user_id: number;
  username: string;
  display_name: string;
  total_score: number;
  games_played: number;
  history: PlayerProfileHistoryRecord[];
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
  notes?: string | null;
};

export type GameUpdatePayload = Partial<Omit<GameCreatePayload, "event_day_id">>;

export type GameFormatUpdatePayload = {
  is_active?: boolean;
  description?: string | null;
};


export class ApiRequestError extends Error {
  detail: unknown;
  status: number | null;

  constructor(message: string, detail: unknown, status: number | null = null) {
    super(message);
    this.name = "ApiRequestError";
    this.detail = detail;
    this.status = status;
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
    throw new ApiRequestError(message, detail, response.status);
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


export function getGameFormatContext(token: string, gameId: number): Promise<GameFormatContext> {
  return request<GameFormatContext>(`/games/${gameId}/format-context`, withAuth(token));
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


export function getReviewQueue(token: string): Promise<GameReviewSummary[]> {
  return request<GameReviewSummary[]>("/admin/games/review", withAuth(token));
}


export function confirmGameResult(
  token: string,
  gameId: number,
  payload: GameConfirmPayload = {},
): Promise<GameResultDraftResponse> {
  return request<GameResultDraftResponse>(`/games/${gameId}/confirm-result`, withAuth(token, {
    method: "POST",
    body: JSON.stringify(payload),
  }));
}


export function rejectGameResult(
  token: string,
  gameId: number,
  payload: GameRejectPayload,
): Promise<GameResultDraftResponse> {
  return request<GameResultDraftResponse>(`/games/${gameId}/reject-result`, withAuth(token, {
    method: "POST",
    body: JSON.stringify(payload),
  }));
}


export function reviseGameResult(
  token: string,
  gameId: number,
  payload: GameRevisionWritePayload,
): Promise<GameResultDraftResponse> {
  return request<GameResultDraftResponse>(`/games/${gameId}/revise-result`, withAuth(token, {
    method: "POST",
    body: JSON.stringify(payload),
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


export function startGame(token: string, gameId: number): Promise<GameDetail> {
  return request<GameDetail>(`/games/${gameId}/start`, withAuth(token, { method: "POST" }));
}


export function endGame(token: string, gameId: number): Promise<GameDetail> {
  return request<GameDetail>(`/games/${gameId}/end`, withAuth(token, { method: "POST" }));
}


export function cancelGame(token: string, gameId: number, reason: string): Promise<GameDetail> {
  return request<GameDetail>(`/games/${gameId}/cancel`, withAuth(token, {
    method: "POST",
    body: JSON.stringify({ reason }),
  }));
}


export function listGameEvents(
  token: string,
  gameId: number,
  options: {
    view?: "effective" | "ledger";
    afterLedgerSequence?: number;
    afterLogicalSequence?: number;
    limit?: number;
  } = {},
): Promise<GameEventRecord[]> {
  const params = new URLSearchParams();
  if (options.view) params.set("view", options.view);
  if (options.afterLedgerSequence !== undefined) {
    params.set("after_ledger_sequence", String(options.afterLedgerSequence));
  }
  if (options.afterLogicalSequence !== undefined) {
    params.set("after_logical_sequence", String(options.afterLogicalSequence));
  }
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  const query = params.size > 0 ? `?${params.toString()}` : "";
  return request<GameEventRecord[]>(`/games/${gameId}/events${query}`, withAuth(token));
}


export function listGameEventDefinitions(token: string): Promise<GameEventDefinition[]> {
  return request<GameEventDefinition[]>("/game-events/definitions", withAuth(token));
}

export function getGameDerivedState(
  token: string,
  gameId: number,
  throughLogicalSequence?: number,
): Promise<GameDerivedState> {
  const params = new URLSearchParams();
  if (throughLogicalSequence !== undefined) {
    params.set("through_logical_sequence", String(throughLogicalSequence));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  return request<GameDerivedState>(
    `/games/${gameId}/derived-state${query}`,
    withAuth(token),
  );
}


export function getGameEvent(
  token: string,
  gameId: number,
  eventId: number,
): Promise<GameEventRecord> {
  return request<GameEventRecord>(`/games/${gameId}/events/${eventId}`, withAuth(token));
}


export function createGameEvent(
  token: string,
  gameId: number,
  payload: GameEventBodyPayload,
): Promise<GameEventRecord> {
  return request<GameEventRecord>(`/games/${gameId}/events`, withAuth(token, {
    method: "POST",
    body: JSON.stringify(payload),
  }));
}


export function correctGameEvent(
  token: string,
  gameId: number,
  eventId: number,
  payload: GameEventCorrectionPayload,
): Promise<GameEventRecord> {
  return request<GameEventRecord>(`/games/${gameId}/events/${eventId}/correct`, withAuth(token, {
    method: "POST",
    body: JSON.stringify(payload),
  }));
}


export function voidGameEvent(
  token: string,
  gameId: number,
  eventId: number,
  reason: string,
): Promise<GameEventRecord> {
  return request<GameEventRecord>(`/games/${gameId}/events/${eventId}/void`, withAuth(token, {
    method: "POST",
    body: JSON.stringify({ reason }),
  }));
}


export function getJudgeOwnedGames(
  token: string,
  filters: { playStatus?: GamePlayStatus; resultStatus?: GameResultStatus } = {},
): Promise<GameSummary[]> {
  const params = new URLSearchParams();
  if (filters.playStatus) params.set("play_status", filters.playStatus);
  if (filters.resultStatus) params.set("result_status", filters.resultStatus);
  const query = params.size > 0 ? `?${params.toString()}` : "";
  return request<GameSummary[]>(`/judges/me/games${query}`, withAuth(token));
}


export function getJudgeOptions(token: string): Promise<JudgeOptionRecord[]> {
  return request<JudgeOptionRecord[]>("/users/judges", withAuth(token));
}


export function getSeasonLeaderboard(
  token: string,
  seasonId: number,
): Promise<LeaderboardEntry[]> {
  return request<LeaderboardEntry[]>(`/seasons/${seasonId}/leaderboard`, withAuth(token));
}


export function getPlayerProfile(
  token: string,
  playerId: number,
): Promise<PlayerProfileRecord> {
  return request<PlayerProfileRecord>(`/players/${playerId}/profile`, withAuth(token));
}
