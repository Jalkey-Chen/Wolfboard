"""Shared SQLAlchemy declarative base."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models.

    Keeping a single declarative base ensures metadata collection stays
    predictable for Alembic migrations and model registration.
    """
