# Wolfboard

Wolfboard is a web-based Werewolf tournament recording platform. This repository currently contains **Milestone 2: season, event day, registration, and check-in flows** on top of the Milestone 1 scaffold.

## Scope

Milestone 2 includes:

- Monorepo structure with `frontend/` and `backend/`
- FastAPI backend with PostgreSQL connectivity
- SQLAlchemy 2.0 models for:
  - `users`
  - `roles`
  - `user_roles`
  - `seasons`
  - `event_days`
  - `registrations`
- Alembic migration setup
- JWT authentication with multi-role responses
- FastAPI role dependencies for future resource-level authorization
- Next.js App Router frontend with:
  - login
  - role-aware home page
  - season list and detail pages
  - event-day detail page
  - admin season management page
  - admin event-day management page
  - admin registration and check-in page
- Docker Compose for local startup
- Seed script with sample users, season data, event days, and registrations

Milestone 2 does **not** include games, game players, scoreboards, result entry, or event flow logic.

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

The Docker setup will still run without a local `.env`, because `docker-compose.yml` includes safe default values for Milestone 1.

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

### 4. Seed default roles, users, seasons, event days, and registrations

```bash
uv run python -m app.scripts.seed
```

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
2. Seeds default roles, users, seasons, event days, and registrations
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

Sample seeded competition data:

- `S1 Trial Season` → active
- `2026-04-05 Official Match Day` → `open_for_registration`
- `2026-03-29 Community Match Day` → `registration_closed`

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

## Milestone 2 API Summary

- `GET /api/v1/seasons`
- `POST /api/v1/seasons`
- `GET /api/v1/seasons/{season_id}`
- `PATCH /api/v1/seasons/{season_id}`
- `GET /api/v1/seasons/{season_id}/event-days`
- `GET /api/v1/event-days/{event_day_id}`
- `POST /api/v1/event-days`
- `PATCH /api/v1/event-days/{event_day_id}`
- `GET /api/v1/event-days/{event_day_id}/registrations`
- `POST /api/v1/event-days/{event_day_id}/registrations`
- `PATCH /api/v1/registrations/{registration_id}`
- `PATCH /api/v1/registrations/{registration_id}/cancel`

## Validation Steps

### Player registration flow

1. Run `docker compose up --build`.
2. Open `http://localhost:3000/login`.
3. Sign in with `player_user / password123`.
4. Open `http://localhost:3000/event-days/1`.
5. Click `Register`.
6. Refresh the page and confirm your registration status now appears.

### Admin season and check-in flow

1. Sign in with `admin_user / password123`.
2. Open `http://localhost:3000/admin/seasons`.
3. Create a new season.
4. Open any season detail page and create an event day, or open an existing event day from the season detail.
5. Open `http://localhost:3000/admin/event-days/1/registrations`.
6. Change a registration row to `checked_in`.
7. Save the row and confirm the updated status persists.

### Backend verification flow

1. Open `http://localhost:8000/docs`.
2. Authenticate with `POST /api/v1/auth/login`.
3. Call `GET /api/v1/seasons` and `GET /api/v1/event-days/1`.
4. Confirm `player_user` can register for the open event day.
5. Confirm `admin_user` can update check-in status via `PATCH /api/v1/registrations/{id}`.

## Notes

- Passwords are stored as bcrypt hashes through `passlib`.
- Authorization is based on `users`, `roles`, and `user_roles`; there is no single `users.role_id`.
- Role checks are centralized in FastAPI dependencies so later milestones can layer in resource-level ownership rules.
- Normal users can only create registrations for themselves.
- Admins can manage seasons, event days, registrations, and check-in state.
