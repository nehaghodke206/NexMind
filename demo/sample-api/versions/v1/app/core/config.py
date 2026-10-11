"""Application settings and configuration for sample API (v1)."""
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Dependency Guardian Sample API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False


settings = Settings()

