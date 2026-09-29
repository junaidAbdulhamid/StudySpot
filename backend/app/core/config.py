from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: SecretStr
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=list)
    supabase_url: str = ""
    supabase_anon_key: SecretStr = SecretStr("")
    redis_url: str = "redis://127.0.0.1:56379/0"
    checkin_duration_hours: int = Field(default=4, ge=1, le=12)
    checkin_radius_meters: int = Field(default=200, ge=50, le=1000)
    report_cooldown_minutes: int = Field(default=10, ge=1, le=120)
    validation_cooldown_minutes: int = Field(default=10, ge=1, le=120)
    report_half_life_minutes: int = Field(default=25, ge=1, le=180)
    occupancy_max_age_minutes: int = Field(default=90, ge=30, le=240)

    @field_validator("supabase_url")
    @classmethod
    def auth_url(cls, value: str) -> str:
        secure = value.startswith("https://")
        loopback = value.startswith("http://127.0.0.1") or value.startswith("http://localhost")
        if value and (not (secure or loopback) or "@" in value or "?" in value or "#" in value):
            raise ValueError("SUPABASE_URL must be an HTTPS project URL")
        return value.rstrip("/")

    dev_user_enabled: bool = False
    dev_user_id: str = "dev-studyspot"

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use the postgresql+psycopg driver")
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def prefix_valid(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("API prefix must start with / and have no trailing slash")
        return value

    @model_validator(mode="after")
    def secure_defaults(self):
        if "*" in self.cors_origins:
            raise ValueError("Configure explicit CORS origins")
        if self.app_env == "production" and (self.dev_user_enabled or self.debug):
            raise ValueError("Development identity and debug must be disabled in production")
        if (
            self.app_env == "production"
            and self.supabase_url
            and not self.supabase_url.startswith("https://")
        ):
            raise ValueError("Production Supabase authentication requires HTTPS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
