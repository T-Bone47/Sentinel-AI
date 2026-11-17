"""
Application configuration, loaded from environment variables / .env.

Fails closed: ENVIRONMENT defaults to "production", and outside local
development the app refuses to start with the public demo secret, the demo
database credentials or debug on. A deployment that forgets to configure
itself therefore stops with an explanation instead of running insecurely.
For local work set ENVIRONMENT=development (the checked-in .env.example
does this).
"""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_KEY = "dev-only-secret-change-me"  # noqa: S105 - public placeholder, rejected outside local envs
DEMO_DB_CREDENTIALS = "sentinel:sentinel@"
LOCAL_ENVIRONMENTS = frozenset({"development", "test"})
MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Sentinel AI"
    app_version: str = "0.1.0-phase1"
    environment: str = "production"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_ai"
    database_url_sync: str = "postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel_ai"

    # Auth
    secret_key: str = DEV_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # CORS
    frontend_url: str | None = None

    @property
    def is_local(self) -> bool:
        """Only these exact names relax the checks. Anything else — including
        a typo or an unrecognised name — is treated as production."""
        return self.environment in LOCAL_ENVIRONMENTS

    @property
    def allowed_origins(self) -> list[str]:
        origins = (
            ["http://localhost:5173", "http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:5173"]
            if self.is_local
            else []
        )
        if self.frontend_url:
            origins.append(self.frontend_url)
        return origins

    @model_validator(mode="after")
    def _refuse_unsafe_configuration_outside_local(self) -> "Settings":
        if self.is_local:
            return self
        problems = []
        if self.secret_key == DEV_SECRET_KEY or len(self.secret_key) < MIN_SECRET_KEY_LENGTH:
            problems.append(
                f"SECRET_KEY must be a unique random value of at least {MIN_SECRET_KEY_LENGTH} characters"
            )
        if self.debug:
            problems.append("DEBUG must be off")
        if DEMO_DB_CREDENTIALS in self.database_url or DEMO_DB_CREDENTIALS in self.database_url_sync:
            problems.append("DATABASE_URL / DATABASE_URL_SYNC must not use the public demo credentials")
        if problems:
            raise ValueError(
                f"Refusing to start with ENVIRONMENT={self.environment!r}: "
                + "; ".join(problems)
                + ". For local development set ENVIRONMENT=development."
            )
        return self

    # Ingestion
    uploads_dir: str = "/mnt/user-data/uploads"

    # LLM (optional — Copilot falls back to deterministic responses when unset)
    llm_api_key: str | None = None
    llm_model: str = "gemini-flash-latest"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    llm_timeout: int = 15

    # NVIDIA NIM (preferred provider for the Copilot). Mirrors sentinel-ai-nvidia.env.
    nvidia_api_key: str | None = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "z-ai/glm-5.3-flash"
    nvidia_timeout_seconds: int = 90
    nvidia_max_tokens: int = 800
    nvidia_temperature: float = 0.2

    # Copilot LLM behaviour flags (from sentinel-ai-nvidia.env).
    copilot_llm_enabled: bool = False
    copilot_llm_provider: str = "nvidia"
    copilot_llm_fallback_enabled: bool = True

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
