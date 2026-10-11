# Dependency Guardian — Repository Dependency Report

**Scanned Repository Path:** `/home/last-hope/Dnyaneshwar/HackWave/agents/detection/tests/fixtures/fixture_repo`  
**Scan Timestamp:** `2026-10-11T07:54:40.667589+00:00`  
**Scanner Engine:** `Dependency Guardian Repository Intelligence v0.2.0`  

## 1. Executive Summary

| Metric | Count | Note |
|---|---|---|
| **Total Declared Dependencies** | 9 | Discovered across manifests and lockfiles |
| **Active Dependencies in Code** | 8 | Imported or required in source code |
| **Declared but Unused Packages** | 1 | Potential cleanup candidates |
| **Internal Modules** | 4 | Local architectural modules |
| **External Integrations** | 4 | Databases, queues, HTTP clients, SDKs |

---

## 2. External Dependencies Inventory

All discovered third-party libraries, version constraints, resolved lockfile versions, purposes, and usage sites:

| Package Name | Ecosystem | Declared Constraint | Resolved Version | Used in Code | Purpose | Documentation URL | Vulnerabilities |
|---|---|---|---|:---:|---|---|---|
| **axios** | npm | `^1.6.0` | `1.6.2` | ✅ Yes | Promise-based HTTP client for the browser and Node.js | [Docs](https://axios-http.com/) | None verified |
| **express** | npm | `^4.18.2` | `4.18.2` | ✅ Yes | Fast, unopinionated, minimalist web framework for Node.js | [Docs](https://expressjs.com/) | None verified |
| **fastapi** | python | `>=0.100.0` | `0.104.1` | ✅ Yes | High-performance asynchronous web framework for building APIs | [Docs](https://fastapi.tiangolo.com/) | None verified |
| **httpx** | python | `>=0.24.0` | `0.25.1` | ✅ Yes | Next-generation HTTP client with async support and HTTP/2 | [Docs](https://www.python-httpx.org/) | None verified |
| **psycopg2-binary** | python | `>=2.9.0` | `2.9.9` | ✅ Yes | Standalone binary package for PostgreSQL database adapter | [Docs](https://www.psycopg.org/docs/) | None verified |
| **pydantic** | python | `>=2.0.0` | `2.5.2` | ✅ Yes | Data validation and settings management using Python type annotations | [Docs](https://docs.pydantic.dev/) | None verified |
| **redis** | python | `>=5.0.0` | `5.0.1` | ✅ Yes | Python interface to Redis in-memory data structure store | [Docs](https://redis-py.readthedocs.io/) | None verified |
| **stripe** | python | `>=5.0.0` | `5.4.0` | ✅ Yes | Official Stripe Python API library for payment processing | [Docs](https://docs.stripe.com/api) | None verified |
| **unused-lib** | python | `>=1.0.0` | `1.2.0` | ⚠️ No | Python library: unused-lib *(Inferred)* | [Docs](https://pypi.org/project/unused-lib/) | None verified |

### Dependency Usage Sites (Top Imported Packages)

#### `fastapi` (1 import sites)
- `app/main.py:7`: `from fastapi import Depends, FastAPI, HTTPException`

#### `pydantic` (1 import sites)
- `app/main.py:10`: `from pydantic import BaseModel, Field`

#### `httpx` (1 import sites)
- `app/main.py:8`: `import httpx`

#### `psycopg2-binary` (1 import sites)
- `app/main.py:9`: `import psycopg2`

#### `redis` (1 import sites)
- `app/main.py:11`: `import redis`

#### `stripe` (1 import sites)
- `app/main.py:12`: `import stripe`

#### `express` (1 import sites)
- `web/server.js:4`: `const express = require('express');`

#### `axios` (1 import sites)
- `web/server.js:5`: `const axios = require('axios');`

---

## 3. Declared but Unused Dependencies

> [!NOTE]
> The following packages are declared in dependency manifests but were not found imported or required anywhere in the scanned source code. Consider removing them to reduce attack surface and build times.

- ⚠️ **unused-lib** — Declared in manifest but has 0 import references

---

## 4. Internal Module Architecture

Local packages and modules detected within the repository:

- `app`
- `main`
- `test_api`
- `tests`

---

## 5. External Services and Integrations

> [!IMPORTANT]
> All external service interfaces, outbound HTTP calls, database clients, SDKs, and message brokers are inventoried below.
> **Secret Safety Verification:** All credential strings, tokens, and passwords have been strictly sanitized and redacted.

| Integration Type | Service Name | Target / Host | File Location | Detected Operations | Redacted Secrets |
|---|---|---|---|---|:---:|
| **DATABASE** | PostgreSQL (psycopg2) | *Configuration-driven* | `app/main.py:63` | `connect, query` | 0 (Safe) |
| **HTTP_SERVICE** | Stripe API | `https://api.stripe.com/v1/customers` | `app/main.py:69` | `POST` | 0 (Safe) |
| **CACHE** | Redis Client | *Configuration-driven* | `app/main.py:76` | `connect, publish, query` | 0 (Safe) |
| **DATABASE** | PostgreSQL (psycopg2) | *Configuration-driven* | `app/main.py:107` | `connect, query` | 0 (Safe) |

---

## 6. Scanner Limitations and Skipped Files

✅ All discoverable source files and manifests were successfully parsed.
