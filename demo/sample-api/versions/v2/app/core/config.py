"""Application settings and configuration for sample API (v2)."""
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Dependency Guardian Sample API"
    app_version: str = "2.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False


settings = Settings()
