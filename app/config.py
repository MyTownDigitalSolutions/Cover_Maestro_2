from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    ENV: str = "local"
    DATABASE_URL: str
    MIGRATION_DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    AUTH_REQUIRED: bool = True
    SUPABASE_JWT_AUDIENCE: str = "authenticated"
    SUPABASE_JWT_ISSUER: str | None = None
    SUPABASE_OWNER_EMAIL: str | None = Field(default=None, description="Optional allowlist for single owner account")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
