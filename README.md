# Wolfboard

Wolfboard is a web-based Werewolf tournament recording platform. This repository currently contains **Milestone 1: project scaffold and authentication foundation**.

## Scope

Milestone 1 includes:

- Monorepo structure with `frontend/` and `backend/`
- FastAPI backend with PostgreSQL connectivity
- SQLAlchemy 2.0 models for `users`, `roles`, and `user_roles`
- Alembic migration setup
- JWT authentication with multi-role responses
- FastAPI role dependencies for future resource-level authorization
- Next.js App Router frontend with a login page and role-aware placeholder dashboard
- Docker Compose for local startup
- Seed script with default roles and sample users

Milestone 1 does **not** include seasons, event days, games, leaderboards, or event flow logic.

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

### 4. Seed default roles and users

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
2. Seeds default roles and users
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

## Validation Steps

1. Run `docker compose up --build`.
2. Open `http://localhost:3000/login`.
3. Sign in with `admin_user / password123`.
4. Confirm the frontend redirects to `/`.
5. Confirm the homepage shows the admin, judge, and player placeholder cards.
6. Open `http://localhost:8000/docs` and inspect `POST /api/v1/auth/login` plus `GET /api/v1/auth/me`.
7. Use the returned JWT in `GET /api/v1/auth/me` and confirm the response includes the full role array.

## Notes

- Passwords are stored as bcrypt hashes through `passlib`.
- Authorization is based on `users`, `roles`, and `user_roles`; there is no single `users.role_id`.
- Role checks are centralized in FastAPI dependencies so later milestones can layer in resource-level ownership rules.
