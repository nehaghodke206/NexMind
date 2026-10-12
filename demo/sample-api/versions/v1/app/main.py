"""Version 1 entry point forwarding to the minimal localhost integration demo app."""
from demo.sample_api.main import app, create_app

__all__ = ["app", "create_app"]
