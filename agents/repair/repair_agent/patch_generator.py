import difflib
import logging
from pathlib import Path
import re
from typing import Optional, Tuple

from .inspector import InspectionResult
from .models import FindingInput
from .ollama_client import OllamaRepairClient

logger = logging.getLogger("repair_agent.patch_generator")


class PatchResult:
    def __init__(self, proposed_content: str, diff: str, strategy: str, explanation: str):
        self.proposed_content = proposed_content
        self.diff = diff
        self.strategy = strategy
        self.explanation = explanation


class PatchGenerator:
    """Generates candidate source code patches and unified diffs."""

    def __init__(self, ollama_client: Optional[OllamaRepairClient] = None):
        self.ollama_client = ollama_client

    def generate(
        self,
        finding: FindingInput,
        inspection: InspectionResult,
        preferred_provider: str = "deterministic",
        assessment: Optional[Any] = None,
    ) -> PatchResult:
        """Produce a proposed patch using AI or deterministic rules."""
        original = inspection.content

        # 1. Try local Ollama if requested
        if preferred_provider == "ollama" and self.ollama_client and self.ollama_client.is_available():
            finding_dict = finding.model_dump()
            ai_proposal = self.ollama_client.generate_repair(
                finding_info=finding_dict,
                original_code=original,
                relevant_snippet=inspection.snippet,
            )
            if ai_proposal and ai_proposal.strip() != original.strip():
                diff = self._create_unified_diff(original, ai_proposal, inspection.file_path)
                return PatchResult(
                    proposed_content=ai_proposal,
                    diff=diff,
                    strategy="ollama",
                    explanation=f"AI-generated candidate patch via local Ollama ({self.ollama_client.model}) for {finding.rule_id}.",
                )
            logger.info("Ollama did not produce a differentiated patch. Falling back to deterministic engine.")

        # 2. Deterministic rule-based patch synthesis
        proposed, explanation = self._generate_deterministic(finding, inspection, assessment=assessment)
        diff = self._create_unified_diff(original, proposed, inspection.file_path)

        strategy = "fallback" if preferred_provider == "ollama" else "deterministic"
        return PatchResult(
            proposed_content=proposed,
            diff=diff,
            strategy=strategy,
            explanation=explanation,
        )

    def _generate_deterministic(
        self,
        finding: FindingInput,
        inspection: InspectionResult,
        assessment: Optional[Any] = None,
    ) -> Tuple[str, str]:
        """Apply deterministic compatibility adapter patterns."""
        content = inspection.content
        ev = finding.evidence or {}
        rule = finding.rule_id

        # Strategy 1: Renamed or Removed Field (e.g. RULE-RESPONSE-FIELD-REMOVED or rename candidate)
        removed_prop = ev.get("removed_property") or ev.get("renamed_from")
        renamed_to = ev.get("renamed_to")

        if not removed_prop and finding.schema_location:
            parts = finding.schema_location.split(".")
            if parts and len(parts) > 1 and parts[-2] == "properties":
                removed_prop = parts[-1]

        if removed_prop:
            default_style = (
                assessment.convention_details.get("default_style")
                if (assessment and hasattr(assessment, "convention_details"))
                else "standard"
            )
            if renamed_to:
                # Rename adapter: data.get("renamed_to", data.get("removed_prop"))
                if default_style == "none":
                    replacement = rf'\1.get("{renamed_to}", \1.get("{removed_prop}", None))'
                elif default_style == "empty_str":
                    replacement = rf'\1.get("{renamed_to}", \1.get("{removed_prop}", ""))'
                else:
                    replacement = rf'\1.get("{renamed_to}", \1.get("{removed_prop}"))'

                # Match either item["name"] or item.get("name")
                pattern = rf'([a-zA-Z0-9_]+)(?:\[[\'"]{re.escape(removed_prop)}[\'"]\]|\.get\([\'"]{re.escape(removed_prop)}[\'"]\))'
                new_content = re.sub(pattern, replacement, content)

                if new_content != content:
                    return (
                        new_content,
                        f"Introduced backwards-compatible field adapter resolving '{renamed_to}' with fallback to '{removed_prop}'.",
                    )
            else:
                # Removed property fallback: item["stock"] -> item.get("stock", default)
                if default_style == "none":
                    replacement = rf'\1.get("{removed_prop}", None)'
                elif default_style == "empty_str":
                    replacement = rf'\1.get("{removed_prop}", "")'
                else:
                    replacement = rf'\1.get("{removed_prop}", 0)'

                pattern = rf'([a-zA-Z0-9_]+)(?:\[[\'"]{re.escape(removed_prop)}[\'"]\]|\.get\([\'"]{re.escape(removed_prop)}[\'"]\))'
                new_content = re.sub(pattern, replacement, content)

                if new_content != content:
                    return (
                        new_content,
                        f"Safe dictionary access adapter added with default fallback for removed field '{removed_prop}'.",
                    )

        # Strategy 2: Field Type Changed (e.g., number -> string)
        if "TYPE-CHANGED" in rule or "type" in ev:
            prop_name = ev.get("property") or removed_prop
            prev_type = ev.get("previous_type") or finding.previous_value
            curr_type = ev.get("current_type") or finding.current_value

            if prev_type in ["number", "integer", "float", "int"] and curr_type in ["string", "str"]:
                # The upstream API now sends a string where code expected a number
                # Convert: item["amount"] -> float(item.get("amount", 0))
                if prop_name:
                    pattern = rf'([a-zA-Z0-9_]+)\[[\'"]{re.escape(prop_name)}[\'"]\]'
                    replacement = rf'float(\1.get("{prop_name}", 0))'
                    new_content = re.sub(pattern, replacement, content)
                    if new_content != content:
                        return (
                            new_content,
                            f"Type coercion adapter converting string field '{prop_name}' to float.",
                        )

            elif prev_type in ["string", "str"] and curr_type in ["number", "integer"]:
                if prop_name:
                    pattern = rf'([a-zA-Z0-9_]+)\[[\'"]{re.escape(prop_name)}[\'"]\]'
                    replacement = rf'str(\1.get("{prop_name}", ""))'
                    new_content = re.sub(pattern, replacement, content)
                    if new_content != content:
                        return (
                            new_content,
                            f"Type coercion adapter converting numeric field '{prop_name}' to string.",
                        )

        # Strategy 3: Required parameter added (e.g., store_id added to GET /products)
        param_name = ev.get("parameter_name") or ev.get("added_property")
        if param_name and ("PARAM-ADDED" in rule or "FIELD-ADDED" in rule):
            # Look for client request calls: requests.get(url, ...) or client.get(url, ...)
            # Add parameter to params dict if present
            if "params=" in content:
                pattern = r'params=\{([^}]+)\}'
                replacement = rf'params={{\1, "{param_name}": "default"}}'
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    return (
                        new_content,
                        f"Added newly required parameter '{param_name}' to outbound request params dictionary.",
                    )

        # Fallback: Comment annotation adapter if no automated code transform matched
        lines = content.splitlines()
        annotated_lines = []
        injected = False
        for line in lines:
            annotated_lines.append(line)
            if not injected and finding.path and finding.path in line:
                annotated_lines.append(
                    f"    # TODO(DependencyGuardian): Adapt to {finding.rule_id} on {finding.path}"
                )
                injected = True

        if injected:
            return (
                "\n".join(annotated_lines) + ("\n" if content.endswith("\n") else ""),
                f"Injected review marker and compatibility warning for {finding.rule_id}.",
            )

        return (
            content,
            f"No automated deterministic transformation pattern matched for rule {rule}.",
        )

    def _create_unified_diff(self, original: str, proposed: str, file_path: Path) -> str:
        """Generate human-readable unified diff."""
        file_name = file_path.name
        orig_lines = original.splitlines(keepends=True)
        prop_lines = proposed.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                orig_lines,
                prop_lines,
                fromfile=f"a/{file_name}",
                tofile=f"b/{file_name}",
            )
        )
        return "".join(diff)
