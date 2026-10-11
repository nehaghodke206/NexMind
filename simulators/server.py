"""Simulated external REST services for Dependency Guardian demo.
Provides:
- Users API on port 8001
- Payments API on port 8002
- Search API on port 8003
- Notification Tool on port 8004
Includes mode switching (v1/v2) and reset endpoints.
"""

import asyncio
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Global state for versioning
modes: Dict[str, str] = {
    "users": "v1",
    "payments": "v1",
    "search": "v1",
    "notification": "v1",
}


def create_users_app() -> FastAPI:
    app = FastAPI(title="Simulated Users API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/users/{user_id}")
    async def get_user(user_id: str):
        mode = modes.get("users", "v1")
        if mode == "v1":
            return {
                "id": user_id,
                "name": "Alice",
                "email": "alice@example.com",
            }
        else:
            return {
                "id": user_id,
                "display_name": "Alice",
                "email": "alice@example.com",
            }

    @app.post("/mode")
    async def set_mode(request: Request):
        data = await request.json()
        version = data.get("version", "v1")
        modes["users"] = version
        return {"service": "users", "mode": version}

    @app.post("/reset")
    async def reset():
        modes["users"] = "v1"
        return {"service": "users", "mode": "v1"}

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "users", "mode": modes.get("users", "v1")}

    return app


def create_payments_app() -> FastAPI:
    app = FastAPI(title="Simulated Payments API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/payments/{payment_id}")
    async def get_payment(payment_id: str):
        mode = modes.get("payments", "v1")
        if mode == "v1":
            return {
                "id": payment_id,
                "status": "paid",
                "amount": 100,
            }
        else:
            # Semantic change: status changed to "processing_escrow" (not recognized as confirmed payment)
            return {
                "id": payment_id,
                "status": "processing_escrow",
                "amount": 100,
            }

    @app.post("/mode")
    async def set_mode(request: Request):
        data = await request.json()
        version = data.get("version", "v1")
        modes["payments"] = version
        return {"service": "payments", "mode": version}

    @app.post("/reset")
    async def reset():
        modes["payments"] = "v1"
        return {"service": "payments", "mode": "v1"}

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "payments", "mode": modes.get("payments", "v1")}

    return app


def create_search_app() -> FastAPI:
    app = FastAPI(title="Simulated Search API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/search")
    async def search(page: int = 1, cursor: str = None):
        mode = modes.get("search", "v1")
        if mode == "v1":
            return {
                "items": [{"id": "u_123"}],
                "page": page,
                "next_page": page + 1,
            }
        else:
            # Contract change: cursor-based pagination
            next_cur = f"cursor_demo_{page + 1}" if cursor is None else "cursor_demo_end"
            return {
                "results": [{"id": "u_123"}],
                "next_cursor": next_cur,
            }

    @app.post("/mode")
    async def set_mode(request: Request):
        data = await request.json()
        version = data.get("version", "v1")
        modes["search"] = version
        return {"service": "search", "mode": version}

    @app.post("/reset")
    async def reset():
        modes["search"] = "v1"
        return {"service": "search", "mode": "v1"}

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "search", "mode": modes.get("search", "v1")}

    return app


def create_notification_app() -> FastAPI:
    app = FastAPI(title="Simulated Notification Tool")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/status")
    async def get_status():
        return {
            "tool": "notification",
            "status": "ready",
            "version": "1.0",
        }

    @app.post("/notify")
    async def send_notify(request: Request):
        body = await request.json()
        return {
            "delivered": True,
            "recipient": body.get("recipient", "admin"),
            "message": body.get("message", "Alert"),
        }

    @app.post("/reset")
    async def reset():
        modes["notification"] = "v1"
        return {"service": "notification", "mode": "v1"}

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "notification", "mode": "v1"}

    return app


def reset_all_modes():
    modes["users"] = "v1"
    modes["payments"] = "v1"
    modes["search"] = "v1"
    modes["notification"] = "v1"


async def run_all_simulators():
    config_users = uvicorn.Config(create_users_app(), host="127.0.0.1", port=8001, log_level="warning")
    config_payments = uvicorn.Config(create_payments_app(), host="127.0.0.1", port=8002, log_level="warning")
    config_search = uvicorn.Config(create_search_app(), host="127.0.0.1", port=8003, log_level="warning")
    config_notification = uvicorn.Config(create_notification_app(), host="127.0.0.1", port=8004, log_level="warning")

    server_users = uvicorn.Server(config_users)
    server_payments = uvicorn.Server(config_payments)
    server_search = uvicorn.Server(config_search)
    server_notification = uvicorn.Server(config_notification)

    await asyncio.gather(
        server_users.serve(),
        server_payments.serve(),
        server_search.serve(),
        server_notification.serve(),
    )


if __name__ == "__main__":
    print("Starting simulated services on ports 8001, 8002, 8003, 8004...")
    asyncio.run(run_all_simulators())
