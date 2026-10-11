"""Lightweight Engineering Reasoning Layer for Dependency Guardian Repair Agent.

Assesses intended behavior, nearby project conventions, evidence sufficiency,
and plausible competing repair approaches before patch synthesis.
"""

from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from .inspector import InspectionResult
from .models import FindingInput

logger = logging.getLogger("repair_agent.reasoning")


@dataclass
class ReasoningAssessment:
    """Outcome of engineering reasoning evaluation."""

    sufficient_evidence: bool
    missing_evidence_reason: Optional[str] = None
    intended_behavior: str = ""
    conventions_observed: List[str] = field(default_factory=list)
    alternatives_considered: List[str] = field(default_factory=list)
    chosen_approach: str = ""
    rationale: str = ""
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    is_low_risk_deterministic: bool = True
    convention_details: Dict[str, Any] = field(default_factory=dict)


class EngineeringReasoningLayer:
    """Evaluates findings and target code to guide safe, convention-aware repairs."""

    def assess(
        self,
        finding: FindingInput,
        inspection: InspectionResult,
        preferred_provider: str = "deterministic",
    ) -> ReasoningAssessment:
        content = inspection.content
        ev = finding.evidence or {}
        rule = finding.rule_id

        # -------------------------------------------------------------
        # 1. Evidence Sufficiency & Safety Gate
        # Never invent field meanings, fallback values, or business logic.
        # If evidence is insufficient, return needs_review.
        # -------------------------------------------------------------

        # Check A: Semantic uncertainty or explicit safety block
        if (
            ev.get("semantic_uncertainty") is True
            or ev.get("requires_domain_knowledge") is True
            or ev.get("insufficient_evidence") is True
            or finding.severity == "blocked"
            or finding.compatibility in {"blocked", "uncertain"}
            or "SEMANTIC-UNCERTAINTY" in rule
            or "UNCERTAINTY" in rule
        ):
            return ReasoningAssessment(
                sufficient_evidence=False,
                missing_evidence_reason=(
                    f"Finding '{finding.id}' involves semantic uncertainty in domain logic ({rule}). "
                    "Automated repair synthesis is strictly prohibited without developer domain knowledge "
                    "to prevent corrupting business state."
                ),
                rationale="Automated repair blocked due to semantic uncertainty in business domain logic.",
                assumptions=["Observed change alters domain semantics where automatic mapping is unsafe."],
                risks=["Corrupting business state, financial calculations, or payment verification logic."],
                alternatives_considered=[
                    "Block automatic repair and request human developer review (Chosen)",
                    "Speculative status mapping (Rejected: unsafe to invent domain logic)",
                ],
                chosen_approach="Block automatic repair and request human review",
                is_low_risk_deterministic=False,
            )

        # Check B: Field rename finding missing target field ('renamed_to')
        is_rename = (
            "RENAME" in rule
            or "renamed_from" in ev
            or ("renamed_to" in ev and "renamed_from" in ev)
        )
        if is_rename:
            renamed_to = ev.get("renamed_to")
            renamed_from = ev.get("renamed_from") or ev.get("removed_property")
            if not renamed_to:
                return ReasoningAssessment(
                    sufficient_evidence=False,
                    missing_evidence_reason=(
                        f"Field rename indicated for '{renamed_from or 'property'}', but evidence does not specify "
                        "the new target field name ('renamed_to'). Cannot synthesize patch without target field name."
                    ),
                    rationale="Insufficient evidence: Missing target attribute 'renamed_to'.",
                    assumptions=["Cannot guess the new field name without upstream contract specification."],
                    risks=["Injecting non-existent attribute access or guessing incorrect property names."],
                    alternatives_considered=[
                        "Return needs_review with explanation of missing field (Chosen)",
                        "Invent replacement property name (Rejected: violates safety principle)",
                    ],
                    chosen_approach="Return needs_review",
                    is_low_risk_deterministic=False,
                )

        # Check C: Type change missing type specifications
        if "TYPE-CHANGED" in rule or "type" in ev:
            prev_type = ev.get("previous_type") or finding.previous_value
            curr_type = ev.get("current_type") or finding.current_value
            if "TYPE-CHANGED" in rule and (not prev_type or not curr_type):
                return ReasoningAssessment(
                    sufficient_evidence=False,
                    missing_evidence_reason=(
                        "Type change detected, but source or target type definition is missing from finding evidence. "
                        "Cannot synthesize safe type coercion without explicit type metadata."
                    ),
                    rationale="Insufficient evidence: Missing previous_type or current_type.",
                    assumptions=["Type conversion requires known source and destination types."],
                    risks=["Attempting invalid type casts causing runtime TypeError or ValueError."],
                    alternatives_considered=[
                        "Return needs_review explaining missing type definition (Chosen)",
                        "Guess type coercion (Rejected: violates safety principle)",
                    ],
                    chosen_approach="Return needs_review",
                    is_low_risk_deterministic=False,
                )

        # Check D: Required parameter added missing parameter name
        if "PARAM-ADDED" in rule or "FIELD-ADDED" in rule:
            param_name = ev.get("parameter_name") or ev.get("added_property")
            if not param_name and not finding.schema_location:
                return ReasoningAssessment(
                    sufficient_evidence=False,
                    missing_evidence_reason=(
                        "Required parameter added according to rule, but parameter name is missing from finding evidence."
                    ),
                    rationale="Insufficient evidence: Missing parameter_name.",
                    assumptions=[],
                    risks=["Cannot construct request payload without parameter name."],
                    alternatives_considered=[
                        "Return needs_review (Chosen)",
                        "Guess parameter name (Rejected)",
                    ],
                    chosen_approach="Return needs_review",
                    is_low_risk_deterministic=False,
                )

        # Check E: Response field removed but missing property name and schema location
        if "RESPONSE-FIELD-REMOVED" in rule:
            removed_prop = ev.get("removed_property") or ev.get("renamed_from")
            if not removed_prop and finding.schema_location:
                parts = finding.schema_location.split(".")
                if parts and len(parts) > 1 and parts[-2] == "properties":
                    removed_prop = parts[-1]
            if not removed_prop:
                return ReasoningAssessment(
                    sufficient_evidence=False,
                    missing_evidence_reason=(
                        "Response property removal detected, but property name cannot be determined from evidence or schema."
                    ),
                    rationale="Insufficient evidence: Missing removed property name.",
                    assumptions=[],
                    risks=["Cannot identify which dictionary key was removed."],
                    alternatives_considered=["Return needs_review (Chosen)"],
                    chosen_approach="Return needs_review",
                    is_low_risk_deterministic=False,
                )

        # -------------------------------------------------------------
        # 2. Assess Nearby Project Conventions
        # -------------------------------------------------------------
        conventions_observed: List[str] = []
        convention_details: Dict[str, Any] = {}

        # Convention: Safe dictionary access style in nearby code
        has_explicit_none_get = bool(re.search(r'\.get\([\'"][a-zA-Z0-9_]+[\'"],\s*None\)', content))
        has_explicit_empty_get = bool(re.search(r'\.get\([\'"][a-zA-Z0-9_]+[\'"],\s*["\']\s*["\']\)', content))

        if has_explicit_none_get:
            conventions_observed.append("Observed nearby convention: .get(key, None) pattern for safe field extraction.")
            convention_details["default_style"] = "none"
        elif has_explicit_empty_get:
            conventions_observed.append("Observed nearby convention: .get(key, \"\") pattern for optional string fields.")
            convention_details["default_style"] = "empty_str"
        else:
            conventions_observed.append("Observed standard Python dictionary access convention.")
            convention_details["default_style"] = "standard"

        conventions_observed.append("Preserve PEP 8 formatting and expression-level localized scope.")

        # -------------------------------------------------------------
        # 3. Assess Intended Behavior & Competing Repair Approaches
        # -------------------------------------------------------------
        alternatives: List[str] = []
        assumptions: List[str] = []
        risks: List[str] = []
        intended_behavior: str = ""
        chosen_approach: str = ""
        rationale: str = ""

        if is_rename:
            renamed_from = ev.get("renamed_from") or ev.get("removed_property") or "field"
            renamed_to = ev.get("renamed_to") or "new_field"
            intended_behavior = (
                f"Extract attribute '{renamed_from}' from upstream API response, adapting to new "
                f"attribute '{renamed_to}' while retaining backwards compatibility."
            )
            alternatives = [
                f"Alternative 1 (Direct Key Swap): Replace '{renamed_from}' directly with '{renamed_to}'. (Risk: Breaks backward compatibility during phased deployment or canary rollouts).",
                f"Alternative 2 (Control-Flow Branching): Insert 'if \"{renamed_to}\" in data: ... else: ...' conditional block. (Risk: Introduces AST branching churn and cyclomatic complexity).",
                f"Alternative 3 (Backwards-Compatible Chained Expression): data.get(\"{renamed_to}\", data.get(\"{renamed_from}\")). (Chosen: Smallest maintainable fix preserving dual compatibility).",
            ]
            chosen_approach = f"Backwards-compatible chained get resolving '{renamed_to}' with fallback to '{renamed_from}'."
            rationale = (
                f"Chose the smallest maintainable fix supported by evidence: chained dictionary getter resolves '{renamed_to}' "
                f"while retaining compatibility for '{renamed_from}' during upstream rollout without altering control flow."
            )
            assumptions = [
                f"Upstream service is transitioning from '{renamed_from}' to '{renamed_to}'.",
                "Calling code tolerates None if neither attribute is supplied by upstream.",
            ]
            risks = [
                "Upstream payload may send null for the new field rather than omitting it; downstream code should handle potential None values.",
            ]

        elif "TYPE-CHANGED" in rule or "type" in ev:
            prop = ev.get("property") or ev.get("removed_property") or "value"
            prev_t = ev.get("previous_type") or finding.previous_value or "number"
            curr_t = ev.get("current_type") or finding.current_value or "string"
            intended_behavior = f"Perform operations on '{prop}' expecting type '{prev_t}', but upstream API now delivers '{curr_t}'."
            alternatives = [
                "Alternative 1 (Schema Validation Layer): Introduce external pydantic schema parsing wrapper. (Risk: High architectural invasiveness).",
                f"Alternative 2 (Inline Type Coercion): Coerce '{prop}' inline using {prev_t}(...). (Chosen: Smallest maintainable fix ensuring type contract holds).",
            ]
            chosen_approach = f"Inline type coercion converting upstream '{curr_t}' to expected '{prev_t}'."
            rationale = (
                f"Coerce upstream '{curr_t}' property '{prop}' to expected '{prev_t}' inline, preserving downstream calculation integrity "
                "with minimal code disruption."
            )
            assumptions = [
                f"Upstream string representation of '{prop}' is convertible to '{prev_t}'.",
            ]
            risks = [
                f"Potential ValueError if upstream transmits non-convertible characters in '{prop}'.",
            ]

        elif "RESPONSE-FIELD-REMOVED" in rule:
            removed_prop = ev.get("removed_property") or "removed_field"
            intended_behavior = f"Safely handle removal of property '{removed_prop}' from response payload."
            alternatives = [
                f"Alternative 1 (Delete Reference): Remove the statement referencing '{removed_prop}'. (Risk: Breaks downstream callers expecting this return key).",
                f"Alternative 2 (Safe Getter with Default): Replace direct subscript with .get('{removed_prop}', default). (Chosen: Smallest change avoiding KeyError).",
            ]
            chosen_approach = f"Safe dictionary access adapter with default fallback for '{removed_prop}'."
            rationale = f"Replaced direct subscript with safe .get() to prevent KeyError on removed field '{removed_prop}'."
            assumptions = [
                f"Default value for '{removed_prop}' satisfies downstream callers.",
            ]
            risks = [
                f"Callers depending on non-default values of '{removed_prop}' may receive default values.",
            ]

        elif "PARAM-ADDED" in rule or "FIELD-ADDED" in rule:
            param_name = ev.get("parameter_name") or ev.get("added_property") or "param"
            intended_behavior = f"Provide required parameter '{param_name}' in upstream request."
            alternatives = [
                f"Alternative 1 (Signature Modification): Alter function signature to require '{param_name}'. (Risk: Breaks existing callers of this function).",
                f"Alternative 2 (Default Query Parameter): Add '{param_name}': 'default' into request params dict. (Chosen: Satisfies API contract without caller churn).",
            ]
            chosen_approach = f"Inject default '{param_name}' parameter into request params dict."
            rationale = f"Supplied required parameter '{param_name}' with safe default to satisfy new upstream contract."
            assumptions = [
                f"Default parameter value for '{param_name}' is accepted by upstream endpoint.",
            ]
            risks = [
                f"Upstream may expect dynamic values for '{param_name}' rather than default.",
            ]

        else:
            intended_behavior = f"Adapt application code to API change: {finding.rule_id}."
            alternatives = ["Review marker annotation (Chosen)"]
            chosen_approach = "Inject review marker annotation"
            rationale = f"Injected developer review comment for {finding.rule_id} as no automated pattern matched."
            assumptions = ["Developer will manually adjust code according to review comment."]
            risks = ["Code does not automatically adapt to upstream schema change."]

        return ReasoningAssessment(
            sufficient_evidence=True,
            intended_behavior=intended_behavior,
            conventions_observed=conventions_observed,
            alternatives_considered=alternatives,
            chosen_approach=chosen_approach,
            rationale=rationale,
            assumptions=assumptions,
            risks=risks,
            is_low_risk_deterministic=True,
            convention_details=convention_details,
        )
