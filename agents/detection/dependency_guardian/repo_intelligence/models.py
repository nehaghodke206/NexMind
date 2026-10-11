"""
Repository Intelligence and API Documentation Agent Data Models.
Comprehensive, evidence-backed contracts for scanned repository inventory.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ParameterDoc(BaseModel):
    """Specification for route, query, header, or cookie parameter."""
    name: str
    in_location: str  # "path", "query", "header", "cookie"
    param_type: str = "string"
    required: bool = True
    default: Optional[Any] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    enum_values: Optional[List[Any]] = None
    description: Optional[str] = None
    is_inferred: bool = False
    provenance: str = "explicit"


class FieldDoc(BaseModel):
    """Schema property / field documentation."""
    name: str
    field_type: str = "string"
    required: bool = True
    default: Optional[Any] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    enum_values: Optional[List[Any]] = None
    description: Optional[str] = None
    is_inferred: bool = False
    provenance: str = "explicit"


class RequestBodyDoc(BaseModel):
    """Request body specification."""
    content_type: str = "application/json"
    schema_name: Optional[str] = None
    required: bool = True
    fields: List[FieldDoc] = Field(default_factory=list)
    description: Optional[str] = None
    is_inferred: bool = False
    provenance: str = "explicit"


class ResponseDoc(BaseModel):
    """Response code and schema specification."""
    status_code: int = 200
    description: Optional[str] = None
    schema_name: Optional[str] = None
    fields: List[FieldDoc] = Field(default_factory=list)
    is_inferred: bool = False
    provenance: str = "explicit"


class ErrorCaseDoc(BaseModel):
    """Documented error scenario."""
    status_code: int
    condition: str
    exception_type: Optional[str] = None


class SideEffectDoc(BaseModel):
    """Side effect caused by handler execution."""
    effect_type: str  # "database_write", "database_read", "external_http", "message_publish", "cache_mutation"
    target: str
    description: str


class EndpointDoc(BaseModel):
    """Complete endpoint document capturing every discoverable detail."""
    http_method: str
    route_path: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[ParameterDoc] = Field(default_factory=list)
    request_body: Optional[RequestBodyDoc] = None
    responses: List[ResponseDoc] = Field(default_factory=list)
    auth_and_authz: Optional[str] = None
    auth_inferred: bool = False
    error_cases: List[ErrorCaseDoc] = Field(default_factory=list)
    side_effects: List[SideEffectDoc] = Field(default_factory=list)
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    handler_function: Optional[str] = None
    relevant_dependencies: List[str] = Field(default_factory=list)
    existing_tests: List[str] = Field(default_factory=list)
    generated_tests: List[str] = Field(default_factory=list)
    test_results: Optional[str] = None
    discovery_method: str = "framework_ast"  # "framework_ast", "openapi_spec", "hybrid"
    evidence_source: str = "source_ast"
    confidence_level: float = 1.0
    is_inferred: bool = False


class ImportLocation(BaseModel):
    """Location in source code where a package is imported or required."""
    file: str
    line: int
    statement: str


class DependencyDoc(BaseModel):
    """External dependency record."""
    package_name: str
    ecosystem: str  # "python", "npm", "go", "cargo", "maven", "gem", "composer"
    declared_constraint: Optional[str] = None
    resolved_version: Optional[str] = None
    is_direct: bool = True
    purpose: Optional[str] = None
    is_inferred_purpose: bool = False
    is_used: bool = False
    import_locations: List[ImportLocation] = Field(default_factory=list)
    official_documentation_url: Optional[str] = None
    configuration_requirements: List[str] = Field(default_factory=list)
    vulnerabilities: List[Dict[str, Any]] = Field(default_factory=list)
    manifest_file: Optional[str] = None


class ExternalIntegrationDoc(BaseModel):
    """External integration or third-party service interface."""
    integration_type: str  # "database", "http_service", "sdk_client", "message_broker", "cache"
    service_name: str
    target_url_or_host: Optional[str] = None
    file_path: str
    line_number: int
    code_snippet: str
    config_references: List[str] = Field(default_factory=list)
    operations: List[str] = Field(default_factory=list)
    redacted_secrets_count: int = 0


class DiscrepancyDoc(BaseModel):
    """Discrepancy between source code and OpenAPI specifications."""
    discrepancy_type: str  # "undocumented_endpoint", "ghost_endpoint", "parameter_mismatch", "response_mismatch"
    endpoint_path: str
    method: str
    description: str
    code_evidence: Optional[str] = None
    spec_evidence: Optional[str] = None


class UnsupportedItemDoc(BaseModel):
    """Explanation of unsupported framework or unresolved dynamic route."""
    item_type: str  # "unsupported_framework", "unresolved_dynamic_route"
    file_path: str
    line_number: Optional[int] = None
    reason: str
    code_snippet: Optional[str] = None


class SkippedFileDoc(BaseModel):
    """Record of files skipped during scanning."""
    file_path: str
    reason: str


class TestCoverageSummary(BaseModel):
    """Summary of test coverage across discovered endpoints."""
    total_endpoints: int = 0
    tested_endpoints: int = 0
    untested_endpoints: int = 0
    coverage_percentage: float = 0.0
    endpoint_coverage_map: Dict[str, List[str]] = Field(default_factory=dict)
    integration_tests_found: List[str] = Field(default_factory=list)


class ScannerMetadata(BaseModel):
    """Metadata regarding repository scanner execution."""
    scanner_name: str = "Dependency Guardian Repository Intelligence"
    scanner_version: str = "0.2.0"
    scanned_path: str
    scan_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    languages_detected: List[str] = Field(default_factory=list)
    frameworks_detected: List[str] = Field(default_factory=list)
    total_files_scanned: int = 0
    skipped_files: List[SkippedFileDoc] = Field(default_factory=list)
    openapi_specs_found: List[str] = Field(default_factory=list)


class RepositoryInventory(BaseModel):
    """Complete machine-readable inventory of scanned repository."""
    metadata: ScannerMetadata
    dependencies: List[DependencyDoc] = Field(default_factory=list)
    internal_modules: List[str] = Field(default_factory=list)
    unused_dependencies: List[str] = Field(default_factory=list)
    integrations: List[ExternalIntegrationDoc] = Field(default_factory=list)
    endpoints: List[EndpointDoc] = Field(default_factory=list)
    discrepancies: List[DiscrepancyDoc] = Field(default_factory=list)
    unsupported_frameworks: List[UnsupportedItemDoc] = Field(default_factory=list)
    unresolved_dynamic_routes: List[UnsupportedItemDoc] = Field(default_factory=list)
    test_coverage: TestCoverageSummary
    ai_insights: Optional[Dict[str, Any]] = None
