# Dependency Guardian — Backend Service

The shared backend service for Dependency Guardian. Coordinates project configurations, dependency baselines, automated scanner observations, detected behavior-change incidents, proposed repair patches, multi-stage validations, human approvals, and developer workspace application reports.

---

## 1. Architecture Overview

The backend is built with **FastAPI**, **SQLAlchemy 2.x**, **Pydantic v2**, and **Alembic**, following a modular layered MVC structure:

```
services/backend/
├── alembic/                # Database migrations
│   ├── env.py
│   └── versions/           # Migration revisions
├── app/
│   ├── core/               # Configuration, database engine & session, custom exceptions
│   │   ├── config.py
│   │   ├── database.py
│   │   └── exceptions.py
│   ├── models/             # SQLAlchemy ORM entities
│   │   ├── activity.py
│   │   ├── dependency.py
│   │   ├── incident.py
│   │   ├── observation.py
│   │   ├── project.py
│   │   ├── repair.py
│   │   └── user.py
│   ├── repositories/       # Data persistence & database queries
│   │   ├── activity_repo.py
│   │   ├── baseline_repo.py
│   │   ├── dependency_repo.py
│   │   ├── incident_repo.py
│   │   ├── observation_repo.py
│   │   ├── project_repo.py
│   │   ├── repair_repo.py
│   │   └── scan_repo.py
│   ├── schemas/            # Pydantic v2 DTOs (Requests & Responses)
│   ├── services/           # Business logic & workflow orchestration
│   ├── routers/            # HTTP controllers (endpoints & route handlers)
│   └── main.py             # FastAPI entrypoint, middleware, and route mounting
├── docs/                   # Implementation notes & contract review
│   └── contract-review.md
├── tests/                  # Pytest test suite with isolated in-memory DB
├── .env.example            # Environment configuration template
├── alembic.ini             # Alembic configuration file
├── pytest.ini              # Pytest configuration file
├── requirements.txt        # Production & testing dependencies
└── README.md               # Backend documentation
```

---

## 2. Product Invariants & Lifecycle Rules

1. **Immutable Baselines**:
   Baselines represent known-good contracts and are never overwritten. Every update creates a new incremented version.
2. **Audit Evidence Preservation**:
   Observations and schema diffs are persisted and linked to incidents for full auditability.
3. **Detection Deduplication**:
   Repeated detections for the same dependency behavior change are deduplicated using a stable `fingerprint`.
4. **Separation of Stages**:
   - Proposal $\neq$ Validation $\neq$ Approval $\neq$ Application $\neq$ Resolution.
   - A successful validation run moves a repair proposal to `ready_for_review`, but does not approve it.
   - A repair requires explicit human approval before moving to `approved`.
   - The backend never edits a developer's local files directly. The local VS Code extension or agent applies the patch and reports the result via `POST /repair-proposals/{repair_id}/applications`.
   - An incident is marked `resolved` only after patch application has succeeded.

---

## 3. Setup and Installation

### Prerequisites
- Python 3.11+ (Python 3.13 supported)
- Virtual environment (`venv`)

### 1. Create and Activate Virtual Environment
From `services/backend/`:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
For local PostgreSQL development or production deployments, configure `DATABASE_URL` in `.env`:
```env
DATABASE_URL=postgresql+psycopg://root:your_password@localhost:5432/hackwave
```
(A zero-config SQLite fallback `sqlite:///./dependency_guardian.db` is also available if running without PostgreSQL.)


---

## 4. Database Migrations

Apply existing migrations:
```bash
alembic upgrade head
```

To create a new migration after editing SQLAlchemy models:
```bash
alembic revision --autogenerate -m "describe_changes"
alembic upgrade head
```

To rollback a migration:
```bash
alembic downgrade -1
```

---

## 5. Running the Application

Start the development server with Uvicorn:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Health check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) or [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 6. Running Tests

Tests run against an isolated in-memory SQLite database configured with foreign key constraints enabled.

Execute the test suite:
```bash
pytest -v
```

Execute a specific test module:
```bash
pytest tests/test_first_vertical_slice.py -v
pytest tests/test_repairs_lifecycle.py -v
pytest tests/test_invalid_transitions_and_errors.py -v
pytest tests/test_contract_examples.py -v
```
