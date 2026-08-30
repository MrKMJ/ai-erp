from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET = "change-me-in-production-please"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI ERP"
    app_env: str = "development"  # development | staging | production

    database_url: str = "sqlite:///./ai_erp.db"
    # Auto-create tables from ORM metadata. Keep on for dev/SQLite; in production run
    # Alembic migrations instead and leave this off.
    auto_create_tables: bool = True
    db_pool_size: int = 5
    db_max_overflow: int = 10

    secret_key: str = INSECURE_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,"
        "http://localhost:5173"
    )

    # Rate limiting (per client IP, sliding window)
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 240
    auth_rate_limit_per_minute: int = 20

    log_level: str = "INFO"
    log_json: bool = False  # set true in production for structured logs

    # AI gateway
    ai_provider: str = "rule"  # "rule" | "anthropic"
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-5"
    ai_max_tokens: int = 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod")

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> "Settings":
        if self.is_production:
            problems = []
            if self.secret_key == INSECURE_SECRET or len(self.secret_key) < 32:
                problems.append("SECRET_KEY must be set to a random value of at least 32 chars")
            if self.is_sqlite:
                problems.append("DATABASE_URL must point at PostgreSQL, not SQLite")
            if self.auto_create_tables:
                problems.append("AUTO_CREATE_TABLES must be false (use Alembic migrations)")
            if self.ai_provider == "anthropic" and not self.anthropic_api_key:
                problems.append("ANTHROPIC_API_KEY is required when AI_PROVIDER=anthropic")
            if problems:
                raise ValueError(
                    "Invalid production configuration:\n  - " + "\n  - ".join(problems)
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
