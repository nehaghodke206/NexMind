import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .inspector import CodeInspector
from .models import (
    FindingInput,
    RepairRequest,
    RepairResult,
    RepairStatus,
    ValidationDetails,
    ValidationStatus,
)
from .ollama_client import OllamaRepairClient
from .patch_generator import PatchGenerator
from .reasoning import EngineeringReasoningLayer
from .validator import PatchValidator

logger = logging.getLogger("repair_agent.pipeline")


class RepairPipeline:
    """Minimal end-to-end repair pipeline for Dependency Guardian findings.

    Flow: Accept finding -> Inspect affected code -> Assess reasoning & conventions ->
          Generate proposed patch -> Validate patch in temporary copy -> Return structured repair result.
    """

    def __init__(
        self,
        inspector: Optional[CodeInspector] = None,
        patch_generator: Optional[PatchGenerator] = None,
        validator: Optional[PatchValidator] = None,
        ollama_client: Optional[OllamaRepairClient] = None,
        reasoning_layer: Optional[EngineeringReasoningLayer] = None,
    ):
        self.ollama_client = ollama_client or OllamaRepairClient()
        self.inspector = inspector or CodeInspector()
        self.patch_generator = patch_generator or PatchGenerator(ollama_client=self.ollama_client)
        self.validator = validator or PatchValidator()
        self.reasoning_layer = reasoning_layer or EngineeringReasoningLayer()

    def run(
        self,
        request_or_finding: Optional[Union[RepairRequest, FindingInput, Dict[str, Any]]] = None,
        **kwargs,
    ) -> RepairResult:
        """Execute the repair pipeline on a finding or request."""
        # 1. Parse and validate input finding
        request, parse_error = self._normalize_request(request_or_finding, **kwargs)
        if parse_error:
            return RepairResult(
                finding_id=request.finding.id if (request and request.finding) else "unknown",
                status=RepairStatus.ERROR,
                error_message=parse_error,
                requires_human_review=True,
            )

        finding = request.finding

        # Validate mandatory finding fields
        if not finding.id or not finding.rule_id or not finding.path:
            return RepairResult(
                finding_id=finding.id or "unknown",
                status=RepairStatus.ERROR,
                error_message="Invalid finding: 'id', 'rule_id', and 'path' are required fields.",
                requires_human_review=True,
            )

        # 2. Inspect affected code
        ws_dir = Path(request.workspace_dir) if request.workspace_dir else None
        inspector = CodeInspector(workspace_dir=ws_dir)
        try:
            inspection = inspector.inspect(finding, target_file=request.target_file)
        except Exception as exc:
            logger.error(f"Code inspection failed: {exc}")
            return RepairResult(
                finding_id=finding.id,
                status=RepairStatus.ERROR,
                error_message=f"Code inspection failed: {exc}",
                target_file=request.target_file,
                requires_human_review=True,
            )

        # 2.5. Engineering Reasoning Assessment
        assessment = self.reasoning_layer.assess(
            finding=finding,
            inspection=inspection,
            preferred_provider=request.provider,
        )

        if not assessment.sufficient_evidence:
            return RepairResult(
                finding_id=finding.id,
                status=RepairStatus.NEEDS_REVIEW,
                target_file=str(inspection.file_path),
                proposal_generated=False,
                original_content=inspection.content,
                proposed_content=None,
                diff="",
                strategy="engineering_reasoning",
                explanation=assessment.missing_evidence_reason or "Insufficient evidence to safely synthesize repair.",
                rationale=assessment.rationale,
                assumptions=assessment.assumptions,
                risks=assessment.risks,
                alternatives_considered=assessment.alternatives_considered,
                requires_human_review=True,
                human_approved=False,
                approval_status="pending",
                validation=ValidationDetails(
                    status=ValidationStatus.SKIPPED,
                    ast_valid=False,
                    test_executed=False,
                ),
            )

        # 3. Generate proposed patch
        try:
            generator = self.patch_generator
            if request.provider == "ollama" and (
                request.base_url != self.ollama_client.base_url
                or request.model != self.ollama_client.model
            ):
                dynamic_client = OllamaRepairClient(
                    base_url=request.base_url, model=request.model
                )
                generator = PatchGenerator(ollama_client=dynamic_client)

            patch_res = generator.generate(
                finding=finding,
                inspection=inspection,
                preferred_provider=request.provider,
                assessment=assessment,
            )
        except Exception as exc:
            logger.error(f"Patch generation failed: {exc}")
            return RepairResult(
                finding_id=finding.id,
                status=RepairStatus.ERROR,
                error_message=f"Patch generation failed: {exc}",
                target_file=str(inspection.file_path),
                proposal_generated=False,
                requires_human_review=True,
            )

        # Check if patch actually produced changes
        if not patch_res.diff.strip():
            return RepairResult(
                finding_id=finding.id,
                status=RepairStatus.REJECTED,
                target_file=str(inspection.file_path),
                proposal_generated=False,
                original_content=inspection.content,
                proposed_content=None,
                diff="",
                strategy=patch_res.strategy,
                explanation=patch_res.explanation,
                rationale=assessment.rationale,
                assumptions=assessment.assumptions,
                risks=assessment.risks,
                alternatives_considered=assessment.alternatives_considered,
                requires_human_review=True,
                human_approved=False,
                approval_status="pending",
                validation=ValidationDetails(
                    status=ValidationStatus.SKIPPED,
                    ast_valid=False,
                    test_executed=False,
                ),
            )

        # 4. Validate patch in temporary copy sandbox (NEVER touches original source file)
        val_details = self.validator.validate(
            target_file=inspection.file_path,
            proposed_content=patch_res.proposed_content,
            workspace_dir=ws_dir,
            test_command=request.test_command,
        )

        final_status = (
            RepairStatus.VALIDATED
            if val_details.status == ValidationStatus.SUCCESS
            else RepairStatus.VALIDATION_FAILED
        )

        # 5. Return structured repair result
        return RepairResult(
            finding_id=finding.id,
            status=final_status,
            target_file=str(inspection.file_path),
            proposal_generated=True,
            diff=patch_res.diff,
            original_content=inspection.content,
            proposed_content=patch_res.proposed_content,
            strategy=patch_res.strategy,
            explanation=patch_res.explanation,
            rationale=assessment.rationale,
            assumptions=assessment.assumptions,
            risks=assessment.risks,
            alternatives_considered=assessment.alternatives_considered,
            validation=val_details,
            requires_human_review=True,
            human_approved=False,
            approval_status="pending",
        )

    def _normalize_request(
        self,
        input_data: Optional[Union[RepairRequest, FindingInput, Dict[str, Any]]],
        **kwargs,
    ) -> tuple[Optional[RepairRequest], Optional[str]]:
        """Normalize varied inputs into a clean RepairRequest."""
        try:
            if input_data is None:
                if "finding" in kwargs:
                    input_data = kwargs.pop("finding")
                else:
                    return None, "Invalid finding: No finding input provided."

            if isinstance(input_data, RepairRequest):
                return input_data, None

            if isinstance(input_data, FindingInput):
                req = RepairRequest(finding=input_data, **kwargs)
                return req, None

            if isinstance(input_data, dict):
                # Check if dictionary is a RepairRequest or raw finding
                if "finding" in input_data and isinstance(input_data["finding"], dict):
                    req = RepairRequest.model_validate(input_data)
                    return req, None
                else:
                    try:
                        finding = FindingInput.model_validate(input_data)
                        req = RepairRequest(finding=finding, **kwargs)
                        return req, None
                    except Exception as err:
                        return None, f"Invalid finding data: {err}"

            return None, f"Unsupported input type for repair pipeline: {type(input_data)}"
        except Exception as exc:
            return None, f"Malformed finding input data: {exc}"
