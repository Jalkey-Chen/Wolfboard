"""Smoke tests for the isolated PostgreSQL integration-test database."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session


@pytest.mark.integration
def test_database_is_postgresql_at_alembic_head(db_session: Session) -> None:
    database_version = db_session.scalar(text("SELECT version()"))
    alembic_revision = db_session.scalar(text("SELECT version_num FROM alembic_version"))

    assert database_version is not None
    assert database_version.startswith("PostgreSQL")
    assert alembic_revision == "20260721_0007"
