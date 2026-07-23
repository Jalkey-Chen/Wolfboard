# Wolfboard

[中文](./README.md) | [English](./README.en.md)

Wolfboard is a web-based Werewolf tournament recording and operations platform.

The repository currently includes:

- `Milestone 1`: authentication, multi-role access, project scaffold
- `Milestone 2`: seasons, event days, registrations, check-in
- `Milestone 3`: preset formats, game management, judge assignment
- `Milestone 4`: result entry, draft persistence, result submission
- `Milestone 5`: admin confirmation, revision, formal score logs, leaderboard, player profiles, and audit logs
- bilingual UI support with **Chinese as the default language**

## Overview

Wolfboard is not meant to be a brochure site. It is a long-term tournament operations system focused on:

1. structured data
2. efficient live operations
3. role-aware access control
4. auditable score and result changes
5. future extension toward event-flow recording

The current build already forms a full result-layer workflow:

1. users sign in with role-based access
2. admins create seasons and event days
3. players register and admins check them in
4. admins create games and assign judges
5. judges save drafts and submit results
6. admins confirm or revise results
7. the system writes formal score logs and updates the leaderboard

## Current Capabilities

| Module | Status | Notes |
| --- | --- | --- |
| Authentication and RBAC | Done | multi-role model with `users + roles + user_roles` |
| Seasons and event days | Done | create, edit, and browse |
| Registration and check-in | Done | player sign-up and admin check-in |
| Formats and role composition | Done | preset formats with seeded role lists |
| Game management | Done | create games, assign formats and judges |
| Result entry | Done | judge-owned draft save and submission |
| Review and revision | Done | admin confirmation, rejection, and revision |
| Formal score ledger | Done | `score_logs` drive official standings |
| Leaderboard and player profile | Done | season standings and player history |
| Audit and traceability | Done | `audit_logs` and `game_status_history` |
| Event flow | Not started | reserved for later milestones |

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js App Router, TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic, Alembic |
| Database | PostgreSQL |
| Python environment | uv |
| Local development | Docker Compose |

## Repository Layout

```text
repo-root/
├─ frontend/
│  ├─ app/
│  ├─ components/
│  ├─ lib/
│  ├─ Dockerfile
│  └─ package.json
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ db/
│  │  ├─ models/
│  │  ├─ schemas/
│  │  ├─ scripts/
│  │  └─ services/
│  ├─ migrations/
│  ├─ tests/
│  ├─ Dockerfile
│  ├─ alembic.ini
│  └─ pyproject.toml
├─ docker-compose.yml
├─ .env.example
├─ README.md
└─ README.en.md
```

## Quick Start

### Full stack with Docker

```bash
docker compose up --build
```

Available services:

| Service | URL |
| --- | --- |
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| Swagger Docs | `http://localhost:8000/docs` |
| PostgreSQL | `localhost:5432` |

When the backend container starts, it automatically:

1. runs Alembic migrations
2. seeds sample milestone data
3. starts the FastAPI server

### Run backend locally

