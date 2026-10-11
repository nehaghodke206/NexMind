#!/usr/bin/env python3
"""
Generate genuine OpenAPI 3.1 contract specifications from Demo v1 and v2 FastAPI applications.
"""
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from demo.sample_api.versions.v1.app.main import create_app as create_app_v1
from demo.sample_api.versions.v2.app.main import create_app as create_app_v2


def generate_contracts():
    contracts_dir = Path(__file__).resolve().parents[1] / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate v1 contract
    app_v1 = create_app_v1()
    spec_v1 = app_v1.openapi()
    v1_path = contracts_dir / "openapi-v1.json"
    with open(v1_path, "w", encoding="utf-8") as f:
        json.dump(spec_v1, f, indent=2)
    print(f"[+] Successfully exported v1 OpenAPI contract -> {v1_path} ({len(spec_v1.get('paths', {}))} paths)")

    # 2. Generate v2 contract
    app_v2 = create_app_v2()
    spec_v2 = app_v2.openapi()
    v2_path = contracts_dir / "openapi-v2.json"
    with open(v2_path, "w", encoding="utf-8") as f:
        json.dump(spec_v2, f, indent=2)
    print(f"[+] Successfully exported v2 OpenAPI contract -> {v2_path} ({len(spec_v2.get('paths', {}))} paths)")


if __name__ == "__main__":
    generate_contracts()
