from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="deployment-metrics-service")
    app_env: Literal["development", "staging", "production"] = Field(default="development")
    app_debug: bool = Field(default=False)
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    database_url: str = Field(default="sqlite:///./local_dev.db")
    db_host: str | None = Field(default=None)
    db_port: int | None = Field(default=None)
    db_name: str | None = Field(default=None)
    db_user: str | None = Field(default=None)
    db_password: str | None = Field(default=None)
    db_sslmode: str = Field(default="require")
    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_prefix="",
    )

    @property
    def effective_database_url(self) -> str:
        if self.db_host and self.db_user and self.db_name:
            password = self.db_password or ""
            return (
                f"postgresql://{self.db_user}:{password}@{self.db_host}:{self.db_port or 5432}/"
                f"{self.db_name}?sslmode={self.db_sslmode}"
            )
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