```bash
cd backend
uv sync --dev
uv run alembic upgrade head
uv run python -m app.scripts.seed
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run frontend locally

```bash
cd frontend
npm install
npm run dev
```

By default, the frontend expects:

```text
http://localhost:8000/api/v1
```

## Environment Variables

If you want a local `.env` file, copy:

```powershell
Copy-Item .env.example .env
```

If you run the backend outside Docker, you can create `backend/.env` like this:

```env
DATABASE_URL=postgresql+psycopg://wolfboard:wolfboard@localhost:5432/wolfboard
JWT_SECRET_KEY=change-this-secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
BACKEND_CORS_ORIGINS=http://localhost:3000
```

## Seeded Test Accounts

All sample accounts use:

```text
password123
```

| Username | Roles |
| --- | --- |
| `admin_user` | `admin + judge + player` |
| `judge_user` | `judge + player` |
| `player_user` | `player` |

## Seeded Sample Data

### Season and event days

- `S1 试验赛季`
- `2026-04-05 正赛日`
- `2026-03-29 社群比赛日`

### Preset formats

The seed includes at least these 10 preset formats:

- `预女猎白混`
- `狼王守卫`
- `狼美骑士`
- `机械狼通灵师`
- `梦魇摄梦人`
- `孤注一掷`
- `盗宝大师`
- `假面舞会`
- `唯邻是从`
- `魔幻对决`

Each preset format also includes seeded `format_roles`.

### Sample games

The seed creates:

- 3 official games
- 1 fun game
- at least one game assigned to `judge_user`
- at least one game assigned to `admin_user`

## Language Support

The frontend supports both Chinese and English:

- default language: Simplified Chinese
- switchable languages: Chinese / English
- switch entry points: login page and authenticated shell
- persistence: browser `localStorage`
- storage key: `wolfboard-language`

Notes:

- system-owned copy and preset format descriptions are localized
- user-authored free-text content is not auto-translated

## Key Business Rules

### Multi-role permissions

The system does **not** use a single `users.role_id`.

Instead it uses:

- `users`
- `roles`
- `user_roles`

One user can hold multiple system roles, such as:

- `player + judge`
- `player + admin`
- `player + judge + admin`

### Scoring rules

Current base scoring rules:

- good-side win: `+1`
- wolf-side win: `+1.5`
- loss: `-1`

Adjustments are stored in `score_adjustments`, while official standings are driven by `score_logs`.

### Leaderboard rules

The leaderboard counts only:

- `game.result_status IN (confirmed, revised)`
- `game.play_status = ended`
- `game.game_type = official`
- `score_logs.effective_status = effective`

That means:

- the leaderboard is **not** built directly from `game_players`
- revisions void old ledger rows
- new effective ledger rows are rebuilt after revision

### Independent game and result state machines

- New games are fixed at `play_status=scheduled` and `result_status=empty`; create and generic PATCH accept neither state nor lifecycle timestamps.
- Play follows `scheduled -> in_progress -> ended`. Admins can cancel scheduled/in-progress games and ended games that have not entered review through `POST /games/{id}/start|end|cancel`.
- Results follow `empty -> draft -> submitted -> confirmed`; rejection follows `submitted -> rejected -> draft`, and admins can revise submitted/confirmed/revised results into revised.
- The first draft save temporarily auto-starts a scheduled game, while submitting an in-progress draft ends play in the same transaction. A future event-entry UI will start games explicitly.
- Game number, format, and game type freeze once play or result entry begins. Cancelled games are read-only. The current cancellation action cannot void submitted or effective score ledgers.
- State operations use PostgreSQL `SELECT ... FOR UPDATE` and revalidate both states after locking. Conflicts return `409` without partial history, audit, confirmation, or ledger rows.
- `GameStatusHistory` records actual value changes with `status_scope=play|result` and a `transition_key`. Repeated revisions do not add same-value history, but every revision still writes ResultConfirmation and AuditLog.
- Start, end, cancel, first/post-rejection draft save, submit, reject, confirm, and revise all write AuditLog. See `docs/architecture/game-state-machines.md`.

### ScoreLog ledger semantics

- Confirmed or revised official, fun, and practice games may all retain a `ScoreLog.delta`.
- `effective_status=effective` identifies the current ledger version. PostgreSQL enforces at most one effective row per `game_id + user_id + source_type` with a partial unique index.
- `balance_after` is the player's formal standing balance at that point and matches leaderboard semantics. Only official games change it; fun and practice rows retain their delta without increasing or decreasing the formal balance.
- Revision marks old effective rows `voided`, writes effective rows for the new result, and recalculates later season balances for the union of old and new players.

### Stable in-game participants

- `GameParticipant` is the stable identity inside one game. It owns the mutable `user_id`, seat, and game-time display-name snapshot and is the intended future event actor/target reference.
- `GamePlayer` now owns only role, faction, final state, outcome, score, notes, and adjustments. It no longer duplicates user or seat columns.
- Result APIs still flatten `user_id` and `seat_number` for compatibility and now include `participant_id`; later PUT and revise requests should return that ID unchanged.
- Draft writes reconcile by participant: retained rows update in place, additions create rows, and removals delete only their own aggregate. Identical repeated saves preserve participant and result IDs.
- Display names are snapshotted when an account is bound and do not follow later account renames. Guest creation UI remains deferred.
- See `docs/architecture/game-participants.md` for the boundary.

### Immutable per-game format snapshots

- `GameFormat` / `FormatRole` are mutable templates for scheduled games. After start, `GameFormatSnapshot` / `GameFormatRoleSnapshot` are the sole historical authority.
- Explicit start and first-draft auto-start validate and copy the format, every role row, and independent JSON metadata inside the same Game row-lock transaction. Failure leaves no snapshot, state, history, or audit side effects.
- Result read, save, submit, review, and revision use the snapshot whenever one exists. Later source renames, deactivation, or seed role replacement cannot reinterpret historical games.
- `GET /api/v1/games/{game_id}/format-context` explicitly returns live or frozen context. List payloads expose only `has_format_snapshot` and `format_snapshot_id`.
- Migration `20260722_0009` creates `legacy_backfill` snapshots for games with play or result evidence. They represent the template available during migration, not provable event-time configuration.
- Snapshots have no mutation API. Services and seed do not replace them; only physical Game deletion cascades. See `docs/architecture/game-format-snapshots.md`.

### Structured game-event ledger

- `GameEvent` records in-game actions and resolved facts without duplicating Game lifecycle, result review, scoring, or state history. Normal appends are facts; only correction and void operations also write AuditLog.
- `GET /api/v1/games/{game_id}/derived-state` deterministically projects the current effective timeline into explicit phase, exit records, sheriff state, ballots, recorded action counts, and consistency issues. It is read-only recorded state, not an automated ruling or rules-engine result.
- Optional `through_logical_sequence` reads a logical prefix of the current effective timeline. It cannot reconstruct the historical as-of view before correction or voiding.
- The pure projector neither accesses the database nor reads the clock, writes events, or changes Game. `projection_version = 1` fixes the current semantics; see `docs/architecture/game-state-projection.md`.
- `sequence_no` is immutable ledger order and `logical_sequence_no` is effective timeline position. Correction appends a replacement at the same logical position and retains the old version as `superseded`; void retains the original body as `voided`.
- A Game row lock and `next_event_sequence` serialize allocation. `client_event_id` provides per-game retry idempotency, and a partial unique index permits at most one active version per logical position.
- Event actors and targets use stable `GameParticipant` rows and require frozen format context. Once any event references a participant, result drafts cannot delete it or change its user/seat binding.
- M6.1 permits only admins and the assigned judge to read or write. Submission locks the ledger and rejection reopens it. Skill, phase, death-causality, and victory rules are not executed.
- See `docs/architecture/game-event-ledger.md` for the complete V1 taxonomy, payload contracts, visibility, and concurrency semantics.

## Useful Local Verification Flows

### Sign-in check

1. Open `http://localhost:3000/login`
2. Sign in with `admin_user / password123`
3. Confirm the home page and navigation render correctly
4. Switch between Chinese and English

