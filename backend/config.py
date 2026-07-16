"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings needed to call the Gemini Developer API."""

    gemini_api_key: SecretStr
    gemini_model: str = "gemini-3.5-flash"
    gemini_thinking_level: str = "low"
    gemini_request_timeout_ms: int = 180_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("gemini_model")
    @classmethod
    def model_must_be_gemini(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("GEMINI_MODEL must not be empty")
        if not value.lower().startswith("gemini-"):
            raise ValueError(
                "GEMINI_MODEL must be a Gemini model ID beginning with 'gemini-'"
            )
        return value

    @field_validator("gemini_thinking_level")
    @classmethod
    def thinking_level_must_be_supported(cls, value: str) -> str:
        value = value.strip().lower()
        supported = {"minimal", "low", "medium", "high"}
        if value not in supported:
            raise ValueError(
                "GEMINI_THINKING_LEVEL must be minimal, low, medium or high"
            )
        return value

    @field_validator("gemini_request_timeout_ms")
    @classmethod
    def request_timeout_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("GEMINI_REQUEST_TIMEOUT_MS must be greater than zero")
        return value


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    """Load settings and replace Pydantic's error with a useful startup message."""

    try:
        return Settings(_env_file=env_file)  # type: ignore[call-arg]
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']).upper()}: {error['msg']}"
            for error in exc.errors()
        )
        raise RuntimeError(
            f"Backend configuration is invalid: {details}. Check .env and use "
            "GEMINI_API_KEY plus optional GEMINI_MODEL, GEMINI_THINKING_LEVEL "
            "and GEMINI_REQUEST_TIMEOUT_MS overrides."
        ) from None


@lru_cache
def get_settings() -> Settings:
    """Load settings once for the running application."""

    return load_settings()
