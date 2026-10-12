# Dependency Guardian — Repository Dependency Report

**Scanned Repository Path:** `/home/last-hope/Dnyaneshwar/HackWave/services/backend`  
**Scan Timestamp:** `2026-10-11T20:50:57.743330+00:00`  
**Scanner Engine:** `Dependency Guardian Repository Intelligence v0.2.0`  

## 1. Executive Summary

| Metric | Count | Note |
|---|---|---|
| **Total Declared Dependencies** | 10 | Discovered across manifests and lockfiles |
| **Active Dependencies in Code** | 6 | Imported or required in source code |
| **Declared but Unused Packages** | 4 | Potential cleanup candidates |
| **Internal Modules** | 55 | Local architectural modules |
| **External Integrations** | 0 | Databases, queues, HTTP clients, SDKs |

---

## 2. External Dependencies Inventory

All discovered third-party libraries, version constraints, resolved lockfile versions, purposes, and usage sites:

| Package Name | Ecosystem | Declared Constraint | Resolved Version | Used in Code | Purpose | Documentation URL | Vulnerabilities |
|---|---|---|---|:---:|---|---|---|
| **alembic** | python | `>=1.13.0` | *Unresolved* | ✅ Yes | Database migration tool for SQLAlchemy | [Docs](https://alembic.sqlalchemy.org/) | None verified |
| **fastapi** | python | `>=0.115.0` | *Unresolved* | ✅ Yes | High-performance asynchronous web framework for building APIs | [Docs](https://fastapi.tiangolo.com/) | None verified |
| **pydantic** | python | `>=2.8.0` | *Unresolved* | ✅ Yes | Data validation and settings management using Python type annotations | [Docs](https://docs.pydantic.dev/) | None verified |
| **pydantic-settings** | python | `>=2.4.0` | *Unresolved* | ✅ Yes | Environment and settings management extension for Pydantic | [Docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | None verified |
| **pytest** | python | `>=8.0.0` | *Unresolved* | ✅ Yes | Testing framework supporting unit, functional, and integration tests | [Docs](https://docs.pytest.org/) | None verified |
| **sqlalchemy** | python | `>=2.0.0` | *Unresolved* | ✅ Yes | SQL toolkit and Object Relational Mapper (ORM) for Python | [Docs](https://www.sqlalchemy.org/) | None verified |
| **httpx** | python | `>=0.27.0` | *Unresolved* | ⚠️ No | Next-generation HTTP client with async support and HTTP/2 | [Docs](https://www.python-httpx.org/) | None verified |
| **psycopg** | python | `[binary]>=3.2.0` | *Unresolved* | ⚠️ No | Python library: psycopg *(Inferred)* | [Docs](https://pypi.org/project/psycopg/) | None verified |
| **psycopg2-binary** | python | `>=2.9.9` | *Unresolved* | ⚠️ No | Standalone binary package for PostgreSQL database adapter | [Docs](https://www.psycopg.org/docs/) | None verified |
| **uvicorn** | python | `[standard]>=0.30.0` | *Unresolved* | ⚠️ No | Lightning-fast ASGI web server implementation for Python | [Docs](https://www.uvicorn.org/) | None verified |

### Dependency Usage Sites (Top Imported Packages)

#### `sqlalchemy` (54 import sites)
- `tests/conftest.py:10`: `from sqlalchemy import create_engine, event`
- `tests/conftest.py:11`: `from sqlalchemy.orm import sessionmaker`
- `tests/conftest.py:12`: `from sqlalchemy.pool import StaticPool`
- `app/routers/projects.py:3`: `from sqlalchemy.orm import Session`
- `app/routers/incidents.py:3`: `from sqlalchemy.orm import Session`
- *...and 49 more locations.*

#### `pydantic` (14 import sites)
- `app/schemas/repair.py:3`: `from pydantic import BaseModel, ConfigDict, Field`
- `app/schemas/dashboard.py:3`: `from pydantic import BaseModel, ConfigDict`
- `app/schemas/validation.py:3`: `from pydantic import BaseModel, ConfigDict, Field`
- `app/schemas/incident.py:3`: `from pydantic import BaseModel, ConfigDict, Field`
- `app/schemas/application.py:3`: `from pydantic import BaseModel, ConfigDict, Field`
- *...and 9 more locations.*

#### `fastapi` (13 import sites)
- `tests/conftest.py:13`: `from fastapi.testclient import TestClient`
- `app/main.py:1`: `from fastapi import FastAPI, Request, status`
- `app/main.py:2`: `from fastapi.exceptions import RequestValidationError`
- `app/main.py:3`: `from fastapi.middleware.cors import CORSMiddleware`
- `app/main.py:4`: `from fastapi.responses import JSONResponse`
- *...and 8 more locations.*

#### `alembic` (3 import sites)
- `alembic/env.py:6`: `from alembic import context`
- `alembic/versions/8c3d7f1b2e4a_baselines_scans_incidents.py:10`: `from alembic import op`
- `alembic/versions/04b6dd555033_initial_schema.py:10`: `from alembic import op`

#### `pydantic-settings` (1 import sites)
- `app/core/config.py:5`: `from pydantic_settings import BaseSettings, SettingsConfigDict`

#### `pytest` (1 import sites)
- `tests/conftest.py:3`: `import pytest`

---

## 3. Declared but Unused Dependencies

> [!NOTE]
> The following packages are declared in dependency manifests but were not found imported or required anywhere in the scanned source code. Consider removing them to reduce attack surface and build times.

- ⚠️ **httpx** — Declared in manifest but has 0 import references
- ⚠️ **psycopg** — Declared in manifest but has 0 import references
- ⚠️ **psycopg2-binary** — Declared in manifest but has 0 import references
- ⚠️ **uvicorn** — Declared in manifest but has 0 import references

---

## 4. Internal Module Architecture

Local packages and modules detected within the repository:

- `04b6dd555033_initial_schema`
- `8c3d7f1b2e4a_baselines_scans_incidents`
- `activity`
- `activity_repo`
- `activity_service`
- `alembic`
- `app`
- `application`
- `approval`
- `base`
- `baseline`
- `baseline_repo`
- `baseline_service`
- `baselines`
- `common`
- `config`
- `conftest`
- `dashboard`
- `database`
- `dependencies`
- `dependency`
- `dependency_repo`
- `dependency_service`
- `env`
- `exceptions`
- `health`
- `incident`
- `incident_repo`
- `incident_service`
- `incidents`
- *...and 25 more internal modules.*

---

## 5. External Services and Integrations

> [!IMPORTANT]
> All external service interfaces, outbound HTTP calls, database clients, SDKs, and message brokers are inventoried below.
> **Secret Safety Verification:** All credential strings, tokens, and passwords have been strictly sanitized and redacted.

| Integration Type | Service Name | Target / Host | File Location | Detected Operations | Redacted Secrets |
|---|---|---|---|---|:---:|
| *None* | No external integrations detected | - | - | - | 0 |

---

## 6. Scanner Limitations and Skipped Files

✅ All discoverable source files and manifests were successfully parsed.
