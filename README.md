# Wolfboard

Wolfboard is a web-based Werewolf tournament recording platform. This repository currently contains **Milestone 5: admin confirmation, revision, formal score logs, leaderboard, player profiles, and audit tracking** on top of the Milestone 1 through Milestone 4 foundations.

## Scope

Milestone 5 includes:

- Monorepo structure with `frontend/` and `backend/`
- FastAPI backend with PostgreSQL connectivity
- SQLAlchemy 2.0 models for:
  - `users`
  - `roles`
  - `user_roles`
  - `seasons`
  - `event_days`
  - `registrations`
  - `game_formats`
  - `format_roles`
  - `games`
  - `game_players`
  - `score_adjustments`
  - `score_logs`
  - `result_confirmations`
  - `audit_logs`
  - `game_status_history`
- Alembic migrations through Milestone 5
- JWT authentication with multi-role responses
- FastAPI role dependencies for future resource-level authorization
- Next.js App Router frontend with:
  - login
  - role-aware home page
  - season list and detail pages
  - event-day detail page
  - preset format list and detail pages
  - game detail page
  - judge-owned games page
  - judge-owned result entry page
  - admin review queue page
  - admin review detail page
  - admin revision page
  - leaderboard page
  - player profile page
  - admin season management page
  - admin event-day management page
  - admin registration and check-in page
  - admin game management page
- Docker Compose for local startup
- Seed script with sample users, season data, event days, registrations, preset formats, sample games, and result-entry-ready player pools

Milestone 5 does **not** include:

- event-flow recording
- full event replay tooling
- automated rule adjudication

## Repository Structure

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
└─ README.md
```

## Environment Variables

Copy `.env.example` to `.env` if you want to customize defaults:

```powershell
Copy-Item .env.example .env
```

The Docker setup still runs without a local `.env`, because `docker-compose.yml` includes safe default values for local development.

## Local Backend Setup With uv

### 1. Install dependencies

```bash
cd backend
uv sync --dev
```

### 2. Configure environment

Create `backend/.env` if you want to run the backend outside Docker:

```env
DATABASE_URL=postgresql+psycopg://wolfboard:wolfboard@localhost:5432/wolfboard
JWT_SECRET_KEY=change-this-secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
BACKEND_CORS_ORIGINS=http://localhost:3000
```

### 3. Run migrations

```bash
uv run alembic upgrade head
```

To generate a new migration after model changes:

```bash
uv run alembic revision --autogenerate -m "describe your change"
```

### 4. Seed default roles and milestone sample data

```bash
uv run python -m app.scripts.seed
```

The seed is idempotent for the sample milestone data, so rerunning it is safe during local development.

### 5. Start the API

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Run backend tests

```bash
uv run pytest
```

## Local Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend API at `http://localhost:8000/api/v1` by default.

## Docker Startup

### Start the full stack

```bash
docker compose up --build
```

### Services

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

When the backend container starts, it automatically:

1. Applies Alembic migrations
2. Seeds default roles and milestone sample data
3. Starts the FastAPI server

## Seeded Test Accounts

All sample users use the password below:

```text
password123
```

Available accounts:

- `admin_user` → `["admin", "judge", "player"]`
- `judge_user` → `["judge", "player"]`
- `player_user` → `["player"]`

## Language Support

- The frontend now defaults to Simplified Chinese.
- Users can switch between Chinese and English from the login page or the authenticated site shell.
- The selected language is stored in browser `localStorage` under `wolfboard-language`.

## Seeded Sample Data

### Seasons and event days

- `S1 Trial Season` → `active`
- `2026-04-05 Official Match Day` → `open_for_registration`
- `2026-03-29 Community Match Day` → `registration_closed`

### Preset formats

The seed adds at least these 10 preset formats:

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

Each preset format also receives a seeded role composition in `format_roles`.

### Sample games

Seeded sample games include:

- Match Day A:
  - table 1 / game 1 / `official`
  - table 1 / game 2 / `official`
  - table 1 / game 3 / `official`
- Match Day B:
  - table 1 / game 1 / `fun`

The sample games intentionally assign at least one game to `judge_user` and at least one game to `admin_user`.

### Result-entry player pool

The open registration event day also seeds:

- `player_user`
- `sample_player_01` through `sample_player_10`

This gives the assigned judge enough selectable players to save and submit a realistic result draft during local testing.

## Authentication Flow

### `POST /api/v1/auth/login`

Accepts:

```json
{
  "username": "admin_user",
  "password": "password123"
}
```

Returns:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin_user",
    "display_name": "Admin User",
    "email": "admin@example.com",
    "account_status": "active",
    "created_at": "...",
    "updated_at": "..."
  },
  "roles": ["admin", "judge", "player"]
}
```

### `GET /api/v1/auth/me`

Requires:

```text
Authorization: Bearer <access_token>
```

Returns the authenticated user profile and all assigned system roles.

## Milestone 5 API Summary

Existing Milestone 1 to 4 routes remain available. Milestone 5 adds:

- `GET /api/v1/formats`
- `GET /api/v1/formats/{format_id}`
- `PATCH /api/v1/formats/{format_id}` for admin toggles
- `GET /api/v1/event-days/{event_day_id}/games`
- `POST /api/v1/games`
- `GET /api/v1/games/{game_id}`
- `PATCH /api/v1/games/{game_id}`
- `GET /api/v1/judges/me/games`
- `GET /api/v1/users/judges`
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

## Validation Steps

### Format verification

1. Run `docker compose up --build`.
2. Open `http://localhost:3000/login`.
3. Sign in with any seeded account.
4. Open `http://localhost:3000/formats`.
5. Confirm the preset format list is visible.
6. Open `http://localhost:3000/formats/1`.
7. Confirm the role composition table is visible.

