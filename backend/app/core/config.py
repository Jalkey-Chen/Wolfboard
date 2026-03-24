"""Centralized application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    A dedicated settings object keeps deployment-specific concerns out of the
    rest of the codebase and provides a single place to evolve configuration as
    more services are introduced in later milestones.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = "Wolfboard API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+psycopg://wolfboard:wolfboard@db:5432/wolfboard",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(default="change-this-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(
        default=120,
        alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="BACKEND_CORS_ORIGINS",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        """Allow CORS origins to be passed as a comma-separated string.

        Docker Compose and many deployment platforms expose list-like settings
        as strings, so this parser keeps the environment contract simple while
        still exposing a strongly typed list inside the application.
        """

        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Memoize settings so repeated imports do not rebuild the settings object."""

    return Settings()


settings = get_settings()
