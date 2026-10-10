import json
from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Dependency Guardian API"
    VERSION: str = "1.1.0"
    API_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database configuration
    # Can be set directly via DATABASE_URL or assembled from POSTGRES_* variables
    DATABASE_URL: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: Optional[int] = 5432
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    # CORS origins
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    @model_validator(mode="after")
    def assemble_database_url(self) -> "Settings":
        if not self.DATABASE_URL:
            if self.POSTGRES_HOST and self.POSTGRES_USER and self.POSTGRES_DB:
                password_part = f":{self.POSTGRES_PASSWORD}" if self.POSTGRES_PASSWORD else ""
                port_part = f":{self.POSTGRES_PORT}" if self.POSTGRES_PORT else ""
                self.DATABASE_URL = (
                    f"postgresql+psycopg://{self.POSTGRES_USER}{password_part}"
                    f"@{self.POSTGRES_HOST}{port_part}/{self.POSTGRES_DB}"
                )
            else:
                self.DATABASE_URL = "sqlite:///./dependency_guardian.db"
        return self

    @property
    def masked_database_url(self) -> str:
        """Return DATABASE_URL with database password masked for safe logging."""
        if not self.DATABASE_URL:
            return ""
        try:
            return make_url(self.DATABASE_URL).render_as_string(hide_password=True)
        except Exception:
            return "***"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip().startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    def __repr__(self) -> str:
        return (
            f"Settings(PROJECT_NAME='{self.PROJECT_NAME}', "
            f"VERSION='{self.VERSION}', "
            f"ENVIRONMENT='{self.ENVIRONMENT}', "
            f"DATABASE_URL='{self.masked_database_url}')"
        )

    model_config = SettingsConfigDict(
        env_file=(_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

