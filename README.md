# Wolfboard

Wolfboard is a web-based Werewolf tournament recording platform. This repository currently contains **Milestone 3: preset formats, event-day game management, judge assignment, and judge-owned game browsing** on top of the Milestone 1 and Milestone 2 foundations.

## Scope

Milestone 3 includes:

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
- Alembic migrations through Milestone 3
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
  - admin season management page
  - admin event-day management page
  - admin registration and check-in page
  - admin game management page
- Docker Compose for local startup
- Seed script with sample users, season data, event days, registrations, preset formats, and sample games

Milestone 3 does **not** include:

- `game_players`
- result entry
- scoring or score logs
- leaderboard logic
- event-flow recording

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

## Milestone 3 API Summary

Existing Milestone 1 and 2 routes remain available. Milestone 3 adds:

- `GET /api/v1/formats`
- `GET /api/v1/formats/{format_id}`
- `PATCH /api/v1/formats/{format_id}` for admin toggles
- `GET /api/v1/event-days/{event_day_id}/games`
- `POST /api/v1/games`
- `GET /api/v1/games/{game_id}`
- `PATCH /api/v1/games/{game_id}`
- `GET /api/v1/judges/me/games`
- `GET /api/v1/users/judges`

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

### Backend verification flow

1. Open `http://localhost:8000/docs`.
2. Authenticate with `POST /api/v1/auth/login`.
3. Call `GET /api/v1/formats` and confirm the seeded presets are returned.
4. Call `GET /api/v1/event-days/1` and confirm the response includes a `games` array.
5. Call `GET /api/v1/judges/me/games` as `judge_user` and confirm only assigned games are returned.

## Notes

- Passwords are stored as bcrypt hashes through `passlib`.
- Authorization is based on `users`, `roles`, and `user_roles`; there is no single `users.role_id`.
- Role checks are centralized in FastAPI dependencies so later milestones can layer in resource-level ownership rules.
- Admins manage seasons, event days, registrations, check-in state, formats, and games.
- Judges can only access the game queue that belongs to them.
- Result-entry, player-per-game data, score logs, and event flow are intentionally deferred to later milestones.
