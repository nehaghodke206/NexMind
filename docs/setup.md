
# Development Setup

Each component owner must document prerequisites, installation, run, and test commands
in that component folder README.

## Backend starter

From `services/backend/`:

```bash
python -m venv .venv
```

Activate the environment:

Linux/macOS:
```bash
source .venv/bin/activate
```

Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```

Install and run:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check: http://127.0.0.1:8000/health
API docs: http://127.0.0.1:8000/docs

