"""
External Dependency and Integration Scanner.
Discovers dependency manifests, lockfiles, import sites, external HTTP calls,
SDKs, database clients, message brokers, and safe configuration references.
"""
import ast
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from .models import (
    DependencyDoc,
    ExternalIntegrationDoc,
    ImportLocation,
    SkippedFileDoc,
)

logger = logging.getLogger("dependency_guardian.repo_intelligence.dependency_scanner")

# Curated catalog of package purposes and official documentation URLs
PACKAGE_CATALOG: Dict[str, Dict[str, str]] = {
    # Python
    "fastapi": {
        "purpose": "High-performance asynchronous web framework for building APIs",
        "url": "https://fastapi.tiangolo.com/",
    },
    "pydantic": {
        "purpose": "Data validation and settings management using Python type annotations",
        "url": "https://docs.pydantic.dev/",
    },
    "pydantic-settings": {
        "purpose": "Environment and settings management extension for Pydantic",
        "url": "https://docs.pydantic.dev/latest/concepts/pydantic_settings/",
    },
    "httpx": {
        "purpose": "Next-generation HTTP client with async support and HTTP/2",
        "url": "https://www.python-httpx.org/",
    },
    "requests": {
        "purpose": "Synchronous HTTP library for Python",
        "url": "https://requests.readthedocs.io/",
    },
    "psycopg2": {
        "purpose": "PostgreSQL database adapter for Python",
        "url": "https://www.psycopg.org/docs/",
    },
    "psycopg2-binary": {
        "purpose": "Standalone binary package for PostgreSQL database adapter",
        "url": "https://www.psycopg.org/docs/",
    },
    "asyncpg": {
        "purpose": "High-performance asynchronous PostgreSQL client library",
        "url": "https://magicstack.github.io/asyncpg/",
    },
    "sqlalchemy": {
        "purpose": "SQL toolkit and Object Relational Mapper (ORM) for Python",
        "url": "https://www.sqlalchemy.org/",
    },
    "alembic": {
        "purpose": "Database migration tool for SQLAlchemy",
        "url": "https://alembic.sqlalchemy.org/",
    },
    "redis": {
        "purpose": "Python interface to Redis in-memory data structure store",
        "url": "https://redis-py.readthedocs.io/",
    },
    "celery": {
        "purpose": "Distributed task queue and asynchronous job framework",
        "url": "https://docs.celeryq.dev/",
    },
    "pika": {
        "purpose": "Pure-Python implementation of the AMQP 0-9-1 protocol (RabbitMQ)",
        "url": "https://pika.readthedocs.io/",
    },
    "stripe": {
        "purpose": "Official Stripe Python API library for payment processing",
        "url": "https://docs.stripe.com/api",
    },
    "boto3": {
        "purpose": "AWS SDK for Python to interact with Amazon Web Services",
        "url": "https://boto3.amazonaws.com/v1/documentation/api/latest/index.html",
    },
    "flask": {
        "purpose": "Lightweight WSGI web application framework for Python",
        "url": "https://flask.palletsprojects.com/",
    },
    "django": {
        "purpose": "High-level Python web framework encouraging clean design",
        "url": "https://www.djangoproject.com/",
    },
    "djangorestframework": {
        "purpose": "Powerful and flexible toolkit for building Web APIs in Django",
        "url": "https://www.django-rest-framework.org/",
    },
    "pytest": {
        "purpose": "Testing framework supporting unit, functional, and integration tests",
        "url": "https://docs.pytest.org/",
    },
    "pyyaml": {
        "purpose": "YAML parser and emitter for Python",
        "url": "https://pyyaml.org/",
    },
    "uvicorn": {
        "purpose": "Lightning-fast ASGI web server implementation for Python",
        "url": "https://www.uvicorn.org/",
    },
    "python-dotenv": {
        "purpose": "Reads key-value pairs from .env files and sets them as environment variables",
        "url": "https://github.com/theskumar/python-dotenv",
    },
    "openai": {
        "purpose": "Official Python client library for OpenAI APIs",
        "url": "https://platform.openai.com/docs/",
    },
    # Node.js / NPM
    "express": {
        "purpose": "Fast, unopinionated, minimalist web framework for Node.js",
        "url": "https://expressjs.com/",
    },
    "axios": {
        "purpose": "Promise-based HTTP client for the browser and Node.js",
        "url": "https://axios-http.com/",
    },
    "pg": {
        "purpose": "Non-blocking PostgreSQL client for Node.js",
        "url": "https://node-postgres.com/",
    },
    "ioredis": {
        "purpose": "Robust, performance-focused Redis client for Node.js",
        "url": "https://ioredis.readthedocs.io/",
    },
    "mongoose": {
        "purpose": "MongoDB object modeling tool for asynchronous environments",
        "url": "https://mongoosejs.com/",
    },
    "jsonwebtoken": {
        "purpose": "JSON Web Token (JWT) implementation for Node.js",
        "url": "https://github.com/auth0/node-jsonwebtoken",
    },
    "dotenv": {
        "purpose": "Zero-dependency module that loads environment variables from a .env file",
        "url": "https://github.com/motdotla/dotenv",
    },
}

