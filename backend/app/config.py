import sys
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_builder"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/agentic_builder"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440

    # AI
    ai_provider: str = "openai"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o"

    # Environment: local | dev | staging | production
    environment: str = "local"
    debug: bool = True

    model_config = {"env_file": "../.env", "extra": "ignore"}

    @property
    def is_local(self) -> bool:
        return self.environment in ("local", "dev")

    def validate_for_deployment(self):
        errors = []

        if not self.is_local:
            if self.jwt_secret == "change-me-in-production":
                errors.append("JWT_SECRET must be changed for non-local environments")
            if len(self.jwt_secret) < 32:
                errors.append("JWT_SECRET must be at least 32 characters")
            if self.debug:
                print("[WARN] DEBUG=true in non-local environment. Forcing off.")
                object.__setattr__(self, "debug", False)

        if self.environment == "production":
            if "postgres:postgres" in self.database_url:
                errors.append("DATABASE_URL must not use default credentials in production")

        if errors:
            for e in errors:
                print(f"[FATAL] {e}")
            sys.exit(1)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate_for_deployment()
    return s
