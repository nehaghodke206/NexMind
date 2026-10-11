"""Unified server runner booting Dependency Guardian Backend (8765)
and Simulated Services (8001, 8002, 8003, 8004) concurrently on loopback.
"""

import asyncio
import os
import sys
import uvicorn

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.main import app as backend_app
from simulators.server import (
    create_users_app,
    create_payments_app,
    create_search_app,
    create_notification_app,
)


async def main():
    print("=" * 65)
    print("  [DEPENDENCY GUARDIAN UNIFIED SERVER STACK]")
    print("=" * 65)
    print("  Backend API:         http://127.0.0.1:8765")
    print("  Users API:           http://127.0.0.1:8001")
    print("  Payments API:        http://127.0.0.1:8002")
    print("  Search API:          http://127.0.0.1:8003")
    print("  Notification Tool:   http://127.0.0.1:8004")
    print("=" * 65)
    import socket
    ports_to_check = [8765, 8001, 8002, 8003, 8004]
    busy_ports = []
    for p in ports_to_check:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) == 0:
                busy_ports.append(p)

    if busy_ports:
        print(f"\n[!] Notice: Port(s) {busy_ports} are already in use.")
        try:
            import httpx
            r = httpx.get("http://127.0.0.1:8765/api/health", timeout=1.0)
            if r.status_code == 200:
                print("  ✓ Dependency Guardian is ALREADY active and serving at http://127.0.0.1:8765!")
                print("  You can directly use the VS Code extension or run: python scripts/test_e2e.py")
                return
        except Exception:
            pass
        print("  Please terminate any existing process using those ports or check Task Manager.\n")
        return

    config_backend = uvicorn.Config(backend_app, host="127.0.0.1", port=8765, log_level="warning")
    config_users = uvicorn.Config(create_users_app(), host="127.0.0.1", port=8001, log_level="warning")
    config_payments = uvicorn.Config(create_payments_app(), host="127.0.0.1", port=8002, log_level="warning")
    config_search = uvicorn.Config(create_search_app(), host="127.0.0.1", port=8003, log_level="warning")
    config_notif = uvicorn.Config(create_notification_app(), host="127.0.0.1", port=8004, log_level="warning")

    server_backend = uvicorn.Server(config_backend)
    server_users = uvicorn.Server(config_users)
    server_payments = uvicorn.Server(config_payments)
    server_search = uvicorn.Server(config_search)
    server_notif = uvicorn.Server(config_notif)

    await asyncio.gather(
        server_backend.serve(),
        server_users.serve(),
        server_payments.serve(),
        server_search.serve(),
        server_notif.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
