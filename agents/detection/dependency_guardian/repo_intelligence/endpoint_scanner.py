"""
API Endpoint Inventory and Framework AST Parser.
Discovers endpoints from source code AST (FastAPI, Flask, Express) and OpenAPI specs.
Extracts route parameters, request body schemas, response models, auth, error cases,
side effects, and tracks discrepancies between code and specifications.
"""
import ast
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import yaml

from .models import (
    DiscrepancyDoc,
    EndpointDoc,
    ErrorCaseDoc,
    FieldDoc,
    ParameterDoc,
    RequestBodyDoc,
    ResponseDoc,
    SideEffectDoc,
    SkippedFileDoc,
    UnsupportedItemDoc,
)
from .traversal import find_spec_files, safe_walk

logger = logging.getLogger("dependency_guardian.repo_intelligence.endpoint_scanner")


class EndpointScanner:
    """Discovers and parses API endpoints across frameworks and OpenAPI documents."""

    def __init__(self, repo_root: Path, output_dir: Optional[Path] = None, on_progress: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.repo_root = repo_root.resolve()
        self.output_dir = output_dir.resolve() if output_dir else None
        self.on_progress = on_progress
        self.code_endpoints: List[EndpointDoc] = []
        self.openapi_endpoints: List[EndpointDoc] = []
        self.discrepancies: List[DiscrepancyDoc] = []
        self.unsupported_frameworks: List[UnsupportedItemDoc] = []
        self.unresolved_dynamic_routes: List[UnsupportedItemDoc] = []
        self.openapi_files_found: List[str] = []
        self.pydantic_models_by_file: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def scan(self) -> Tuple[List[EndpointDoc], List[DiscrepancyDoc], List[UnsupportedItemDoc], List[UnsupportedItemDoc], List[str]]:
        """
        Execute endpoint discovery across source code and OpenAPI specifications.
        Returns:
            (reconciled_endpoints, discrepancies, unsupported_frameworks, unresolved_dynamic_routes, openapi_files_found)
        """
        # Step 1: Scan OpenAPI specifications
        self._scan_openapi_specs()

        # Step 2: Scan source code for frameworks
        self._scan_source_code_frameworks()

        # Step 3: Reconcile code endpoints and OpenAPI endpoints
        reconciled = self._reconcile_endpoints()

        return reconciled, self.discrepancies, self.unsupported_frameworks, self.unresolved_dynamic_routes, self.openapi_files_found

    def _normalize_route_path(self, path: str) -> str:
        """Normalize route path so /users/:id and /users/{id} match consistently."""
        clean = path.strip()
        if not clean.startswith("/"):
            clean = "/" + clean
        if len(clean) > 1 and clean.endswith("/"):
            clean = clean[:-1]
        # Express :param -> {param}
        clean = re.sub(r":([a-zA-Z0-9_]+)", r"{\1}", clean)
        # Flask <int:param> or <param> -> {param}
        clean = re.sub(r"<[a-zA-Z0-9_]+:([a-zA-Z0-9_]+)>", r"{\1}", clean)
        clean = re.sub(r"<([a-zA-Z0-9_]+)>", r"{\1}", clean)
        return clean

    # =========================================================================
    # OPENAPI / SWAGGER SPECIFICATION SCANNER
    # =========================================================================

    def _scan_openapi_specs(self) -> None:
        """Find and parse OpenAPI/Swagger JSON and YAML files."""
        found_files = find_spec_files(self.repo_root, output_dir=self.output_dir)

        for file_path in found_files:
            rel_path = str(file_path.relative_to(self.repo_root))
            try:
                content = file_path.read_text(encoding="utf-8")
                data = yaml.safe_load(content)
                if isinstance(data, dict) and ("openapi" in data or "swagger" in data):
                    self.openapi_files_found.append(rel_path)
                    self._parse_openapi_dict(data, rel_path)
            except Exception as exc:
                logger.debug(f"Failed parsing OpenAPI candidate at {rel_path}: {exc}")

    def _parse_openapi_dict(self, spec: Dict[str, Any], file_path: str) -> None:
        """Extract endpoints, schemas, parameters, and auth from OpenAPI specification."""
        paths = spec.get("paths", {})
        if not isinstance(paths, dict):
            return

        components = spec.get("components", {})
        schemas = components.get("schemas", {}) if isinstance(components, dict) else {}
        # Support Swagger 2.0 definitions
        if "definitions" in spec and isinstance(spec["definitions"], dict):
            schemas.update(spec["definitions"])

        for raw_path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            normalized_path = self._normalize_route_path(raw_path)

            for method_key in ["get", "post", "put", "delete", "patch", "options", "head"]:
                op = path_item.get(method_key)
                if not isinstance(op, dict):
                    continue

                method = method_key.upper()
                summary = op.get("summary")
                description = op.get("description")

                # Parameters
                parameters: List[ParameterDoc] = []
                raw_params = list(path_item.get("parameters", [])) + list(op.get("parameters", []))
                for p in raw_params:
                    if isinstance(p, dict):
                        p_name = p.get("name", "unknown")
                        p_in = p.get("in", "query")
                        p_schema = p.get("schema", {})
                        p_type = p_schema.get("type", "string") if isinstance(p_schema, dict) else "string"
                        p_req = p.get("required", p_in == "path")
                        p_default = p_schema.get("default") if isinstance(p_schema, dict) else None
                        p_desc = p.get("description")
                        p_enums = p_schema.get("enum") if isinstance(p_schema, dict) else None

                        constraints: Dict[str, Any] = {}
                        if isinstance(p_schema, dict):
                            for ck in ["minimum", "maximum", "minLength", "maxLength", "pattern"]:
                                if ck in p_schema:
                                    constraints[ck] = p_schema[ck]

                        parameters.append(
                            ParameterDoc(
                                name=p_name,
                                in_location=p_in,
                                param_type=p_type,
                                required=p_req,
                                default=p_default,
                                constraints=constraints,
                                enum_values=p_enums,
                                description=p_desc,
                                is_inferred=False,
                                provenance="explicit_openapi",
                            )
                        )

                # Request Body
                request_body: Optional[RequestBodyDoc] = None
                raw_req_body = op.get("requestBody")
                if isinstance(raw_req_body, dict):
                    content = raw_req_body.get("content", {})
                    content_type = "application/json" if "application/json" in content else (next(iter(content.keys())) if content else "application/json")
                    schema_obj = content.get(content_type, {}).get("schema", {}) if isinstance(content, dict) else {}
                    schema_name, fields = self._resolve_schema_fields(schema_obj, schemas)

                    request_body = RequestBodyDoc(
                        content_type=content_type,
                        schema_name=schema_name,
                        required=raw_req_body.get("required", True),
                        fields=fields,
                        description=raw_req_body.get("description"),
                        is_inferred=False,
                        provenance="explicit_openapi",
                    )

                # Responses
                responses: List[ResponseDoc] = []
                raw_responses = op.get("responses", {})
                if isinstance(raw_responses, dict):
                    for code_str, resp_val in raw_responses.items():
                        try:
                            status_code = int(code_str)
                        except ValueError:
                            status_code = 200

                        r_desc = resp_val.get("description") if isinstance(resp_val, dict) else None
                        r_fields: List[FieldDoc] = []
                        r_schema_name = None

                        if isinstance(resp_val, dict) and "content" in resp_val:
                            r_content = resp_val.get("content", {})
                            if isinstance(r_content, dict):
                                c_type = "application/json" if "application/json" in r_content else next(iter(r_content.keys()), None)
                                if c_type:
                                    schema_obj = r_content.get(c_type, {}).get("schema", {})
                                    r_schema_name, r_fields = self._resolve_schema_fields(schema_obj, schemas)

                        responses.append(
                            ResponseDoc(
                                status_code=status_code,
                                description=r_desc,
                                schema_name=r_schema_name,
                                fields=r_fields,
                                is_inferred=False,
                                provenance="explicit_openapi",
                            )
                        )

                # Auth & Security
                security = op.get("security", spec.get("security", []))
                auth_desc = None
                if security and isinstance(security, list) and len(security) > 0:
                    auth_schemes = []
                    for s in security:
                        if isinstance(s, dict):
                            auth_schemes.extend(list(s.keys()))
                    if auth_schemes:
                        auth_desc = f"Secured: {', '.join(auth_schemes)}"

                ep = EndpointDoc(
                    http_method=method,
                    route_path=normalized_path,
                    summary=summary,
                    description=description,
                    parameters=parameters,
                    request_body=request_body,
                    responses=responses,
                    auth_and_authz=auth_desc,
                    auth_inferred=False,
                    source_file=file_path,
                    discovery_method="openapi_spec",
                    evidence_source=f"openapi_specification ({file_path})",
                    confidence_level=1.0,
                    is_inferred=False,
                )
                self.openapi_endpoints.append(ep)

    def _resolve_schema_fields(self, schema_obj: Dict[str, Any], schemas_catalog: Dict[str, Any]) -> Tuple[Optional[str], List[FieldDoc]]:
        """Resolve schema properties and referenced definitions recursively."""
        if not isinstance(schema_obj, dict):
            return None, []

        schema_name = None
        # Handle $ref
        ref = schema_obj.get("$ref")
        if ref and isinstance(ref, str):
            ref_name = ref.split("/")[-1]
            schema_name = ref_name
            if ref_name in schemas_catalog:
                schema_obj = schemas_catalog[ref_name]

        fields: List[FieldDoc] = []
        properties = schema_obj.get("properties", {})
        required_list = schema_obj.get("required", [])

        if isinstance(properties, dict):
            for f_name, f_def in properties.items():
                if isinstance(f_def, dict):
                    f_type = f_def.get("type", "string")
                    f_desc = f_def.get("description")
                    f_default = f_def.get("default")
                    f_enums = f_def.get("enum")
                    constraints: Dict[str, Any] = {}
                    for ck in ["minimum", "maximum", "minLength", "maxLength", "pattern"]:
                        if ck in f_def:
                            constraints[ck] = f_def[ck]

                    fields.append(
                        FieldDoc(
                            name=f_name,
                            field_type=f_type,
                            required=f_name in required_list,
                            default=f_default,
                            constraints=constraints,
                            enum_values=f_enums,
                            description=f_desc,
                            is_inferred=False,
                            provenance="explicit_openapi",
                        )
                    )

        return schema_name, fields

    # =========================================================================
    # SOURCE CODE FRAMEWORK AST PARSER (FastAPI, Flask, Express)
    # =========================================================================

    def _scan_source_code_frameworks(self) -> None:
        """Scan source files using framework-specific AST parsers."""
        # Step A: Collect all Pydantic model definitions in Python files first
        self._collect_all_pydantic_models()

        # Step B: Walk files and parse endpoints
        for root, _, files in safe_walk(self.repo_root, output_dir=self.output_dir):
            for f in files:
                file_path = Path(root) / f
                rel_path = str(file_path.relative_to(self.repo_root))
                ext = file_path.suffix.lower()

                if ext == ".py":
                    self._parse_python_file(file_path, rel_path)
                elif ext in {".js", ".ts", ".jsx", ".tsx"}:
                    self._parse_javascript_file(file_path, rel_path)

    def _collect_all_pydantic_models(self) -> None:
        """Parse all Python files to extract Pydantic BaseModel definitions and their fields."""
        for root, _, files in safe_walk(self.repo_root, output_dir=self.output_dir):
            for f in files:
                if f.endswith(".py"):
                    p = Path(root) / f
                    rel_path = str(p.relative_to(self.repo_root))
                    try:
                        content = p.read_text(encoding="utf-8", errors="replace")
                        tree = ast.parse(content)
                        self._extract_pydantic_classes(tree, rel_path)
                    except Exception:
                        pass

    def _extract_pydantic_classes(self, tree: ast.AST, file_path: str) -> None:
        """Extract Pydantic model classes and field specifications."""
        models: Dict[str, Dict[str, Any]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if inherits from BaseModel or Schema or Enum
                is_pydantic = any(
                    (isinstance(b, ast.Name) and "Model" in b.id) or
                    (isinstance(b, ast.Attribute) and b.attr == "BaseModel")
                    for b in node.bases
                )
                is_enum = any(
                    (isinstance(b, ast.Name) and "Enum" in b.id)
                    for b in node.bases
                )

                fields: List[FieldDoc] = []
                enum_values: List[str] = []

                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        f_name = item.target.id
                        f_type = self._ast_unparse_type(item.annotation)
                        f_default = None
                        f_desc = None
                        f_req = True
                        constraints: Dict[str, Any] = {}

                        # Check default value (Field(...) or value)
                        if item.value is not None:
                            f_req = False
                            if isinstance(item.value, ast.Call):
                                # Field(default=..., description=...)
                                for kw in item.value.keywords:
                                    if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                                        f_desc = str(kw.value.value)
                                    elif kw.arg == "default":
                                        if isinstance(kw.value, ast.Constant):
                                            f_default = kw.value.value
                                        elif isinstance(kw.value, ast.Constant) and kw.value.value is Ellipsis:
                                            f_req = True
                                    elif kw.arg in ["gt", "ge", "lt", "le", "min_length", "max_length", "pattern"]:
                                        if isinstance(kw.value, ast.Constant):
                                            constraints[kw.arg] = kw.value.value
                            elif isinstance(item.value, ast.Constant):
                                f_default = item.value.value
                                if f_default is Ellipsis:
                                    f_req = True

                        if "Optional" in f_type or "None" in f_type:
                            f_req = False

                        fields.append(
                            FieldDoc(
                                name=f_name,
                                field_type=f_type,
                                required=f_req,
                                default=f_default,
                                constraints=constraints,
                                description=f_desc,
                                is_inferred=False,
                                provenance="source_ast",
                            )
                        )
                    elif isinstance(item, ast.Assign) and is_enum:
                        for target in item.targets:
                            if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                                enum_values.append(str(item.value.value))

                models[node.name] = {
                    "fields": fields,
                    "is_enum": is_enum,
                    "enum_values": enum_values,
                }

        self.pydantic_models_by_file[file_path] = models

    def _ast_unparse_type(self, node: ast.AST) -> str:
        """Convert AST type annotation node to string type name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            val = self._ast_unparse_type(node.value)
            slice_val = self._ast_unparse_type(node.slice)
            return f"{val}[{slice_val}]"
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return f"{self._ast_unparse_type(node.left)} | {self._ast_unparse_type(node.right)}"
        return "Any"

    def _parse_python_file(self, file_path: Path, rel_path: str) -> None:
        """Parse Python source file for FastAPI, Starlette, and Flask routes."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except Exception:
            return

        # Check for router prefixes (e.g. router = APIRouter(prefix="/users"))
        router_prefixes: Dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                        call_func = node.value.func
                        func_name = call_func.id if isinstance(call_func, ast.Name) else (call_func.attr if isinstance(call_func, ast.Attribute) else "")
                        if "APIRouter" in func_name:
                            for kw in node.value.keywords:
                                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                                    router_prefixes[target.id] = str(kw.value.value)

        # Scan function definitions for route decorators
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._inspect_python_route_handler(node, rel_path, router_prefixes)

    def _inspect_python_route_handler(self, func_node: ast.FunctionDef, rel_path: str, router_prefixes: Dict[str, str]) -> None:
        """Inspect a Python function definition for FastAPI/Flask route decorators."""
        http_methods = {"get", "post", "put", "delete", "patch", "options", "head"}

        for decorator in func_node.decorator_list:
            method = None
            route_path = None
            prefix = ""
            status_code = 200
            response_model_name = None

            if isinstance(decorator, ast.Call):
                # @app.get("/path") or @router.post("/path", status_code=201)
                dec_func = decorator.func
                if isinstance(dec_func, ast.Attribute):
                    attr_name = dec_func.attr.lower()
                    owner_name = dec_func.value.id if isinstance(dec_func.value, ast.Name) else ""
                    prefix = router_prefixes.get(owner_name, "")

                    if attr_name in http_methods:
                        method = attr_name.upper()
                    elif attr_name in {"route", "api_route"}:
                        # Check methods kwarg
                        method = "GET"
                        for kw in decorator.keywords:
                            if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                                for elt in kw.value.elts:
                                    if isinstance(elt, ast.Constant):
                                        method = str(elt.value).upper()
                                        break

                    # Extract path from first argument
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        route_path = str(decorator.args[0].value)
                    elif decorator.keywords:
                        for kw in decorator.keywords:
                            if kw.arg in ["path", "rule"] and isinstance(kw.value, ast.Constant):
                                route_path = str(kw.value.value)
                                break

                    # Extract status_code & response_model
                    for kw in decorator.keywords:
                        if kw.arg == "status_code":
                            if isinstance(kw.value, ast.Constant):
                                status_code = int(kw.value.value)
                            elif isinstance(kw.value, ast.Attribute):
                                status_code = 201 if "201" in kw.value.attr or "CREATED" in kw.value.attr else 200
                        elif kw.arg == "response_model":
                            if isinstance(kw.value, ast.Name):
                                response_model_name = kw.value.id

            if method and route_path is not None:
                full_path = self._normalize_route_path(f"{prefix}{route_path}")

                # Extract parameters, body, auth, error cases, side effects
                params, req_body, auth_info = self._parse_fastapi_params(func_node, full_path, rel_path)
                responses = self._build_fastapi_responses(status_code, response_model_name, rel_path)
                error_cases = self._detect_ast_error_cases(func_node)
                side_effects = self._detect_ast_side_effects(func_node)

                # Extract docstring description
                docstring = ast.get_docstring(func_node)
                summary = docstring.split("\n\n")[0].strip() if docstring else None
                description = docstring.strip() if docstring else None

                # Find relevant dependencies used in function
                deps_used = self._find_function_dependencies(func_node)

                ep = EndpointDoc(
                    http_method=method,
                    route_path=full_path,
                    summary=summary,
                    description=description,
                    parameters=params,
                    request_body=req_body,
                    responses=responses,
                    auth_and_authz=auth_info,
                    auth_inferred=auth_info is not None,
                    error_cases=error_cases,
                    side_effects=side_effects,
                    source_file=rel_path,
                    line_number=func_node.lineno,
                    handler_function=func_node.name,
                    relevant_dependencies=deps_used,
                    discovery_method="framework_ast",
                    evidence_source=f"source_ast:fastapi_router ({rel_path}:{func_node.lineno})",
                    confidence_level=1.0,
                    is_inferred=False,
                )
                self.code_endpoints.append(ep)

    def _parse_fastapi_params(self, func_node: ast.FunctionDef, route_path: str, rel_path: str) -> Tuple[List[ParameterDoc], Optional[RequestBodyDoc], Optional[str]]:
        """Extract parameters, request body models, and authentication dependencies from function args."""
        parameters: List[ParameterDoc] = []
        request_body: Optional[RequestBodyDoc] = None
        auth_info: Optional[str] = None

        path_params_in_url = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", route_path))

        for arg in func_node.args.args:
            arg_name = arg.arg
            if arg_name in {"self", "cls", "request"}:
                continue

            param_type = "string"
            if arg.annotation:
                param_type = self._ast_unparse_type(arg.annotation)

            # Check if parameter represents an auth dependency
            is_auth = False
            is_body = False
            default_val = None
            required = True
            constraints: Dict[str, Any] = {}
            p_desc = None

            # Check defaults
            defaults = func_node.args.defaults
            arg_idx_from_end = len(func_node.args.args) - func_node.args.args.index(arg)
            if arg_idx_from_end <= len(defaults):
                default_node = defaults[-arg_idx_from_end]
                if isinstance(default_node, ast.Call):
                    call_name = default_node.func.id if isinstance(default_node.func, ast.Name) else (default_node.func.attr if isinstance(default_node.func, ast.Attribute) else "")
                    if call_name in {"Depends", "Security"}:
                        is_auth = True
                        dep_name = "Auth Dependency"
                        if default_node.args:
                            if isinstance(default_node.args[0], ast.Name):
                                dep_name = default_node.args[0].id
                        auth_info = f"Security: Depends({dep_name})"
                    elif call_name == "Body":
                        is_body = True
                    elif call_name in {"Query", "Path", "Header", "Cookie"}:
                        for kw in default_node.keywords:
                            if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                                p_desc = str(kw.value.value)
                            elif kw.arg in ["gt", "ge", "lt", "le", "min_length", "max_length"]:
                                if isinstance(kw.value, ast.Constant):
                                    constraints[kw.arg] = kw.value.value
                elif isinstance(default_node, ast.Constant):
                    default_val = default_node.value
                    if default_val is not Ellipsis:
                        required = False

            if is_auth:
                continue

            # Check if parameter type is a known Pydantic Model (Request Body)
            known_model = self._find_model_definition(param_type)
            if known_model or is_body:
                fields = known_model.get("fields", []) if known_model else []
                request_body = RequestBodyDoc(
                    content_type="application/json",
                    schema_name=param_type,
                    required=required,
                    fields=fields,
                    description=f"Request payload for {param_type}",
                    is_inferred=False,
                    provenance="source_ast",
                )
                continue

            # Determine parameter location
            if arg_name in path_params_in_url:
                in_loc = "path"
                required = True
            elif "header" in arg_name.lower():
                in_loc = "header"
            elif "cookie" in arg_name.lower():
                in_loc = "cookie"
            else:
                in_loc = "query"

            parameters.append(
                ParameterDoc(
                    name=arg_name,
                    in_location=in_loc,
                    param_type=param_type,
                    required=required,
                    default=default_val,
                    constraints=constraints,
                    description=p_desc,
                    is_inferred=False,
                    provenance="source_ast",
                )
            )

        return parameters, request_body, auth_info

    def _find_model_definition(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Look up a Pydantic model by name across scanned model catalog."""
        clean_name = model_name.split("[")[0].strip()
        for file_models in self.pydantic_models_by_file.values():
            if clean_name in file_models:
                return file_models[clean_name]
        return None

    def _build_fastapi_responses(self, status_code: int, model_name: Optional[str], rel_path: str) -> List[ResponseDoc]:
        """Build response documentation from status_code and response_model."""
        fields: List[FieldDoc] = []
        if model_name:
            model_def = self._find_model_definition(model_name)
            if model_def:
                fields = model_def.get("fields", [])

        desc = f"Successful response ({status_code})"
        return [
            ResponseDoc(
                status_code=status_code,
                description=desc,
                schema_name=model_name,
                fields=fields,
                is_inferred=False,
                provenance="source_ast",
            )
        ]

    def _detect_ast_error_cases(self, func_node: ast.FunctionDef) -> List[ErrorCaseDoc]:
        """Detect HTTP exceptions raised within handler function."""
        error_cases: List[ErrorCaseDoc] = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                exc_name = node.exc.func.id if isinstance(node.exc.func, ast.Name) else (node.exc.func.attr if isinstance(node.exc.func, ast.Attribute) else "")
                if "HTTPException" in exc_name:
                    sc = 400
                    cond = "Validation or business logic exception"
                    for kw in node.exc.keywords:
                        if kw.arg == "status_code" and isinstance(kw.value, ast.Constant):
                            try:
                                sc = int(kw.value.value)
                            except Exception:
                                pass
                        elif kw.arg == "detail" and isinstance(kw.value, ast.Constant):
                            cond = str(kw.value.value)

                    error_cases.append(
                        ErrorCaseDoc(status_code=sc, condition=cond, exception_type=exc_name)
                    )
        return error_cases

    def _detect_ast_side_effects(self, func_node: ast.FunctionDef) -> List[SideEffectDoc]:
        """Detect side effects (database writes, HTTP calls, queue events) in handler."""
        side_effects: List[SideEffectDoc] = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                call_repr = self._ast_call_repr(node).lower()
                if any(k in call_repr for k in [".commit", ".execute", ".add", "commit", "execute"]):
                    side_effects.append(
                        SideEffectDoc(
                            effect_type="database_write",
                            target="Database",
                            description="Persists changes or updates entity in database transaction",
                        )
                    )
                elif any(k in call_repr for k in ["httpx.post", "requests.post", "stripe."]):
                    side_effects.append(
                        SideEffectDoc(
                            effect_type="external_http",
                            target="External Service",
                            description=f"Dispatches outbound call: {call_repr[:60]}",
                        )
                    )
                elif any(k in call_repr for k in [".publish", "publish", "delay", "apply_async"]):
                    side_effects.append(
                        SideEffectDoc(
                            effect_type="message_publish",
                            target="Message Queue",
                            description="Publishes asynchronous event or task",
                        )
                    )
        return side_effects

    def _ast_call_repr(self, node: ast.Call) -> str:
        """Produce brief string representation of an AST call node."""
        if isinstance(node.func, ast.Attribute):
            val_name = node.func.value.id if isinstance(node.func.value, ast.Name) else ""
            return f"{val_name}.{node.func.attr}"
        elif isinstance(node.func, ast.Name):
            return node.func.id
        return "call()"

    def _find_function_dependencies(self, func_node: ast.FunctionDef) -> List[str]:
        """Identify package dependencies invoked within function."""
        deps: Set[str] = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Name) and node.id in {"db", "session", "httpx", "requests", "stripe", "redis", "boto3"}:
                deps.add(node.id)
        return sorted(list(deps))

    def _parse_javascript_file(self, file_path: Path, rel_path: str) -> None:
        """Parse JavaScript/TypeScript Express route patterns."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        express_pattern = re.compile(r"""(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]\s*,\s*(?:async\s*)?(?:\((.*?)\)|([a-zA-Z0-9_]+))""")

        for line_idx, line in enumerate(content.splitlines(), 1):
            # Check dynamic unresolved routes
            if "app[" in line or "router[" in line:
                self.unresolved_dynamic_routes.append(
                    UnsupportedItemDoc(
                        item_type="unresolved_dynamic_route",
                        file_path=rel_path,
                        line_number=line_idx,
                        reason="Dynamic HTTP method indexing on Express router or app object cannot be statically resolved.",
                        code_snippet=line.strip(),
                    )
                )

            m = express_pattern.search(line)
            if m:
                method = m.group(1).upper()
                raw_path = m.group(2)
                handler_name = m.group(4) or "anonymous_handler"
                full_path = self._normalize_route_path(raw_path)

                # Extract path parameters
                params: List[ParameterDoc] = []
                for p_match in re.findall(r"\{([a-zA-Z0-9_]+)\}", full_path):
                    params.append(
                        ParameterDoc(
                            name=p_match,
                            in_location="path",
                            param_type="string",
                            required=True,
                            is_inferred=False,
                            provenance="source_ast",
                        )
                    )

                # Detect auth middleware
                auth_info = None
                if any(auth_word in line.lower() for auth_word in ["authenticate", "verifytoken", "requireauth"]):
                    auth_info = "Security: Middleware auth token required"

                ep = EndpointDoc(
                    http_method=method,
                    route_path=full_path,
                    parameters=params,
                    responses=[ResponseDoc(status_code=200, description="OK response", is_inferred=True, provenance="inferred_default")],
                    auth_and_authz=auth_info,
                    auth_inferred=auth_info is not None,
                    source_file=rel_path,
                    line_number=line_idx,
                    handler_function=handler_name,
                    discovery_method="framework_ast",
                    evidence_source=f"source_regex:express_app ({rel_path}:{line_idx})",
                    confidence_level=0.95,
                    is_inferred=False,
                )
                self.code_endpoints.append(ep)

    # =========================================================================
    # RECONCILIATION & DISCREPANCY TRACKING
    # =========================================================================

    def _reconcile_endpoints(self) -> List[EndpointDoc]:
        """
        Reconcile source code endpoints and OpenAPI endpoints.
        Tracks:
        - Undocumented endpoints (in code, missing in OpenAPI)
        - Ghost endpoints (in OpenAPI, missing in code)
        - Merges complementary metadata for hybrid discovery
        """
        code_by_key: Dict[Tuple[str, str], EndpointDoc] = {
            (ep.http_method, ep.route_path): ep for ep in self.code_endpoints
        }
        spec_by_key: Dict[Tuple[str, str], EndpointDoc] = {
            (ep.http_method, ep.route_path): ep for ep in self.openapi_endpoints
        }

        reconciled: List[EndpointDoc] = []
        all_keys = set(code_by_key.keys()).union(set(spec_by_key.keys()))

        for key in sorted(list(all_keys)):
            method, path = key
            in_code = code_by_key.get(key)
            in_spec = spec_by_key.get(key)

            if in_code and in_spec:
                # Discovered in BOTH -> Hybrid
                merged = in_spec.model_copy(deep=True)
                merged.discovery_method = "hybrid"
                merged.evidence_source = f"hybrid_source_and_openapi ({in_code.source_file}:{in_code.line_number} & {in_spec.source_file})"
                merged.source_file = in_code.source_file
                merged.line_number = in_code.line_number
                merged.handler_function = in_code.handler_function
                merged.error_cases = in_code.error_cases
                merged.side_effects = in_code.side_effects
                merged.relevant_dependencies = in_code.relevant_dependencies
                merged.confidence_level = 1.0

                if not merged.auth_and_authz and in_code.auth_and_authz:
                    merged.auth_and_authz = in_code.auth_and_authz
                    merged.auth_inferred = in_code.auth_inferred

                if not merged.request_body and in_code.request_body:
                    merged.request_body = in_code.request_body

                # Merge parameters if code has extras
                spec_param_names = {p.name for p in merged.parameters}
                for cp in in_code.parameters:
                    if cp.name not in spec_param_names:
                        merged.parameters.append(cp)

                reconciled.append(merged)

            elif in_code and not in_spec:
                # Present in code only -> Undocumented Endpoint
                reconciled.append(in_code)
                if self.openapi_files_found:
                    self.discrepancies.append(
                        DiscrepancyDoc(
                            discrepancy_type="undocumented_endpoint",
                            endpoint_path=path,
                            method=method,
                            description=f"Endpoint {method} {path} is implemented in {in_code.source_file}:{in_code.line_number} but is not documented in any OpenAPI specification.",
                            code_evidence=f"Handler {in_code.handler_function} at {in_code.source_file}:{in_code.line_number}",
                            spec_evidence="Missing from OpenAPI paths",
                        )
                    )

            elif in_spec and not in_code:
                # Present in OpenAPI only -> Ghost / Missing Endpoint
                reconciled.append(in_spec)
                self.discrepancies.append(
                    DiscrepancyDoc(
                        discrepancy_type="ghost_endpoint",
                        endpoint_path=path,
                        method=method,
                        description=f"Endpoint {method} {path} is documented in OpenAPI ({in_spec.source_file}) but was not found implemented in source code routes.",
                        code_evidence="No matching route handler found in source AST",
                        spec_evidence=f"Documented in {in_spec.source_file}",
                    )
                )

        return reconciled
