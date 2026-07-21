"""PostgreSQL integration-test fixtures for the Wolfboard API."""

from collections.abc import Generator
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
TEST_COMPOSE_FILE = REPOSITORY_ROOT / "docker-compose.test.yml"
DEFAULT_ADMIN_DATABASE_URL = (
    "postgresql+psycopg://wolfboard_test:wolfboard_test@localhost:55432/postgres"
)
START_LOCAL_POSTGRES = "TEST_DATABASE_ADMIN_URL" not in os.environ
ADMIN_DATABASE_URL = make_url(
    os.environ.get("TEST_DATABASE_ADMIN_URL", DEFAULT_ADMIN_DATABASE_URL)
)
TEST_DATABASE_NAME = f"wolfboard_test_{uuid4().hex}"
TEST_DATABASE_URL = ADMIN_DATABASE_URL.set(database=TEST_DATABASE_NAME)


if not ADMIN_DATABASE_URL.drivername.startswith("postgresql"):
    raise RuntimeError("TEST_DATABASE_ADMIN_URL must use PostgreSQL.")
if not re.fullmatch(r"wolfboard_test_[0-9a-f]{32}", TEST_DATABASE_NAME):
    raise RuntimeError("Refusing to use an unsafe test database name.")

# Alembic and the application settings both resolve DATABASE_URL at import time.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL.render_as_string(hide_password=False)


def _run_test_compose(*arguments: str) -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            "wolfboard-tests",
            "--file",
            str(TEST_COMPOSE_FILE),
            *arguments,
        ],
        cwd=REPOSITORY_ROOT,
        check=True,
    )


def _create_test_database(admin_url: URL) -> None:
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE {TEST_DATABASE_NAME}"))
    finally:
        engine.dispose()


def _drop_test_database(admin_url: URL) -> None:
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity "
                    "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                ),
                {"database_name": TEST_DATABASE_NAME},
            )
            connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE_NAME}"))
    finally:
        engine.dispose()


def _upgrade_test_database() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.set_main_option(
        "sqlalchemy.url",
        TEST_DATABASE_URL.render_as_string(hide_password=False),
    )
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    """Create a migrated, randomly named PostgreSQL database for this run."""

    compose_started = False
    database_created = False
    engine: Engine | None = None
    try:
        if START_LOCAL_POSTGRES:
            _run_test_compose("up", "--detach", "--wait")
            compose_started = True

        _create_test_database(ADMIN_DATABASE_URL)
        database_created = True
        _upgrade_test_database()
        engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        if database_created:
            _drop_test_database(ADMIN_DATABASE_URL)
        if compose_started:
            _run_test_compose("down", "--volumes", "--remove-orphans")


@pytest.fixture(scope="session")
def test_session_factory(test_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )


@pytest.fixture
def clean_database(test_engine: Engine) -> None:
    """Remove application data while preserving the Alembic revision row."""

    table_names = [
        table_name
        for table_name in inspect(test_engine).get_table_names()
        if table_name != "alembic_version"
    ]
    if not table_names:
        return

    preparer = test_engine.dialect.identifier_preparer
    quoted_tables = ", ".join(preparer.quote(table_name) for table_name in table_names)
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db_session(
    test_session_factory: sessionmaker[Session],
    clean_database: None,
) -> Generator[Session, None, None]:
    _ = clean_database
    with test_session_factory() as session:
        yield session


@pytest.fixture
def api_client(
    test_session_factory: sessionmaker[Session],
    clean_database: None,
) -> Generator[TestClient, None, None]:
    """Run API requests with all database dependencies bound to the test DB."""

    _ = clean_database
    from app.db.session import get_db
    from app.main import app

    def override_get_db() -> Generator[Session, None, None]:
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
