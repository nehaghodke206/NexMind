"""Application settings and configuration for sample API (v1)."""
import os
from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Dependency Guardian Sample API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False
    guardian_backend_url: str = os.getenv("GUARDIAN_BACKEND_URL", "http://127.0.0.1:8000")
    guardian_backend_token: Optional[str] = os.getenv("GUARDIAN_BACKEND_TOKEN", None)
    backend_connect_timeout: float = float(os.getenv("BACKEND_CONNECT_TIMEOUT", "2.0"))
    backend_read_timeout: float = float(os.getenv("BACKEND_READ_TIMEOUT", "5.0"))


settings = Settings()