### Judge result-entry check

1. Sign in as `judge_user`
2. Open `/judge/games`
3. Enter a `draft` or `in_progress` game
4. Save a result draft
5. Submit the result
6. Confirm the page becomes read-only

### Admin review check

1. Sign in as `admin_user`
2. Open `/admin/games/review`
3. Open a submitted game
4. Confirm the result
5. Open `/leaderboard`
6. Confirm the leaderboard updates

### Admin revision check

1. Open the revision page from the review flow
2. Modify player outcomes or score adjustments
3. Enter a revision reason
4. Submit the revision
5. Confirm old `score_logs` become `voided`
6. Confirm new `score_logs` are generated

## Main APIs

This is only a compact list of key routes:

### Auth

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### Tournament organization

- `GET /api/v1/seasons`
- `POST /api/v1/seasons`
- `GET /api/v1/seasons/{season_id}`
- `PATCH /api/v1/seasons/{season_id}`
- `GET /api/v1/event-days/{event_day_id}`
- `POST /api/v1/event-days`
- `PATCH /api/v1/event-days/{event_day_id}`
- `POST /api/v1/event-days/{event_day_id}/registrations`
- `GET /api/v1/event-days/{event_day_id}/registrations`

### Formats and games

- `GET /api/v1/formats`
- `GET /api/v1/formats/{format_id}`
- `GET /api/v1/event-days/{event_day_id}/games`
- `POST /api/v1/games`
- `GET /api/v1/games/{game_id}`
- `GET /api/v1/games/{game_id}/format-context`
- `PATCH /api/v1/games/{game_id}`
- `POST /api/v1/games/{game_id}/start`
- `POST /api/v1/games/{game_id}/end`
- `POST /api/v1/games/{game_id}/cancel`
- `GET /api/v1/judges/me/games`