# Python package alias mapping (PyPI package name -> import module name)
PYTHON_IMPORT_ALIASES: Dict[str, str] = {
    "pyyaml": "yaml",
    "python-dotenv": "dotenv",
    "psycopg2-binary": "psycopg2",
    "pydantic-settings": "pydantic_settings",
    "djangorestframework": "rest_framework",
    "opencv-python": "cv2",
    "pillow": "PIL",
    "beautifulsoup4": "bs4",
    "scikit-learn": "sklearn",
}

# Verified known vulnerability advisory database for test packages or known historical versions
# Strictly verified CVEs only - never invented
VERIFIED_VULNERABILITY_DB: Dict[str, List[Dict[str, Any]]] = {
    "requests": [
        {
            "vulnerability_id": "CVE-2018-18074",
            "affected_versions": "<2.20.0",
            "severity": "medium",
            "description": "Requests allows HTTP Authorization header leak on cross-origin redirects.",
            "advisory_url": "https://nvd.nist.gov/vuln/detail/CVE-2018-18074",
        }
    ],
    "pyyaml": [
        {
            "vulnerability_id": "CVE-2020-14343",
            "affected_versions": "<5.4",
            "severity": "critical",
            "description": "Arbitrary code execution via full_load/unsafe_load in PyYAML.",
            "advisory_url": "https://nvd.nist.gov/vuln/detail/CVE-2020-14343",
        }
    ],
    "lodash": [
        {
            "vulnerability_id": "CVE-2019-10744",
            "affected_versions": "<4.17.12",
            "severity": "critical",
            "description": "Prototype pollution vulnerability in lodash defaultsDeep.",
            "advisory_url": "https://nvd.nist.gov/vuln/detail/CVE-2019-10744",
        }
    ],
}


