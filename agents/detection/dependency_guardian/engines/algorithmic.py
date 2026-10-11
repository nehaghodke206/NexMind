import copy
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from ..contracts.findings import (
    CompatibilityClassification,
    DetectionSource,
    Finding,
    RuleId,
    SeverityLevel,
)
from .base import BaseDetectionEngine

logger = logging.getLogger("dependency_guardian.engines.algorithmic")

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}


class AlgorithmicDetectionEngine(BaseDetectionEngine):
    """
    Deterministic specification comparator for OpenAPI 3.0.x, 3.1.x, and Swagger 2.0.
    Operates strictly offline without external dependencies or language models.
    """

    def detect(
        self,
        baseline_spec: Dict[str, Any],
        current_spec: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        """Compare baseline and current OpenAPI specifications deterministically."""
        findings: List[Finding] = []

        if not isinstance(baseline_spec, dict) or not isinstance(current_spec, dict):
            logger.warning("One or both specifications are not valid dictionaries.")
            return findings

        # Resolve internal references if present
        resolved_base = self._resolve_all_refs(baseline_spec)
        resolved_curr = self._resolve_all_refs(current_spec)

        base_paths_raw = resolved_base.get("paths") if isinstance(resolved_base, dict) else None
        curr_paths_raw = resolved_curr.get("paths") if isinstance(resolved_curr, dict) else None
        base_paths: Dict[str, Any] = base_paths_raw if isinstance(base_paths_raw, dict) else {}
        curr_paths: Dict[str, Any] = curr_paths_raw if isinstance(curr_paths_raw, dict) else {}

        # 1. Path removals
        for path, base_path_item in base_paths.items():
            if not isinstance(base_path_item, dict):
                continue
            if path not in curr_paths:
                methods = [m.upper() for m in base_path_item.keys() if m.lower() in HTTP_METHODS]
                rule = RuleId.PATH_REMOVED.value
                fingerprint = Finding.generate_fingerprint(path, None, f"paths.{path}", rule)
                findings.append(
                    Finding(
                        rule_id=rule,
                        fingerprint=fingerprint,
                        compatibility=CompatibilityClassification.BREAKING,
                        severity=SeverityLevel.HIGH,
                        path=path,
                        method=None,
                        schema_location=f"paths.{path}",
                        previous_value={"methods": methods},
                        current_value=None,
                        message=f"API path '{path}' was removed from the specification.",
                        evidence={"removed_path": path, "previous_methods": methods},
                        confidence=1.0,
                        source=DetectionSource.ALGORITHMIC,
                        review_required=False,
                    )
                )
                continue

            curr_path_item = curr_paths.get(path)
            if not isinstance(curr_path_item, dict):
                continue

            # 2. Method-level comparison
            self._compare_path_methods(path, base_path_item, curr_path_item, findings)

        # Sort findings deterministically
        findings.sort(key=lambda f: (f.path, f.method or "", f.schema_location, f.rule_id))
        return findings

    def _compare_path_methods(
        self,
        path: str,
        base_item: Dict[str, Any],
        curr_item: Dict[str, Any],
        findings: List[Finding],
    ) -> None:
        base_methods = {k.lower(): v for k, v in base_item.items() if k.lower() in HTTP_METHODS and isinstance(v, dict)}
        curr_methods = {k.lower(): v for k, v in curr_item.items() if k.lower() in HTTP_METHODS and isinstance(v, dict)}

        for method, base_op in base_methods.items():
            if method not in curr_methods:
                rule = RuleId.METHOD_REMOVED.value
                loc = f"paths.{path}.{method}"
                fingerprint = Finding.generate_fingerprint(path, method.upper(), loc, rule)
                findings.append(
                    Finding(
                        rule_id=rule,
                        fingerprint=fingerprint,
                        compatibility=CompatibilityClassification.BREAKING,
                        severity=SeverityLevel.HIGH,
                        path=path,
                        method=method.upper(),
                        schema_location=loc,
                        previous_value={"operationId": base_op.get("operationId")},
                        current_value=None,
                        message=f"HTTP method '{method.upper()}' was removed from path '{path}'.",
                        evidence={"path": path, "removed_method": method.upper()},
                        confidence=1.0,
                        source=DetectionSource.ALGORITHMIC,
                        review_required=False,
                    )
                )
                continue

            curr_op = curr_methods[method]

            # 3. Parameters comparison
            self._compare_parameters(path, method, base_op, curr_op, findings)

            # 4. Request Body comparison
            self._compare_request_body(path, method, base_op, curr_op, findings)

            # 5. Responses comparison
            self._compare_responses(path, method, base_op, curr_op, findings)

    def _compare_parameters(
        self,
        path: str,
        method: str,
        base_op: Dict[str, Any],
        curr_op: Dict[str, Any],
        findings: List[Finding],
    ) -> None:
        base_params = {
            (p.get("name"), p.get("in")): p
            for p in base_op.get("parameters", [])
            if isinstance(p, dict) and p.get("name") and p.get("in")
        }
        curr_params = {
            (p.get("name"), p.get("in")): p
            for p in curr_op.get("parameters", [])
            if isinstance(p, dict) and p.get("name") and p.get("in")
        }

        # Check for newly required or added optional parameters in current
        for (name, param_in), curr_p in curr_params.items():
            is_curr_req = bool(curr_p.get("required", False))
            if is_curr_req:
                base_p = base_params.get((name, param_in))
                if base_p is None or not base_p.get("required", False):
                    # Newly required parameter
                    rule = RuleId.REQUIRED_PARAM_ADDED.value
                    loc = f"paths.{path}.{method}.parameters.{name}"
                    fingerprint = Finding.generate_fingerprint(path, method.upper(), loc, rule)
                    findings.append(
                        Finding(
                            rule_id=rule,
                            fingerprint=fingerprint,
                            compatibility=CompatibilityClassification.BREAKING,
                            severity=SeverityLevel.HIGH,
                            path=path,
                            method=method.upper(),
                            schema_location=loc,
                            previous_value={"required": base_p.get("required") if base_p else None},
                            current_value={"required": True},
                            message=f"Newly required {param_in} parameter '{name}' was added to {method.upper()} {path}.",
                            evidence={
                                "parameter_name": name,
                                "in": param_in,
                                "required": True,
                                "previously_present": base_p is not None,
                            },
                            confidence=1.0,
                            source=DetectionSource.ALGORITHMIC,
                            review_required=False,
                        )
                    )
            else:
                if (name, param_in) not in base_params:
                    # New optional parameter added
                    rule = RuleId.FIELD_ADDED_OPTIONAL.value
                    loc = f"paths.{path}.{method}.parameters.{name}"
                    fingerprint = Finding.generate_fingerprint(path, method.upper(), loc, rule)
                    findings.append(
                        Finding(
                            rule_id=rule,
                            fingerprint=fingerprint,
                            compatibility=CompatibilityClassification.NON_BREAKING,
                            severity=SeverityLevel.LOW,
                            path=path,
                            method=method.upper(),
                            schema_location=loc,
                            previous_value=None,
                            current_value=curr_p,
                            message=f"New optional {param_in} parameter '{name}' was added to {method.upper()} {path}.",
                            evidence={
                                "parameter_name": name,
                                "in": param_in,
                                "required": False,
                            },
                            confidence=1.0,
                            source=DetectionSource.ALGORITHMIC,
                            review_required=False,
                        )
                    )

        # Check existing parameters for incompatible type changes
        for (name, param_in), base_p in base_params.items():
            if (name, param_in) in curr_params:
                curr_p = curr_params[(name, param_in)]
                base_type = self._extract_param_type(base_p)
                curr_type = self._extract_param_type(curr_p)
                if base_type and curr_type and base_type != curr_type:
                    rule = RuleId.FIELD_TYPE_CHANGED.value
                    loc = f"paths.{path}.{method}.parameters.{name}.type"
                    fingerprint = Finding.generate_fingerprint(path, method.upper(), loc, rule)
                    findings.append(
                        Finding(
                            rule_id=rule,
                            fingerprint=fingerprint,
                            compatibility=CompatibilityClassification.BREAKING,
                            severity=SeverityLevel.HIGH,
                            path=path,
                            method=method.upper(),
                            schema_location=loc,
                            previous_value=base_type,
                            current_value=curr_type,
                            message=f"Type of {param_in} parameter '{name}' changed incompatibly from '{base_type}' to '{curr_type}'.",
                            evidence={
                                "parameter_name": name,
                                "in": param_in,
                                "previous_type": base_type,
                                "current_type": curr_type,
                            },
                            confidence=1.0,
                            source=DetectionSource.ALGORITHMIC,
                            review_required=False,
                        )
                    )

    def _extract_param_type(self, param: Dict[str, Any]) -> Optional[str]:
        if "schema" in param and isinstance(param["schema"], dict):
            return param["schema"].get("type")
        return param.get("type")

    def _compare_request_body(
        self,
        path: str,
        method: str,
        base_op: Dict[str, Any],
        curr_op: Dict[str, Any],
        findings: List[Finding],
    ) -> None:
        base_rb = base_op.get("requestBody") or {}
        curr_rb = curr_op.get("requestBody") or {}

        base_req = bool(base_rb.get("required", False)) if isinstance(base_rb, dict) else False
        curr_req = bool(curr_rb.get("required", False)) if isinstance(curr_rb, dict) else False

        if curr_req and not base_req:
            rule = RuleId.REQUIRED_FIELD_ADDED.value
            loc = f"paths.{path}.{method}.requestBody.required"
            fingerprint = Finding.generate_fingerprint(path, method.upper(), loc, rule)
            findings.append(
                Finding(
                    rule_id=rule,
                    fingerprint=fingerprint,
                    compatibility=CompatibilityClassification.BREAKING,
                    severity=SeverityLevel.HIGH,
                    path=path,
                    method=method.upper(),
                    schema_location=loc,
                    previous_value={"required": base_req},
                    current_value={"required": True},
                    message=f"Request body for {method.upper()} {path} is now required.",
                    evidence={"previous_required": base_req, "current_required": True},
                    confidence=1.0,
                    source=DetectionSource.ALGORITHMIC,
                    review_required=False,
                )
            )

        # Compare request body schema properties (JSON)
        base_schema = self._extract_media_schema(base_rb)
        curr_schema = self._extract_media_schema(curr_rb)
        if base_schema and curr_schema:
            loc_prefix = f"paths.{path}.{method}.requestBody.content.application/json.schema"
            self._compare_schemas(
                path=path,
                method=method.upper(),
                location_prefix=loc_prefix,
                base_schema=base_schema,
                curr_schema=curr_schema,
                is_request=True,
                findings=findings,
            )

    def _compare_responses(
        self,
        path: str,
        method: str,
        base_op: Dict[str, Any],
        curr_op: Dict[str, Any],
        findings: List[Finding],
    ) -> None:
        base_responses = base_op.get("responses") or {}
        curr_responses = curr_op.get("responses") or {}

        if not isinstance(base_responses, dict) or not isinstance(curr_responses, dict):
            return

        for status_code, base_resp in base_responses.items():
            str_code = str(status_code)
            loc = f"paths.{path}.{method}.responses.{str_code}"
            if str_code not in curr_responses:
                # Removed response status code
                is_success = str_code.startswith("2") or str_code == "default"
                compat = CompatibilityClassification.BREAKING if is_success else CompatibilityClassification.POTENTIALLY_BREAKING
                sev = SeverityLevel.HIGH if is_success else SeverityLevel.MEDIUM
                rule = RuleId.STATUS_CODE_REMOVED.value
                fingerprint = Finding.generate_fingerprint(path, method.upper(), loc, rule)
                findings.append(
                    Finding(
                        rule_id=rule,
                        fingerprint=fingerprint,
                        compatibility=compat,
                        severity=sev,
                        path=path,
                        method=method.upper(),
                        schema_location=loc,
                        previous_value={"status_code": str_code},
                        current_value=None,
                        message=f"Documented response status code '{str_code}' was removed from {method.upper()} {path}.",
                        evidence={"removed_status_code": str_code, "is_success": is_success},
                        confidence=1.0,
                        source=DetectionSource.ALGORITHMIC,
                        review_required=not is_success,
                    )
                )
                continue

            curr_resp = curr_responses[str_code]
            base_schema = self._extract_response_schema(base_resp)
            curr_schema = self._extract_response_schema(curr_resp)

            if base_schema and curr_schema:
                schema_loc = f"{loc}.content.application/json.schema"
                self._compare_schemas(
                    path=path,
                    method=method.upper(),
                    location_prefix=schema_loc,
                    base_schema=base_schema,
                    curr_schema=curr_schema,
                    is_request=False,
                    findings=findings,
                )

    def _extract_media_schema(self, body_obj: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(body_obj, dict):
            return None
        content = body_obj.get("content")
        if isinstance(content, dict):
            for media in ("application/json", "*/*"):
                if media in content and isinstance(content[media], dict):
                    schema = content[media].get("schema")
                    if isinstance(schema, dict):
                        return schema
            for m, obj in content.items():
                if isinstance(obj, dict) and "schema" in obj and isinstance(obj["schema"], dict):
                    return obj["schema"]
        schema = body_obj.get("schema")
        if isinstance(schema, dict):
            return schema
        return None

    def _extract_response_schema(self, resp_obj: Any) -> Optional[Dict[str, Any]]:
        return self._extract_media_schema(resp_obj)

    def _compare_schemas(
        self,
        path: str,
        method: str,
        location_prefix: str,
        base_schema: Dict[str, Any],
        curr_schema: Dict[str, Any],
        is_request: bool,
        findings: List[Finding],
    ) -> None:
        """Deep comparison of schemas: types, properties, enums, required fields, arrays."""
        base_type = base_schema.get("type")
        curr_type = curr_schema.get("type")

        # Incompatible type change
        if base_type and curr_type and base_type != curr_type:
            rule = RuleId.FIELD_TYPE_CHANGED.value
            loc = f"{location_prefix}.type"
            fingerprint = Finding.generate_fingerprint(path, method, loc, rule)
            findings.append(
                Finding(
                    rule_id=rule,
                    fingerprint=fingerprint,
                    compatibility=CompatibilityClassification.BREAKING,
                    severity=SeverityLevel.HIGH,
                    path=path,
                    method=method,
                    schema_location=loc,
                    previous_value=base_type,
                    current_value=curr_type,
                    message=f"Schema type changed incompatibly from '{base_type}' to '{curr_type}' at {location_prefix}.",
                    evidence={
                        "previous_type": base_type,
                        "current_type": curr_type,
                        "is_request": is_request,
                    },
                    confidence=1.0,
                    source=DetectionSource.ALGORITHMIC,
                    review_required=False,
                )
            )
            return

        # Enum comparison
        base_enum = base_schema.get("enum")
        curr_enum = curr_schema.get("enum")
        if isinstance(base_enum, list) and isinstance(curr_enum, list):
            base_set = set(str(e) for e in base_enum)
            curr_set = set(str(e) for e in curr_enum)
            removed = sorted(list(base_set - curr_set))
            if removed:
                rule = RuleId.ENUM_VALUE_REMOVED.value
                loc = f"{location_prefix}.enum"
                fingerprint = Finding.generate_fingerprint(path, method, loc, rule)
                compat = CompatibilityClassification.BREAKING if is_request else CompatibilityClassification.POTENTIALLY_BREAKING
                findings.append(
                    Finding(
                        rule_id=rule,
                        fingerprint=fingerprint,
                        compatibility=compat,
                        severity=SeverityLevel.MEDIUM,
                        path=path,
                        method=method,
                        schema_location=loc,
                        previous_value=base_enum,
                        current_value=curr_enum,
                        message=f"Enum values removed at {loc}: {removed}.",
                        evidence={"removed_values": removed, "is_request": is_request},
                        confidence=1.0,
                        source=DetectionSource.ALGORITHMIC,
                        review_required=not is_request,
                    )
                )

        # Object properties
        base_props = base_schema.get("properties") or {}
        curr_props = curr_schema.get("properties") or {}

        if isinstance(base_props, dict) and isinstance(curr_props, dict):
            # Check removed properties
            for prop_name, base_p in base_props.items():
                if not isinstance(base_p, dict):
                    continue
                loc = f"{location_prefix}.properties.{prop_name}"
                if prop_name not in curr_props:
                    if not is_request:
                        rule = RuleId.RESPONSE_FIELD_REMOVED.value
                        compat = CompatibilityClassification.BREAKING
                        sev = SeverityLevel.HIGH
                        msg = f"Property '{prop_name}' was removed from response schema at {loc}."
                        rev_req = False
                    else:
                        rule = RuleId.REQUEST_FIELD_REMOVED.value
                        compat = CompatibilityClassification.POTENTIALLY_BREAKING
                        sev = SeverityLevel.MEDIUM
                        msg = f"Property '{prop_name}' was removed from request schema at {loc}."
                        rev_req = True

                    fingerprint = Finding.generate_fingerprint(path, method, loc, rule)
                    findings.append(
                        Finding(
                            rule_id=rule,
                            fingerprint=fingerprint,
                            compatibility=compat,
                            severity=sev,
                            path=path,
                            method=method,
                            schema_location=loc,
                            previous_value=base_p,
                            current_value=None,
                            message=msg,
                            evidence={
                                "removed_property": prop_name,
                                "previous_definition": base_p,
                                "is_request": is_request,
                            },
                            confidence=1.0,
                            source=DetectionSource.ALGORITHMIC,
                            review_required=rev_req,
                        )
                    )
                else:
                    # Recursively compare child property
                    curr_p = curr_props[prop_name]
                    if isinstance(curr_p, dict):
                        self._compare_schemas(
                            path=path,
                            method=method,
                            location_prefix=loc,
                            base_schema=base_p,
                            curr_schema=curr_p,
                            is_request=is_request,
                            findings=findings,
                        )

            # Check newly added properties
            for prop_name, curr_p in curr_props.items():
                if not isinstance(curr_p, dict):
                    continue
                if prop_name not in base_props:
                    loc = f"{location_prefix}.properties.{prop_name}"
                    rule = RuleId.FIELD_ADDED_OPTIONAL.value
                    fingerprint = Finding.generate_fingerprint(path, method, loc, rule)
                    findings.append(
                        Finding(
                            rule_id=rule,
                            fingerprint=fingerprint,
                            compatibility=CompatibilityClassification.NON_BREAKING,
                            severity=SeverityLevel.LOW,
                            path=path,
                            method=method,
                            schema_location=loc,
                            previous_value=None,
                            current_value=curr_p,
                            message=f"New optional field '{prop_name}' was added at {loc}.",
                            evidence={
                                "added_property": prop_name,
                                "current_definition": curr_p,
                                "is_request": is_request,
                            },
                            confidence=1.0,
                            source=DetectionSource.ALGORITHMIC,
                            review_required=False,
                        )
                    )

        # Required fields list
        base_req = set(base_schema.get("required") or [])
        curr_req = set(curr_schema.get("required") or [])

        # Newly required field
        newly_req = sorted(list(curr_req - base_req))
        if newly_req and is_request:
            for field in newly_req:
                rule = RuleId.REQUIRED_FIELD_ADDED.value
                loc = f"{location_prefix}.required.{field}"
                fingerprint = Finding.generate_fingerprint(path, method, loc, rule)
                findings.append(
                    Finding(
                        rule_id=rule,
                        fingerprint=fingerprint,
                        compatibility=CompatibilityClassification.BREAKING,
                        severity=SeverityLevel.HIGH,
                        path=path,
                        method=method,
                        schema_location=loc,
                        previous_value=False,
                        current_value=True,
                        message=f"Field '{field}' is newly required in request payload at {location_prefix}.",
                        evidence={"field": field, "required": True},
                        confidence=1.0,
                        source=DetectionSource.ALGORITHMIC,
                        review_required=False,
                    )
                )

        # Array items recursion
        if base_type == "array" or curr_type == "array":
            base_items = base_schema.get("items")
            curr_items = curr_schema.get("items")
            if isinstance(base_items, dict) and isinstance(curr_items, dict):
                self._compare_schemas(
                    path=path,
                    method=method,
                    location_prefix=f"{location_prefix}.items",
                    base_schema=base_items,
                    curr_schema=curr_items,
                    is_request=is_request,
                    findings=findings,
                )

    def _resolve_all_refs(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Deep copy and resolve internal $ref within specification, guarding against cycles."""
        cloned = copy.deepcopy(spec)
        active_refs: Set[str] = set()

        def _resolve_node(node: Any) -> Any:
            if not isinstance(node, dict):
                if isinstance(node, list):
                    return [_resolve_node(item) for item in node]
                return node

            if "$ref" in node and isinstance(node["$ref"], str):
                ref = node["$ref"]
                if ref in active_refs:
                    # Circular reference cycle detected; return node without recursive expansion
                    return {k: v for k, v in node.items()}

                active_refs.add(ref)
                try:
                    resolved = self._lookup_ref(cloned, ref)
                    if resolved is not None and isinstance(resolved, dict):
                        resolved_copy = copy.deepcopy(resolved)
                        for k, v in node.items():
                            if k != "$ref":
                                resolved_copy[k] = v
                        return _resolve_node(resolved_copy)
                finally:
                    active_refs.remove(ref)

            return {k: _resolve_node(v) for k, v in node.items()}

        return _resolve_node(cloned)

    def _lookup_ref(self, root: Dict[str, Any], ref: str) -> Optional[Any]:
        if not ref.startswith("#/"):
            return None
        parts = ref[2:].split("/")
        curr = root
        for p in parts:
            p = p.replace("~1", "/").replace("~0", "~")
            if isinstance(curr, dict) and p in curr:
                curr = curr[p]
            else:
                return None
        return curr
