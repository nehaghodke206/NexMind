# Dependency Guardian — Repository Dependency Report

**Scanned Repository Path:** `/home/last-hope/Dnyaneshwar/HackWave/demo-app`  
**Scan Timestamp:** `2026-10-11T19:20:14.168355+00:00`  
**Scanner Engine:** `Dependency Guardian Repository Intelligence v0.2.0`  

## 1. Executive Summary

| Metric | Count | Note |
|---|---|---|
| **Total Declared Dependencies** | 0 | Discovered across manifests and lockfiles |
| **Active Dependencies in Code** | 0 | Imported or required in source code |
| **Declared but Unused Packages** | 0 | Potential cleanup candidates |
| **Internal Modules** | 8 | Local architectural modules |
| **External Integrations** | 3 | Databases, queues, HTTP clients, SDKs |

---

## 2. External Dependencies Inventory

All discovered third-party libraries, version constraints, resolved lockfile versions, purposes, and usage sites:

| Package Name | Ecosystem | Declared Constraint | Resolved Version | Used in Code | Purpose | Documentation URL | Vulnerabilities |
|---|---|---|---|:---:|---|---|---|

### Dependency Usage Sites (Top Imported Packages)

---

## 3. Declared but Unused Dependencies

> [!NOTE]
> The following packages are declared in dependency manifests but were not found imported or required anywhere in the scanned source code. Consider removing them to reduce attack surface and build times.

✅ All declared dependencies have active import references in the codebase.

---

## 4. Internal Module Architecture

Local packages and modules detected within the repository:

- `payment_service`
- `search_service`
- `src`
- `test_payments`
- `test_search`
- `test_user_profile`
- `tests`
- `user_service`

---

## 5. External Services and Integrations

> [!IMPORTANT]
> All external service interfaces, outbound HTTP calls, database clients, SDKs, and message brokers are inventoried below.
> **Secret Safety Verification:** All credential strings, tokens, and passwords have been strictly sanitized and redacted.

| Integration Type | Service Name | Target / Host | File Location | Detected Operations | Redacted Secrets |
|---|---|---|---|---|:---:|
| **HTTP_SERVICE** | External HTTP Service | `{base_url}/users/{user_id}` | `src/services/user_service.py:8` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External HTTP Service | `{base_url}/payments/{payment_id}` | `src/services/payment_service.py:8` | `GET` | 0 (Safe) |
| **HTTP_SERVICE** | External HTTP Service | `{base_url}/search` | `src/services/search_service.py:8` | `GET` | 0 (Safe) |

---

## 6. Scanner Limitations and Skipped Files

✅ All discoverable source files and manifests were successfully parsed.