class DependencyScanner:
    """Scans repository for declared and resolved dependencies, imports, and integrations."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.import_map: Dict[str, List[ImportLocation]] = {}
        self.internal_modules: Set[str] = set()
        self.integrations: List[ExternalIntegrationDoc] = []
        self.skipped_files: List[SkippedFileDoc] = []
        self.scanned_file_count = 0

    def scan(self) -> Tuple[List[DependencyDoc], List[str], List[str], List[ExternalIntegrationDoc], List[SkippedFileDoc]]:
        """
        Execute full scan of manifests, lockfiles, import sites, and external integrations.
        Returns:
            (dependencies, internal_modules, unused_dependencies, integrations, skipped_files)
        """
        # Step 1: Discover source code imports and internal module structures
        self._scan_source_tree()

        # Step 2: Scan manifests and lockfiles across ecosystems
        dependencies = self._discover_manifest_dependencies()

        # Step 3: Match declared packages with imported packages
        unused_dependencies: List[str] = []
        for dep in dependencies:
            norm_name = self._normalize_package_name(dep.package_name, dep.ecosystem)
            import_locations = self.import_map.get(norm_name, [])
            if not import_locations:
                # Also check direct lowercase name
                import_locations = self.import_map.get(dep.package_name.lower().replace("-", "_"), [])

            dep.import_locations = import_locations
            dep.is_used = len(import_locations) > 0
            if not dep.is_used and dep.is_direct:
                unused_dependencies.append(dep.package_name)

            # Check verified vulnerabilities
            dep.vulnerabilities = self._check_verified_vulnerabilities(dep.package_name, dep.resolved_version)

        # Step 4: Scan external integrations (HTTP, SDKs, DB, queues, config)
        self._scan_external_integrations()

        return dependencies, sorted(list(self.internal_modules)), sorted(unused_dependencies), self.integrations, self.skipped_files

    def _normalize_package_name(self, name: str, ecosystem: str) -> str:
        """Normalize package name to matching import module name."""
        name_lower = name.lower()
        if ecosystem == "python":
            if name_lower in PYTHON_IMPORT_ALIASES:
                return PYTHON_IMPORT_ALIASES[name_lower]
            return name_lower.replace("-", "_")
        return name_lower

    def _scan_source_tree(self) -> None:
        """Walk source tree to collect AST imports, require calls, and internal module names."""
        ignore_dirs = {
            ".git", ".venv", "venv", "node_modules", "__pycache__",
            ".pytest_cache", ".idea", "dist", "build", ".next", ".nuxt", "target"
        }

        for root, dirs, files in os.walk(self.repo_root):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]

            rel_root = Path(root).relative_to(self.repo_root)
            for f in files:
                file_path = Path(root) / f
                rel_path = file_path.relative_to(self.repo_root)
                ext = file_path.suffix.lower()

                # Register Python packages/modules as internal
                if ext == ".py":
                    mod_name = file_path.stem
                    if mod_name != "__init__":
                        self.internal_modules.add(mod_name)
                    if len(rel_root.parts) > 0:
                        self.internal_modules.add(rel_root.parts[0])

                if ext in {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                    self.scanned_file_count += 1
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        if ext == ".py":
                            self._extract_python_imports(content, str(rel_path))
                        else:
                            self._extract_js_imports(content, str(rel_path))
                    except Exception as exc:
                        self.skipped_files.append(
                            SkippedFileDoc(file_path=str(rel_path), reason=f"Failed to read/parse: {exc}")
                        )

    def _extract_python_imports(self, content: str, file_path_str: str) -> None:
        """Parse Python source file for imports using AST with regex fallback."""
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_pkg = alias.name.split(".")[0].lower()
                        loc = ImportLocation(
                            file=file_path_str,
                            line=node.lineno,
                            statement=f"import {alias.name}",
                        )
                        self.import_map.setdefault(root_pkg, []).append(loc)
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0 and node.module:
                        root_pkg = node.module.split(".")[0].lower()
                        imported_names = ", ".join([a.name for a in node.names[:3]])
                        loc = ImportLocation(
                            file=file_path_str,
                            line=node.lineno,
                            statement=f"from {node.module} import {imported_names}",
                        )
                        self.import_map.setdefault(root_pkg, []).append(loc)
        except SyntaxError:
            # Fallback to regex on syntax errors or partial templates
            for line_no, line in enumerate(content.splitlines(), 1):
                m_imp = re.match(r"^\s*import\s+([a-zA-Z0-9_\.]+)", line)
                if m_imp:
                    root_pkg = m_imp.group(1).split(".")[0].lower()
                    loc = ImportLocation(file=file_path_str, line=line_no, statement=line.strip())
                    self.import_map.setdefault(root_pkg, []).append(loc)
                m_from = re.match(r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import", line)
                if m_from:
                    root_pkg = m_from.group(1).split(".")[0].lower()
                    loc = ImportLocation(file=file_path_str, line=line_no, statement=line.strip())
                    self.import_map.setdefault(root_pkg, []).append(loc)

    def _extract_js_imports(self, content: str, file_path_str: str) -> None:
        """Parse JavaScript and TypeScript imports using pattern matching."""
        import_pattern = re.compile(r"""(?:import\s+.*?from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\)|import\s*\(\s*['"]([^'"]+)['"]\s*\))""")
        for line_no, line in enumerate(content.splitlines(), 1):
            for match in import_pattern.finditer(line):
                pkg_ref = match.group(1) or match.group(2) or match.group(3)
                if pkg_ref and not pkg_ref.startswith(".") and not pkg_ref.startswith("/"):
                    # Extract root package or scoped package (@scope/pkg)
                    parts = pkg_ref.split("/")
                    if pkg_ref.startswith("@") and len(parts) >= 2:
                        root_pkg = f"{parts[0]}/{parts[1]}".lower()
                    else:
                        root_pkg = parts[0].lower()

                    loc = ImportLocation(file=file_path_str, line=line_no, statement=line.strip())
                    self.import_map.setdefault(root_pkg, []).append(loc)

    def _discover_manifest_dependencies(self) -> List[DependencyDoc]:
        """Discover dependencies from all found manifests and lockfiles."""
        dependencies: Dict[str, DependencyDoc] = {}

        # 1. Python: requirements.txt, pyproject.toml, poetry.lock, Pipfile.lock
        self._scan_python_manifests(dependencies)

        # 2. Node.js: package.json, package-lock.json, yarn.lock
        self._scan_node_manifests(dependencies)

        # 3. Go: go.mod, go.sum
        self._scan_go_manifests(dependencies)

        # 4. Cargo: Cargo.toml, Cargo.lock
        self._scan_cargo_manifests(dependencies)

        return list(dependencies.values())

    def _scan_python_manifests(self, deps: Dict[str, DependencyDoc]) -> None:
        """Scan Python dependency files."""
        # Check poetry.lock or Pipfile.lock first to get resolved versions
        poetry_lock = self.repo_root / "poetry.lock"
        poetry_resolved: Dict[str, str] = {}
        if poetry_lock.is_file():
            try:
                content = poetry_lock.read_text(encoding="utf-8")
                # Parse [[package]] blocks
                pkg_blocks = re.split(r"\[\[package\]\]", content)
                for block in pkg_blocks[1:]:
                    name_m = re.search(r'name\s*=\s*"([^"]+)"', block)
                    ver_m = re.search(r'version\s*=\s*"([^"]+)"', block)
                    if name_m and ver_m:
                        poetry_resolved[name_m.group(1).lower()] = ver_m.group(1)
            except Exception as exc:
                logger.debug(f"Failed parsing poetry.lock: {exc}")

        # Scan requirements.txt (and variants)
        for req_file in self.repo_root.rglob("*requirements*.txt"):
            if any(part in req_file.parts for part in [".venv", "venv", "node_modules", ".git"]):
                continue
            try:
                rel_manifest = str(req_file.relative_to(self.repo_root))
                for line in req_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    # Remove inline comments
                    line = line.split("#")[0].strip()
                    m = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)", line)
                    if m:
                        pkg_name = m.group(1).strip()
                        constraint = m.group(2).strip() or None
                        resolved = None

                        if constraint and constraint.startswith("=="):
                            resolved = constraint[2:].strip()
                        elif pkg_name.lower() in poetry_resolved:
                            resolved = poetry_resolved[pkg_name.lower()]

                        key = f"python:{pkg_name.lower()}"
                        if key not in deps:
                            purpose_info = PACKAGE_CATALOG.get(pkg_name.lower(), {})
                            doc_url = purpose_info.get("url") or f"https://pypi.org/project/{pkg_name}/"
                            purpose = purpose_info.get("purpose")
                            is_inferred = purpose is None
                            if is_inferred:
                                purpose = f"Python library: {pkg_name}"

                            deps[key] = DependencyDoc(
                                package_name=pkg_name,
                                ecosystem="python",
                                declared_constraint=constraint,
                                resolved_version=resolved,
                                is_direct=True,
                                purpose=purpose,
                                is_inferred_purpose=is_inferred,
                                official_documentation_url=doc_url,
                                manifest_file=rel_manifest,
                            )
            except Exception as exc:
                logger.debug(f"Error scanning {req_file}: {exc}")

        # Scan pyproject.toml
        pyproject = self.repo_root / "pyproject.toml"
        if pyproject.is_file():
            try:
                rel_manifest = "pyproject.toml"
                content = pyproject.read_text(encoding="utf-8")
                # Parse [project] dependencies
                proj_dep_m = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
                if proj_dep_m:
                    dep_items = re.findall(r'["\']([^"\']+)["\']', proj_dep_m.group(1))
                    for item in dep_items:
                        m = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)", item.strip())
                        if m:
                            pkg_name = m.group(1).strip()
                            constraint = m.group(2).strip() or None
                            resolved = poetry_resolved.get(pkg_name.lower())
                            if constraint and constraint.startswith("=="):
                                resolved = constraint[2:].strip()

                            key = f"python:{pkg_name.lower()}"
                            if key not in deps:
                                purpose_info = PACKAGE_CATALOG.get(pkg_name.lower(), {})
                                doc_url = purpose_info.get("url") or f"https://pypi.org/project/{pkg_name}/"
                                purpose = purpose_info.get("purpose")
                                is_inferred = purpose is None
                                if is_inferred:
                                    purpose = f"Python library: {pkg_name}"

                                deps[key] = DependencyDoc(
                                    package_name=pkg_name,
                                    ecosystem="python",
                                    declared_constraint=constraint,
                                    resolved_version=resolved,
                                    is_direct=True,
                                    purpose=purpose,
                                    is_inferred_purpose=is_inferred,
                                    official_documentation_url=doc_url,
                                    manifest_file=rel_manifest,
                                )
            except Exception as exc:
                logger.debug(f"Error reading pyproject.toml: {exc}")

    def _scan_node_manifests(self, deps: Dict[str, DependencyDoc]) -> None:
        """Scan Node.js package.json and lockfiles."""
        for pkg_json_path in self.repo_root.rglob("package.json"):
            if any(part in pkg_json_path.parts for part in ["node_modules", ".git", ".venv"]):
                continue
            try:
                rel_manifest = str(pkg_json_path.relative_to(self.repo_root))
                data = json.loads(pkg_json_path.read_text(encoding="utf-8"))

                # Try to find corresponding package-lock.json
                lock_file = pkg_json_path.parent / "package-lock.json"
                lock_resolved: Dict[str, str] = {}
                if lock_file.is_file():
                    try:
                        lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
                        # npm v7+ packages
                        if "packages" in lock_data:
                            for p_path, p_info in lock_data["packages"].items():
                                if p_path.startswith("node_modules/"):
                                    p_name = p_path.replace("node_modules/", "")
                                    lock_resolved[p_name.lower()] = p_info.get("version")
                        # npm v6 dependencies
                        if "dependencies" in lock_data:
                            for d_name, d_info in lock_data["dependencies"].items():
                                lock_resolved[d_name.lower()] = d_info.get("version")
                    except Exception:
                        pass

                all_deps = {}
                all_deps.update(data.get("dependencies", {}))
                all_deps.update(data.get("devDependencies", {}))

                for pkg_name, constraint in all_deps.items():
                    key = f"npm:{pkg_name.lower()}"
                    if key not in deps:
                        resolved = lock_resolved.get(pkg_name.lower())
                        purpose_info = PACKAGE_CATALOG.get(pkg_name.lower(), {})
                        doc_url = purpose_info.get("url") or f"https://www.npmjs.com/package/{pkg_name}"
                        purpose = purpose_info.get("purpose")
                        is_inferred = purpose is None
                        if is_inferred:
                            purpose = f"Node.js npm package: {pkg_name}"

                        deps[key] = DependencyDoc(
                            package_name=pkg_name,
                            ecosystem="npm",
                            declared_constraint=constraint,
                            resolved_version=resolved,
                            is_direct=True,
                            purpose=purpose,
                            is_inferred_purpose=is_inferred,
                            official_documentation_url=doc_url,
                            manifest_file=rel_manifest,
                        )
            except Exception as exc:
                logger.debug(f"Error reading package.json at {pkg_json_path}: {exc}")

    def _scan_go_manifests(self, deps: Dict[str, DependencyDoc]) -> None:
        """Scan Go go.mod manifests."""
        for go_mod in self.repo_root.rglob("go.mod"):
            if any(part in go_mod.parts for part in [".git", "vendor"]):
                continue
            try:
                rel_manifest = str(go_mod.relative_to(self.repo_root))
                content = go_mod.read_text(encoding="utf-8")
                # Look for require (...) or single require
                req_blocks = re.findall(r"require\s*\((.*?)\)", content, re.DOTALL)
                for block in req_blocks:
                    for line in block.splitlines():
                        line = line.strip()
                        if line and not line.startswith("//"):
                            parts = line.split()
                            if len(parts) >= 2:
                                pkg_name, ver = parts[0], parts[1]
                                key = f"go:{pkg_name.lower()}"
                                deps[key] = DependencyDoc(
                                    package_name=pkg_name,
                                    ecosystem="go",
                                    declared_constraint=ver,
                                    resolved_version=ver,
                                    is_direct=True,
                                    purpose=f"Go module: {pkg_name}",
                                    is_inferred_purpose=True,
                                    official_documentation_url=f"https://pkg.go.dev/{pkg_name}",
                                    manifest_file=rel_manifest,
                                )
            except Exception as exc:
                logger.debug(f"Error parsing go.mod: {exc}")

    def _scan_cargo_manifests(self, deps: Dict[str, DependencyDoc]) -> None:
        """Scan Rust Cargo.toml manifests."""
        for cargo_toml in self.repo_root.rglob("Cargo.toml"):
            if any(part in cargo_toml.parts for part in [".git", "target"]):
                continue
            try:
                rel_manifest = str(cargo_toml.relative_to(self.repo_root))
                content = cargo_toml.read_text(encoding="utf-8")
                # Parse [dependencies]
                dep_sec = re.search(r"\[dependencies\](.*?)(?:\[|\Z)", content, re.DOTALL)
                if dep_sec:
                    for line in dep_sec.group(1).splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            m = re.match(r"^([a-zA-Z0-9_\-]+)\s*=\s*(.*)", line)
                            if m:
                                pkg_name = m.group(1).strip()
                                constraint = m.group(2).strip().strip('"\'')
                                key = f"cargo:{pkg_name.lower()}"
                                deps[key] = DependencyDoc(
                                    package_name=pkg_name,
                                    ecosystem="cargo",
                                    declared_constraint=constraint,
                                    resolved_version=None,
                                    is_direct=True,
                                    purpose=f"Rust crate: {pkg_name}",
                                    is_inferred_purpose=True,
                                    official_documentation_url=f"https://crates.io/crates/{pkg_name}",
                                    manifest_file=rel_manifest,
                                )
            except Exception as exc:
                logger.debug(f"Error parsing Cargo.toml: {exc}")

    def _check_verified_vulnerabilities(self, package_name: str, resolved_version: Optional[str]) -> List[Dict[str, Any]]:
        """Check for verified vulnerabilities in local advisory database without hallucination."""
        vulns = VERIFIED_VULNERABILITY_DB.get(package_name.lower(), [])
        if not vulns or not resolved_version:
            return []

        matched = []
        for v in vulns:
            affected = v.get("affected_versions", "")
            if affected.startswith("<"):
                max_ver = affected[1:].strip()
                # Simple version comparison
                if self._version_less(resolved_version, max_ver):
                    matched.append(v)
        return matched

    def _version_less(self, v1: str, v2: str) -> bool:
        """Helper to compare simple semver strings."""
        try:
            p1 = [int(x) for x in re.findall(r"\d+", v1)]
            p2 = [int(x) for x in re.findall(r"\d+", v2)]
            return p1 < p2
        except Exception:
            return False

    def _scan_external_integrations(self) -> None:
        """
        Scan for external services and integrations:
        - Outbound HTTP calls
        - SDK client initializations
        - Database clients and queries
        - Message brokers
        - Safe configuration references with secret redaction
        """
        config_refs = self._scan_configuration_references()

        ignore_dirs = {
            ".git", ".venv", "venv", "node_modules", "__pycache__",
            ".pytest_cache", ".idea", "dist", "build", "target"
        }

        # Outbound HTTP patterns
        http_patterns = [
            (re.compile(r"""(?:requests|httpx)\.(get|post|put|delete|patch)\s*\(\s*(['"][^'"]+['"])"""), "python_http"),
            (re.compile(r"""(?:axios)\.(get|post|put|delete|patch)\s*\(\s*(['"][^'"]+['"])"""), "node_axios"),
            (re.compile(r"""fetch\s*\(\s*(['"][^'"]+['"])"""), "js_fetch"),
        ]

        # Database patterns
        db_patterns = [
            (re.compile(r"""psycopg2\.connect\s*\((.*?)\)"""), "PostgreSQL (psycopg2)", "database"),
            (re.compile(r"""asyncpg\.create_pool\s*\((.*?)\)"""), "PostgreSQL (asyncpg)", "database"),
            (re.compile(r"""create_engine\s*\((.*?)\)"""), "SQLAlchemy Engine", "database"),
            (re.compile(r"""sqlite3\.connect\s*\((.*?)\)"""), "SQLite3 Client", "database"),
            (re.compile(r"""redis\.Redis\s*\((.*?)\)"""), "Redis Client", "cache"),
            (re.compile(r"""redis\.from_url\s*\((.*?)\)"""), "Redis Client", "cache"),
            (re.compile(r"""MongoClient\s*\((.*?)\)"""), "MongoDB (pymongo)", "database"),
            (re.compile(r"""new\s+Pool\s*\((.*?)\)"""), "PostgreSQL (pg Pool)", "database"),
            (re.compile(r"""new\s+PrismaClient\s*\((.*?)\)"""), "Prisma ORM Client", "database"),
        ]

        # SDK Client patterns
        sdk_patterns = [
            (re.compile(r"""stripe\.[A-Za-z]+\.[A-Za-z]+"""), "Stripe API SDK", "sdk_client"),
            (re.compile(r"""boto3\.(client|resource)\s*\(\s*['"]([^'"]+)['"]"""), "AWS SDK (boto3)", "sdk_client"),
            (re.compile(r"""SendGridAPIClient\s*\((.*?)\)"""), "SendGrid Email SDK", "sdk_client"),
            (re.compile(r"""twilio\.rest\.Client\s*\((.*?)\)"""), "Twilio SMS/Voice SDK", "sdk_client"),
            (re.compile(r"""OpenAI\s*\((.*?)\)"""), "OpenAI API Client", "sdk_client"),
            (re.compile(r"""pika\.BlockingConnection\s*\((.*?)\)"""), "RabbitMQ (pika)", "message_broker"),
            (re.compile(r"""KafkaProducer\s*\((.*?)\)"""), "Apache Kafka Producer", "message_broker"),
            (re.compile(r"""KafkaConsumer\s*\((.*?)\)"""), "Apache Kafka Consumer", "message_broker"),
            (re.compile(r"""@celery\.task|\.apply_async\s*\("""), "Celery Task Broker", "message_broker"),
        ]

        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            for f in files:
                file_path = Path(root) / f
                rel_path = str(file_path.relative_to(self.repo_root))
                ext = file_path.suffix.lower()

                if ext in {".py", ".js", ".ts", ".jsx", ".tsx"}:
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")

                        # For Python, use AST to reliably extract multiline calls
                        if ext == ".py":
                            try:
                                tree = ast.parse(content)
                                for node in ast.walk(tree):
                                    if isinstance(node, ast.Call):
                                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                                            caller = node.func.value.id.lower()
                                            method = node.func.attr.lower()

                                            # HTTP client: httpx or requests
                                            if caller in {"httpx", "requests"} and method in {"get", "post", "put", "delete", "patch", "options", "head"}:
                                                raw_url = None
                                                if node.args and isinstance(node.args[0], ast.Constant):
                                                    raw_url = str(node.args[0].value)
                                                elif node.keywords:
                                                    for kw in node.keywords:
                                                        if kw.arg in ["url", "target"] and isinstance(kw.value, ast.Constant):
                                                            raw_url = str(kw.value.value)
                                                            break
                                                if raw_url:
                                                    clean_url, secrets_count = self._sanitize_url(raw_url)
                                                    self.integrations.append(
                                                        ExternalIntegrationDoc(
                                                            integration_type="http_service",
                                                            service_name=self._extract_service_name_from_url(clean_url),
                                                            target_url_or_host=clean_url,
                                                            file_path=rel_path,
                                                            line_number=node.lineno,
                                                            code_snippet=self._sanitize_string(f"{caller}.{method}(\"{clean_url}\")"),
                                                            operations=[method.upper()],
                                                            config_references=[c for c in config_refs if c in content],
                                                            redacted_secrets_count=secrets_count,
                                                        )
                                                    )
                                            # Database: psycopg2
                                            elif caller == "psycopg2" and method == "connect":
                                                self.integrations.append(
                                                    ExternalIntegrationDoc(
                                                        integration_type="database",
                                                        service_name="PostgreSQL (psycopg2)",
                                                        target_url_or_host=None,
                                                        file_path=rel_path,
                                                        line_number=node.lineno,
                                                        code_snippet=self._sanitize_string("psycopg2.connect(...)"),
                                                        operations=["connect", "query"],
                                                        config_references=[c for c in config_refs if c in content],
                                                    )
                                                )
                                            # Cache / Broker: redis
                                            elif caller == "redis" and method in {"redis", "from_url"}:
                                                self.integrations.append(
                                                    ExternalIntegrationDoc(
                                                        integration_type="cache",
                                                        service_name="Redis Client",
                                                        target_url_or_host=None,
                                                        file_path=rel_path,
                                                        line_number=node.lineno,
                                                        code_snippet=self._sanitize_string(f"redis.{method}(...)"),
                                                        operations=["connect", "publish", "query"],
                                                        config_references=[c for c in config_refs if c in content],
                                                    )
                                                )
                            except Exception:
                                pass

                        # General regex fallback for lines
                        lines = content.splitlines()
                        for line_idx, line in enumerate(lines, 1):
                            # Check outbound HTTP (JS/other)
                            if ext != ".py":
                                for pat, p_type in http_patterns:
                                    m = pat.search(line)
                                    if m:
                                        op, raw_url = (m.group(1).upper(), m.group(2).strip("\"'")) if p_type == "node_axios" else ("GET", m.group(1).strip("\"'"))
                                        clean_url, secrets_count = self._sanitize_url(raw_url)
                                        self.integrations.append(
                                            ExternalIntegrationDoc(
                                                integration_type="http_service",
                                                service_name=self._extract_service_name_from_url(clean_url),
                                                target_url_or_host=clean_url,
                                                file_path=rel_path,
                                                line_number=line_idx,
                                                code_snippet=self._sanitize_string(line.strip()),
                                                operations=[op],
                                                config_references=[c for c in config_refs if c in line],
                                                redacted_secrets_count=secrets_count,
                                            )
                                        )

                            # Check databases (JS/other)
                            if ext != ".py":
                                for pat, db_name, itype in db_patterns:
                                    if pat.search(line):
                                        self.integrations.append(
                                            ExternalIntegrationDoc(
                                                integration_type=itype,
                                                service_name=db_name,
                                                target_url_or_host=None,
                                                file_path=rel_path,
                                                line_number=line_idx,
                                                code_snippet=self._sanitize_string(line.strip()),
                                                operations=["connect", "query"],
                                                config_references=[c for c in config_refs if c in line],
                                            )
                                        )

                            # Check SDKs and message brokers
                            for pat, sdk_name, itype in sdk_patterns:
                                m = pat.search(line)
                                if m:
                                    target = m.group(2) if m.lastindex and m.lastindex >= 2 else None
                                    self.integrations.append(
                                        ExternalIntegrationDoc(
                                            integration_type=itype,
                                            service_name=sdk_name + (f" ({target})" if target else ""),
                                            target_url_or_host=target,
                                            file_path=rel_path,
                                            line_number=line_idx,
                                            code_snippet=self._sanitize_string(line.strip()),
                                            operations=["invoke"],
                                            config_references=[c for c in config_refs if c in line],
                                        )
                                    )
                    except Exception as exc:
                        logger.debug(f"Error scanning file {rel_path} for integrations: {exc}")

    def _scan_configuration_references(self) -> Set[str]:
        """Discover configuration and environment variable keys safely without exposing values."""
        config_keys: Set[str] = set()
        env_files = list(self.repo_root.glob("*.env*")) + list(self.repo_root.glob("config/*.env*"))

        for env_file in env_files:
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        if parts:
                            key = parts[0].strip()
                            if re.match(r"^[A-Z0-9_]+$", key):
                                config_keys.add(key)
            except Exception:
                pass

        return config_keys

    def _sanitize_string(self, text: str) -> str:
        """Mask and redact any secret keys, passwords, or credentials in a code string."""
        # Mask standard credential patterns
        patterns = [
            (r"""(['"]?)(?:sk_live_|sk_test_|ghp_|xoxb-|bearer\s+)[A-Za-z0-9_\-\.]{8,}(['"]?)""", r"\1[REDACTED]\2"),
            (r"""(password|secret|api_key|token)\s*[:=]\s*['"][^'"]+['"]""", r"\1=[REDACTED]"),
            (r"""://([^:]+):([^@]+)@""", r"://\1:[REDACTED]@"),
        ]
        sanitized = text
        for p, r in patterns:
            sanitized = re.sub(p, r, sanitized, flags=re.IGNORECASE)
        return sanitized

    def _sanitize_url(self, raw_url: str) -> Tuple[str, int]:
        """Redact query token parameters or embedded passwords in URL."""
        secrets_redacted = 0
        clean_url = raw_url

        # Check basic auth credentials in URL
        if "://" in clean_url and "@" in clean_url:
            clean_url = re.sub(r"://([^:]+):([^@]+)@", r"://\1:[REDACTED]@", clean_url)
            secrets_redacted += 1

        # Check sensitive query parameters
        sensitive_params = ["key", "api_key", "token", "secret", "password", "auth"]
        for p in sensitive_params:
            if f"{p}=" in clean_url.lower():
                clean_url = re.sub(rf"({p}=)[^&#]+", rf"\1[REDACTED]", clean_url, flags=re.IGNORECASE)
                secrets_redacted += 1

        return clean_url, secrets_redacted

    def _extract_service_name_from_url(self, url: str) -> str:
        """Derive friendly service name from target URL."""
        if "stripe.com" in url:
            return "Stripe API"
        if "github.com" in url or "api.github" in url:
            return "GitHub API"
        if "amazonaws.com" in url:
            return "AWS Service Endpoint"
        if "slack.com" in url:
            return "Slack Webhook/API"
        if "sendgrid.com" in url:
            return "SendGrid Email API"
        if "twilio.com" in url:
            return "Twilio Communications API"
        if "openai.com" in url:
            return "OpenAI API"

        # Extract domain
        m = re.search(r"://([^/:]+)", url)
        if m:
            return f"External Service ({m.group(1)})"
        return "External HTTP Service"
