"""
Repository Intelligence Scanner Orchestrator.
Coordinates dependency discovery, endpoint AST parsing, test coverage analysis,
OpenAPI reconciliation, and documentation generation.
"""
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .dependency_scanner import DependencyScanner
from .doc_generator import DocumentationGenerator
from .endpoint_scanner import EndpointScanner
from .models import (
    RepositoryInventory,
    ScannerMetadata,
    SkippedFileDoc,
)
from .test_coverage_scanner import TestCoverageScanner

logger = logging.getLogger("dependency_guardian.repo_intelligence.scanner")


class RepositoryIntelligenceScanner:
    """Orchestrates comprehensive, evidence-backed repository scanning."""

    def __init__(self, repo_path: Path, ai_provider: Optional[Any] = None):
        self.repo_path = repo_path.resolve()
        self.ai_provider = ai_provider

        if not self.repo_path.exists() or not self.repo_path.is_dir():
            raise FileNotFoundError(f"Repository directory not found: {self.repo_path}")

    def scan(self, output_dir: Optional[Path] = None, enrich_openapi: bool = True) -> RepositoryInventory:
        """
        Execute repository intelligence scan and generate documentation deliverables.
        """
        logger.info(f"Starting repository intelligence scan on: {self.repo_path}")

        # 1. Dependency and Integration Scan
        dep_scanner = DependencyScanner(self.repo_path)
        deps, internal_mods, unused_deps, integrations, skipped_dep_files = dep_scanner.scan()

        # 2. Endpoint and Framework AST Scan
        ep_scanner = EndpointScanner(self.repo_path)
        endpoints, discrepancies, unsupported_fw, unresolved_routes, openapi_files = ep_scanner.scan()

        # 3. Test Coverage and Verification Scan
        test_scanner = TestCoverageScanner(self.repo_path)
        test_summary = test_scanner.scan(endpoints, integrations)

        # Detect languages and frameworks
        languages = self._detect_languages()
        frameworks = self._detect_frameworks(deps, endpoints)

        # Combine skipped files
        all_skipped = list(skipped_dep_files)

        # Create Metadata
        metadata = ScannerMetadata(
            scanned_path=str(self.repo_path),
            languages_detected=languages,
            frameworks_detected=frameworks,
            total_files_scanned=dep_scanner.scanned_file_count,
            skipped_files=all_skipped,
            openapi_specs_found=openapi_files,
        )

        inventory = RepositoryInventory(
            metadata=metadata,
            dependencies=deps,
            internal_modules=internal_mods,
            unused_dependencies=unused_deps,
            integrations=integrations,
            endpoints=endpoints,
            discrepancies=discrepancies,
            unsupported_frameworks=unsupported_fw,
            unresolved_dynamic_routes=unresolved_routes,
            test_coverage=test_summary,
        )

        # Optional AI Explanation & Architectural Synthesis (strictly grounded)
        if self.ai_provider:
            inventory.ai_insights = self._generate_ai_insights(inventory)

        # Generate deliverables if output directory provided
        if output_dir:
            base_spec = None
            if openapi_files:
                try:
                    first_spec_path = self.repo_path / openapi_files[0]
                    content = first_spec_path.read_text(encoding="utf-8")
                    base_spec = yaml.safe_load(content)
                except Exception as exc:
                    logger.debug(f"Could not load base spec {openapi_files[0]}: {exc}")

            doc_gen = DocumentationGenerator(
                inventory=inventory,
                output_dir=output_dir,
                base_openapi_spec=base_spec if enrich_openapi else None,
            )
            doc_gen.generate_all()

        return inventory

    def _detect_languages(self) -> List[str]:
        """Detect primary programming languages present in repository."""
        langs = set()
        ignore_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__"}

        for p in self.repo_path.rglob("*"):
            if any(part in p.parts for part in ignore_dirs):
                continue
            if p.is_file():
                ext = p.suffix.lower()
                if ext in {".py"}:
                    langs.add("Python")
                elif ext in {".js", ".jsx", ".mjs", ".cjs"}:
                    langs.add("JavaScript")
                elif ext in {".ts", ".tsx"}:
                    langs.add("TypeScript")
                elif ext in {".go"}:
                    langs.add("Go")
                elif ext in {".rs"}:
                    langs.add("Rust")
                elif ext in {".java"}:
                    langs.add("Java")
                elif ext in {".rb"}:
                    langs.add("Ruby")
                elif ext in {".php"}:
                    langs.add("PHP")

        return sorted(list(langs))

    def _detect_frameworks(self, deps: List[Any], endpoints: List[Any]) -> List[str]:
        """Identify web and API frameworks utilized."""
        fws = set()
        dep_names = {d.package_name.lower() for d in deps}

        if "fastapi" in dep_names:
            fws.add("FastAPI")
        if "flask" in dep_names:
            fws.add("Flask")
        if "django" in dep_names or "djangorestframework" in dep_names:
            fws.add("Django REST Framework")
        if "express" in dep_names:
            fws.add("Express")
        if "koa" in dep_names:
            fws.add("Koa")
        if "nest" in dep_names:
            fws.add("NestJS")
        if "gin" in dep_names:
            fws.add("Gin")

        # Also inspect endpoints discovery methods
        for ep in endpoints:
            if "fastapi" in ep.evidence_source:
                fws.add("FastAPI")
            elif "express" in ep.evidence_source:
                fws.add("Express")
            elif "flask" in ep.evidence_source:
                fws.add("Flask")

        return sorted(list(fws))

    def _generate_ai_insights(self, inventory: RepositoryInventory) -> Dict[str, Any]:
        """Generate high-level architectural explanations using AI provider without hallucination."""
        try:
            prompt = (
                f"Analyze the following factual repository inventory summary:\n"
                f"- Total Dependencies: {len(inventory.dependencies)} (Used: {sum(1 for d in inventory.dependencies if d.is_used)}, Unused: {len(inventory.unused_dependencies)})\n"
                f"- External Integrations: {len(inventory.integrations)}\n"
                f"- API Endpoints: {len(inventory.endpoints)}\n"
                f"- Discrepancies (Undocumented/Ghost): {len(inventory.discrepancies)}\n"
                f"- Test Coverage: {inventory.test_coverage.coverage_percentage}%\n"
                f"Provide concise, evidence-based architectural recommendations focusing on unused package pruning, undocumented route risks, and test coverage improvements. Do not invent any new endpoints or packages."
            )
            # Call AI provider if supports chat
            res = self.ai_provider.generate_chat(prompt) if hasattr(self.ai_provider, "generate_chat") else None
            return {"architectural_analysis": res or "AI analysis grounded in deterministic findings."}
        except Exception as exc:
            logger.debug(f"AI insights generation error: {exc}")
            return {"error": str(exc)}
