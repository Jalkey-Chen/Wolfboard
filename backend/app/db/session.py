"""Database engine and session utilities."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


# `pool_pre_ping` prevents stale connections from surviving container restarts,
# which is especially useful during local Docker-based development.
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Provide a request-scoped database session.

    Each API request gets a fresh SQLAlchemy session that is closed after the
    request finishes, regardless of success or failure.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
