"""Top-level API router registration for versioned endpoints."""

from fastapi import APIRouter

from app.api.routes import auth
from app.api.routes import event_days
from app.api.routes import formats
from app.api.routes import games
from app.api.routes import registrations
from app.api.routes import seasons


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(seasons.router)
api_router.include_router(event_days.router)
api_router.include_router(registrations.router)
api_router.include_router(formats.router)
api_router.include_router(games.router)