### Admin game management flow

1. Sign in with `admin_user / password123`.
2. Open `http://localhost:3000/admin/event-days/1/games`.
3. Confirm the page shows the existing seeded games.
4. Create a new game by choosing:
   - table number
   - game number
   - format
   - judge
   - game type
   - status
5. Save the game.
6. Open `http://localhost:3000/event-days/1`.
7. Confirm the new game appears in the event-day game list.

### Judge visibility flow

1. Sign in with `judge_user / password123`.
2. Open `http://localhost:3000/judge/games`.
3. Confirm only judge-owned games are shown.
4. Open one of the listed game detail pages.
5. Confirm the page is accessible.
6. Try to mutate a game through an admin-only API such as `PATCH /api/v1/games/{id}` and confirm the backend returns `403`.

### Judge result-entry flow

1. Sign in with `judge_user / password123`.
2. Open `http://localhost:3000/judge/games`.
3. Open a judge-owned game whose status is `draft` or `in_progress`.
4. Click `Enter Result`.
5. Add player rows with seat number, player, role, faction, winner flag, final status, and remarks.
6. Add at least one score adjustment.
7. Click `Save Draft`.
8. Refresh the page and confirm the draft still exists.
9. Click `Submit Result`.
10. Confirm the page becomes read-only and the game status is now `submitted`.

### Submitted read-only verification

1. Refresh the same result-entry page after submission.
2. Confirm all inputs are read-only.
3. Confirm `Save Draft` and `Submit Result` are no longer available.
4. Open the game detail page and confirm the result summary is visible.

### Ownership and permission verification

1. Sign in with `player_user / password123`.
2. Try to open `http://localhost:3000/judge/games/1/result`.
3. Confirm the frontend redirects away from the page.
4. Call `GET /api/v1/games/{id}/result-draft` as `player_user`.
5. Confirm the backend returns `403`.
6. As `judge_user`, try to call `PUT /api/v1/games/{id}/result-draft` after the same game has been submitted.
7. Confirm the backend rejects the update.

### Admin confirmation flow

1. Sign in with `admin_user / password123`.
2. Open `http://localhost:3000/admin/games/review`.
3. Open one submitted game.
4. Click `Confirm Result`.
5. Open `http://localhost:3000/leaderboard`.
6. Confirm the leaderboard now reflects the effective score logs from that confirmed official game.

### Admin revision flow

1. Open a confirmed or revised game review page.
2. Click `Revise Result`.
3. Change one or more player outcomes or score adjustments.
4. Enter a revision reason.
5. Submit the revision.
6. Confirm the game status becomes `revised`.
7. Confirm old score logs are `voided` and new score logs are `effective`.

### Leaderboard verification

1. Open `http://localhost:3000/leaderboard`.
2. Select the active season.
3. Confirm only effective logs from `official` games with status `confirmed` or `revised` are counted.
4. Open one player profile from the leaderboard table and confirm the effective game history is visible.

### Backend verification flow

1. Open `http://localhost:8000/docs`.
2. Authenticate with `POST /api/v1/auth/login`.
3. Call `GET /api/v1/formats` and confirm the seeded presets are returned.
4. Call `GET /api/v1/event-days/1` and confirm the response includes a `games` array.
5. Call `GET /api/v1/judges/me/games` as `judge_user` and confirm only assigned games are returned.
6. Call `GET /api/v1/games/{id}/result-draft` as the assigned judge and confirm the payload includes `players`, `adjustments`, `format_roles`, `selectable_players`, and `validation`.
7. Call `POST /api/v1/games/{id}/submit-result` after saving a valid draft and confirm the returned status is `submitted`.
8. Call `POST /api/v1/games/{id}/confirm-result` as `admin_user` and confirm score logs are written.
9. Call `POST /api/v1/games/{id}/revise-result` and confirm the previous game score logs become `voided`.
10. Call `GET /api/v1/audit-logs?entity_type=game` and confirm confirmation or revision actions are present.
11. Call `GET /api/v1/players/{id}/profile` as the same player or an admin and confirm effective history is returned.

## Notes

- Passwords are stored as bcrypt hashes through `passlib`.
- Authorization is based on `users`, `roles`, and `user_roles`; there is no single `users.role_id`.
- Role checks are centralized in FastAPI dependencies so later milestones can layer in resource-level ownership rules.
- Admins manage seasons, event days, registrations, check-in state, formats, and games.
- Judges can only access the game queue and result-entry routes that belong to them.
- Result drafts always recompute base score, adjustment score, and final score on the backend.
- Leaderboards are built from `score_logs`, not directly from `game_players`.
- Admin confirmation and revision write both audit logs and game status history.
- Revising a confirmed game voids the old ledger rows and writes new effective rows instead of mutating history in place.
- Event flow is intentionally deferred to later milestones.