### Results and scoring

- `GET /api/v1/games/{game_id}/result-draft`
- `PUT /api/v1/games/{game_id}/result-draft`
- `POST /api/v1/games/{game_id}/submit-result`
- `GET /api/v1/admin/games/review`
- `POST /api/v1/games/{game_id}/confirm-result`
- `POST /api/v1/games/{game_id}/reject-result`
- `POST /api/v1/games/{game_id}/revise-result`
- `GET /api/v1/seasons/{season_id}/leaderboard`
- `GET /api/v1/players/{player_id}/profile`
- `GET /api/v1/audit-logs`

### Game events

- `GET /api/v1/game-events/definitions`
- `GET /api/v1/games/{game_id}/derived-state`
- `GET /api/v1/games/{game_id}/events`
- `GET /api/v1/games/{game_id}/events/{event_id}`
- `POST /api/v1/games/{game_id}/events`
- `POST /api/v1/games/{game_id}/events/{event_id}/correct`
- `POST /api/v1/games/{game_id}/events/{event_id}/void`

## Migrations

Run migrations:

```bash
cd backend
uv run alembic upgrade head
```

Generate a new migration:

```bash
cd backend
uv run alembic revision --autogenerate -m "describe your change"
```

## Tests

Install frontend dependencies from the committed `package-lock.json` and run the same checks as CI:

```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm run test
npm run build
```

Use the locked `uv.lock` dependencies for backend checks:

```bash
cd backend
uv sync --frozen --dev
uv run pytest -q
uv run alembic heads
```

`pytest` runs both unit tests and integration tests against real PostgreSQL. The integration suite neither substitutes SQLite nor runs the seed script:

- Without `TEST_DATABASE_ADMIN_URL`, the fixtures start local PostgreSQL from `docker-compose.test.yml`.
- Each pytest session creates a randomly named `wolfboard_test_*` database and runs `alembic upgrade head` automatically.
- Application tables are truncated before each test while the Alembic revision is preserved. The random database and any fixture-owned containers are removed after success or failure.
- CI may point `TEST_DATABASE_ADMIN_URL` at its dedicated PostgreSQL service. Never point it at a development or production database.

The local test PostgreSQL service can also be started explicitly:

```bash
docker compose --project-name wolfboard-tests -f docker-compose.test.yml up --detach --wait
cd backend
uv run pytest -q
```

When no external test URL is set, pytest owns and removes that Compose service at the end of the run.

### CI quality gates

`.github/workflows/quality.yml` runs two parallel jobs on pushes and pull requests:

- Frontend: `npm ci`, ESLint, TypeScript checking, Vitest, and a production build.
- Backend: `uv sync --frozen --dev`, a CI-only PostgreSQL service, `alembic upgrade head`, and `pytest -q`.
- CI does not run the seed script and does not require real secrets.

### Known-defect baseline

M6.0C converts the final strict xfail (a repeated draft save changing `GamePlayer.id`) into a normal passing regression test. The suite now has `0 xfailed` tests.

## Not Implemented Yet

The judge event workbench is available at `/judge/games/{game_id}/events`. It consumes authoritative constraints from the server definitions registry and supports all 22 V1 events, effective and ledger views, correction, voiding, and safe `client_event_id` retries. Versioned local drafts contain neither authentication tokens nor a complete Game object.

The deterministic read-only backend projection is now available, but it is not yet displayed in the event workbench. Still deferred:

- the workbench state panel and public/full replay projections
- automatic adjudication
- replay tooling
- complex rules engine

These will be addressed in later milestones.

## Development Conventions

- do not work directly on `main`
- branch from the latest `dev`
- use Conventional Commits
- merge important changes through PRs
- keep code comments and docstrings in English

## License

No standalone open-source license is declared yet. Add one explicitly before public distribution.
