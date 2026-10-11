import json
import logging
import os
from typing import Any, Dict, List, Optional
import httpx

from ..contracts.findings import (
    CompatibilityClassification,
    DetectionSource,
    Finding,
    RuleId,
    SeverityLevel,
)
from .base import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    AIInvalidOutputError,
    AIProviderError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    BaseAIProvider,
)

logger = logging.getLogger("dependency_guardian.providers.ollama")


class OllamaProvider(BaseAIProvider):
    """
    Local Ollama AI provider for Dependency Guardian.
    Connects to local Ollama HTTP API (default: http://localhost:11434).
    Operates strictly locally with zero external network transmission.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_input_bytes: int = 500_000,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        configured_model = model_name or os.getenv("DEPENDENCY_GUARDIAN_AI_MODEL")
        env_timeout = os.getenv("DEPENDENCY_GUARDIAN_AI_TIMEOUT_SECONDS")
        effective_timeout = timeout_seconds if timeout_seconds is not None else (
            float(env_timeout) if env_timeout else 60.0
        )
        super().__init__(
            model_name=configured_model or "default",
            timeout_seconds=effective_timeout,
            max_input_bytes=max_input_bytes,
        )
        raw_url = base_url or os.getenv("DEPENDENCY_GUARDIAN_AI_BASE_URL") or "http://localhost:11434"
        self.base_url = raw_url.rstrip("/")
        self._transport = transport
        self._resolved_model_name: Optional[str] = None

    def _get_client(self, timeout: Optional[float] = None) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            timeout=timeout or self.timeout_seconds,
            transport=self._transport,
        )

    def is_available(self) -> bool:
        """
        Check if Ollama server is running locally on base_url.
        Uses lightweight GET /api/tags without triggering model loading.
        """
        try:
            with self._get_client(timeout=2.0) as client:
                resp = client.get("/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """Diagnostic health inspection of the Ollama endpoint and model availability."""
        status: Dict[str, Any] = {
            "reachable": False,
            "base_url": self.base_url,
            "installed_models": [],
            "selected_model": self.model_name,
            "model_available": False,
            "error": None,
        }
        try:
            with self._get_client(timeout=3.0) as client:
                resp = client.get("/api/tags")
                if resp.status_code != 200:
                    status["error"] = f"Endpoint responded with HTTP {resp.status_code}"
                    return status

                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                status["reachable"] = True
                status["installed_models"] = models

                try:
                    resolved = self._resolve_model(models)
                    status["selected_model"] = resolved
                    status["model_available"] = True
                except AIProviderUnavailableError as err:
                    status["error"] = str(err)
        except httpx.ConnectError:
            status["error"] = f"Connection refused to {self.base_url}. Ensure Ollama service is running locally."
        except httpx.TimeoutException:
            status["error"] = f"Timed out connecting to {self.base_url}"
        except Exception as exc:
            status["error"] = f"Failed to query Ollama: {exc}"
        return status

    def _resolve_model(self, installed_models: List[str]) -> str:
        """Resolve target model from installed models or raise actionable error."""
        if self._resolved_model_name and self._resolved_model_name in installed_models:
            return self._resolved_model_name

        if not installed_models:
            raise AIProviderUnavailableError(
                f"Ollama at {self.base_url} has no models installed. "
                "Download a model first with: ollama pull qwen2.5-coder:3b"
            )

        # If user explicitly requested a specific model (and not 'default')
        if self.model_name and self.model_name.lower() != "default":
            target = self.model_name.lower()
            for m in installed_models:
                m_lower = m.lower()
                if (
                    m_lower == target
                    or m_lower.startswith(f"{target}:")
                    or target.startswith(f"{m_lower.split(':')[0]}:")
                ):
                    self._resolved_model_name = m
                    return m

            raise AIProviderUnavailableError(
                f"Configured model '{self.model_name}' is not installed in Ollama. "
                f"Installed models: {installed_models}. "
                f"Run 'ollama pull {self.model_name}' to install it."
            )

        # Auto-detection: prefer qwen2.5-coder:3b or first available model
        for preferred in ("qwen2.5-coder:3b", "qwen2.5-coder", "llama3", "codellama", "mistral"):
            for m in installed_models:
                if preferred in m.lower():
                    self._resolved_model_name = m
                    return m

        self._resolved_model_name = installed_models[0]
        return self._resolved_model_name

    def _call_chat(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        num_predict: int = 350,
    ) -> str:
        """Execute chat completion request against local Ollama API."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic output
                "num_predict": num_predict,
            },
        }

        try:
            with self._get_client() as client:
                resp = client.post("/api/chat", json=payload)
                if resp.status_code == 404:
                    raise AIProviderUnavailableError(
                        f"Model '{model}' not found in Ollama. Run 'ollama pull {model}'"
                    )
                elif resp.status_code != 200:
                    raise AIProviderError(
                        f"Ollama returned HTTP {resp.status_code}: {resp.text[:300]}"
                    )

                data = resp.json()
                msg = data.get("message", {})
                content = msg.get("content", "")
                if not content:
                    raise AIInvalidOutputError("Ollama response contained empty content")
                return content
        except httpx.ConnectError as exc:
            raise AIProviderUnavailableError(
                f"Failed to connect to Ollama at {self.base_url}. Ensure Ollama is running locally: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise AIProviderTimeoutError(
                f"Ollama inference timed out after {self.timeout_seconds}s for model '{model}'"
            ) from exc
        except (AIProviderError, AIProviderUnavailableError, AIProviderTimeoutError, AIInvalidOutputError):
            raise
        except Exception as exc:
            raise AIProviderError(f"Unexpected error calling Ollama: {exc}") from exc

    @staticmethod
    def _clean_and_parse_json(content: str) -> Dict[str, Any]:
        """Strip markdown code fence if present and parse JSON."""
        text = content.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        return json.loads(text)

    def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Execute AI analysis using local Ollama model.
        Supports both Hybrid enrichment and Pure AI detection modes.
        """
        # Fetch installed models and resolve model
        try:
            with self._get_client(timeout=3.0) as client:
                tags_resp = client.get("/api/tags")
                if tags_resp.status_code != 200:
                    raise AIProviderUnavailableError(
                        f"Ollama endpoint {self.base_url} returned HTTP {tags_resp.status_code}"
                    )
                installed = [m.get("name", "") for m in tags_resp.json().get("models", [])]
        except httpx.ConnectError as exc:
            raise AIProviderUnavailableError(
                f"Ollama server at {self.base_url} is unreachable. Ensure Ollama is running: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise AIProviderTimeoutError(f"Timed out querying Ollama tags at {self.base_url}: {exc}") from exc

        model = self._resolve_model(installed)

        if request.algorithmic_findings:
            return self._analyze_hybrid(request, model)
        else:
            return self._analyze_pure_ai(request, model)

    def _analyze_hybrid(self, request: AIAnalysisRequest, model: str) -> AIAnalysisResponse:
        """Enrich existing deterministic findings with AI reasoning, remediation, and test suggestions."""
        # Sort breaking findings first for prioritized enrichment
        sorted_findings = sorted(
            request.algorithmic_findings,
            key=lambda f: (0 if f.compatibility == CompatibilityClassification.BREAKING else 1)
        )

        findings_summary = []
        for f in sorted_findings[:2]:
            findings_summary.append({
                "fingerprint": f.fingerprint,
                "rule_id": f.rule_id,
                "path": f.path,
                "method": f.method or "*",
                "compatibility": f.compatibility.value,
                "message": f.message,
            })

        system_prompt = (
            "You are Dependency Guardian AI, an expert API reliability engineer. "
            "Analyze the provided API contract changes. Keep explanations concise (1 sentence each). "
            "Return ONLY a JSON object with this exact structure:\n"
            "{\n"
            '  "summary": "1-sentence executive overview of contract evolution",\n'
            '  "enriched_findings": [\n'
            "    {\n"
            '      "fingerprint": "<matching fingerprint>",\n'
            '      "reasoning": "<1-sentence technical reason why this impacts callers>",\n'
            '      "remediation": "<1-sentence actionable fix or migration step>",\n'
            '      "test_suggestion": "<1-sentence regression test scenario>"\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Provide impact analysis and remediation for these {len(findings_summary)} key contract changes:\n"
            f"{json.dumps(findings_summary, indent=2)}\n"
        )

        content = self._call_chat(user_prompt, system_prompt, model, num_predict=300)
        try:
            parsed = self._clean_and_parse_json(content)
        except json.JSONDecodeError as exc:
            raise AIInvalidOutputError(f"Ollama output was not valid JSON: {exc}\nRaw output: {content[:300]}") from exc

        enrichment_map: Dict[str, Dict[str, str]] = {}
        for item in parsed.get("enriched_findings", []):
            if isinstance(item, dict) and "fingerprint" in item:
                enrichment_map[item["fingerprint"]] = {
                    "reasoning": item.get("reasoning", ""),
                    "remediation": item.get("remediation", ""),
                    "test_suggestion": item.get("test_suggestion", ""),
                }

        out_findings: List[Finding] = []
        for f in request.algorithmic_findings:
            f_copy = f.model_copy(deep=True)
            if f.fingerprint in enrichment_map:
                enr = enrichment_map[f.fingerprint]
                f_copy.ai_reasoning = enr["reasoning"] or f_copy.message
                if enr.get("remediation"):
                    f_copy.evidence["remediation"] = enr["remediation"]
                if enr.get("test_suggestion"):
                    f_copy.evidence["test_suggestion"] = enr["test_suggestion"]
            else:
                f_copy.ai_reasoning = f_copy.message
                if f.compatibility == CompatibilityClassification.BREAKING:
                    f_copy.evidence["remediation"] = f"Update consumer integration to conform with changed contract at {f.path}."
                    f_copy.evidence["test_suggestion"] = f"Assert request to {f.method or 'GET'} {f.path} validates backward compatibility."
            out_findings.append(f_copy)

        return AIAnalysisResponse(
            findings=out_findings,
            model_name=model,
            reasoning_summary=parsed.get("summary", "Hybrid AI reasoning completed successfully."),
            raw_response=content,
        )

    def _analyze_pure_ai(self, request: AIAnalysisRequest, model: str) -> AIAnalysisResponse:
        """
        Pure AI mode: Ollama analyzes contract changes directly from OpenAPI specifications.
        Grounded strictly in paths and schemas present in baseline and current specs.
        """
        base_paths = list((request.baseline_spec.get("paths") or {}).keys())
        curr_paths = list((request.current_spec.get("paths") or {}).keys())
        all_valid_paths = set(base_paths + curr_paths)

        spec_summary = {
            "baseline_title": request.baseline_spec.get("info", {}).get("title"),
            "baseline_version": request.baseline_spec.get("info", {}).get("version"),
            "baseline_paths": {p: list(ops.keys()) for p, ops in (request.baseline_spec.get("paths") or {}).items() if isinstance(ops, dict)},
            "current_title": request.current_spec.get("info", {}).get("title"),
            "current_version": request.current_spec.get("info", {}).get("version"),
            "current_paths": {p: list(ops.keys()) for p, ops in (request.current_spec.get("paths") or {}).items() if isinstance(ops, dict)},
            "baseline_components": list((request.baseline_spec.get("components", {}).get("schemas") or {}).keys()),
            "current_components": list((request.current_spec.get("components", {}).get("schemas") or {}).keys()),
        }

        system_prompt = (
            "You are Dependency Guardian AI, a strict API contract analyzer. "
            "Compare the baseline and current OpenAPI specifications to detect breaking and non-breaking contract changes. "
            "CRITICAL: You MUST ONLY reference endpoints and paths that actually exist in the provided specifications. "
            "DO NOT invent non-existent paths. "
            "Return ONLY a JSON object with this structure:\n"
            "{\n"
            '  "summary": "Executive overview of changes",\n'
            '  "findings": [\n'
            "    {\n"
            '      "rule_id": "<RULE-PATH-REMOVED | RULE-METHOD-REMOVED | RULE-REQUIRED-PARAM-ADDED | RULE-REQUIRED-FIELD-ADDED | RULE-ENUM-VALUE-REMOVED | RULE-FIELD-TYPE-CHANGED | RULE-RESPONSE-FIELD-REMOVED | RULE-FIELD-ADDED-OPTIONAL>",\n'
            '      "compatibility": "<breaking | potentially_breaking | non_breaking | unknown>",\n'
            '      "severity": "<critical | high | medium | low>",\n'
            '      "path": "<exact path from the specification, e.g. /api/v1/products>",\n'
            '      "method": "<GET | POST | PUT | DELETE | null>",\n'
            '      "schema_location": "<paths./path.method or schema key>",\n'
            '      "message": "<clear description of what changed>",\n'
            '      "ai_reasoning": "<why this breaks or affects callers>",\n'
            '      "evidence": {"remediation": "...", "test_suggestion": "..."}\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Compare these two API versions and find breaking and non-breaking changes:\n"
            f"{json.dumps(spec_summary, indent=2)}\n"
        )

        content = self._call_chat(user_prompt, system_prompt, model, num_predict=800)
        try:
            parsed = self._clean_and_parse_json(content)
        except json.JSONDecodeError as exc:
            raise AIInvalidOutputError(f"Ollama output was not valid JSON: {exc}\nRaw output: {content[:300]}") from exc

        raw_findings = parsed.get("findings", [])
        validated_findings: List[Finding] = []

        for item in raw_findings:
            if not isinstance(item, dict):
                continue
            path = item.get("path", "")
            # Grounding check: reject hallucinated paths unsupported by specifications
            if path and path not in all_valid_paths and not any(p in path for p in all_valid_paths):
                logger.warning("Rejecting unsupported/hallucinated endpoint '%s' generated by AI", path)
                continue

            method = item.get("method")
            if method:
                method = method.upper()
            rule_id = item.get("rule_id", RuleId.UNKNOWN_CHANGE.value)
            loc = item.get("schema_location", f"paths.{path}")
            compat_str = item.get("compatibility", "breaking")
            try:
                compat = CompatibilityClassification(compat_str.lower())
            except ValueError:
                compat = CompatibilityClassification.UNKNOWN

            sev_str = item.get("severity", "high")
            try:
                sev = SeverityLevel(sev_str.lower())
            except ValueError:
                sev = SeverityLevel.MEDIUM

            fingerprint = Finding.generate_fingerprint(path, method, loc, rule_id)
            ev = item.get("evidence", {})
            if not isinstance(ev, dict):
                ev = {}

            f = Finding(
                rule_id=rule_id,
                fingerprint=fingerprint,
                compatibility=compat,
                severity=sev,
                path=path,
                method=method,
                schema_location=loc,
                previous_value=item.get("previous_value"),
                current_value=item.get("current_value"),
                message=item.get("message", f"Change detected at {path}"),
                evidence=ev,
                confidence=0.85,
                source=DetectionSource.AI,
                review_required=compat == CompatibilityClassification.BREAKING,
                ai_reasoning=item.get("ai_reasoning"),
            )
            validated_findings.append(f)

        return AIAnalysisResponse(
            findings=validated_findings,
            model_name=model,
            reasoning_summary=parsed.get("summary", "Pure AI analysis completed successfully."),
            raw_response=content,
        )

    def generate_risk_insights(
        self,
        findings: List[Finding],
        baseline_spec: Dict[str, Any],
        current_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate comprehensive AI risk insights, consumer impact, remediation,
        and regression testing advice from detection findings.
        """
        installed = []
        try:
            with self._get_client(timeout=3.0) as client:
                resp = client.get("/api/tags")
                if resp.status_code == 200:
                    installed = [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception:
            pass

        model = self._resolve_model(installed) if installed else self.model_name or "qwen2.5-coder:3b"

        breaking_list = [
            f"- [{f.rule_id}] {f.method or '*'} {f.path}: {f.message}"
            for f in findings if f.compatibility == CompatibilityClassification.BREAKING
        ]
        non_breaking_list = [
            f"- [{f.rule_id}] {f.method or '*'} {f.path}: {f.message}"
            for f in findings if f.compatibility == CompatibilityClassification.NON_BREAKING
        ]

        system_prompt = (
            "You are Dependency Guardian AI Risk Advisor. Keep each field very concise (1-2 sentences). "
            "Return ONLY a JSON object with this exact structure:\n"
            "{\n"
            '  "executive_summary": "1-sentence summary of risks and contract changes",\n'
            '  "consumer_impact_analysis": "1-sentence explanation of which consumers break and why",\n'
            '  "top_breaking_changes": ["list of top breaking changes"],\n'
            '  "recommended_fixes": ["step-by-step remediation actions"],\n'
            '  "recommended_order_of_resolution": ["recommended order to address changes"],\n'
            '  "recommended_regression_tests": ["recommended test scenarios to safeguard consumers"],\n'
            '  "assumptions_and_limitations": "Explicit uncertainty regarding consumer implementation",\n'
            '  "facts_extracted_from_openapi": ["concrete factual changes extracted from contracts"],\n'
            '  "ai_generated_hypotheses": ["AI hypotheses regarding consumer impact"]\n'
            "}"
        )

        user_prompt = (
            f"Baseline API: {baseline_spec.get('info', {}).get('title', 'API')} v{baseline_spec.get('info', {}).get('version', '1')}\n"
            f"Current API: {current_spec.get('info', {}).get('title', 'API')} v{current_spec.get('info', {}).get('version', '2')}\n"
            f"Breaking changes ({len(breaking_list)}):\n" + "\n".join(breaking_list[:2]) + "\n\n"
            f"Non-breaking changes ({len(non_breaking_list)}):\n" + "\n".join(non_breaking_list[:1]) + "\n"
        )

        try:
            content = self._call_chat(user_prompt, system_prompt, model, num_predict=500)
            parsed = self._clean_and_parse_json(content)
            parsed["model"] = model
            parsed["provider"] = "ollama"
            # Ensure facts list is populated if missing
            if not parsed.get("facts_extracted_from_openapi"):
                parsed["facts_extracted_from_openapi"] = breaking_list[:5] + non_breaking_list[:3]
            return parsed
        except Exception as exc:
            logger.warning("Failed to generate AI risk insights from Ollama: %s", exc)
            return {
                "model": model,
                "provider": "ollama",
                "executive_summary": "AI risk insights generation unavailable due to local inference status.",
                "consumer_impact_analysis": f"Ollama generation encountered: {exc}",
                "top_breaking_changes": breaking_list[:5],
                "recommended_fixes": ["Review breaking contract changes and update client integration code."],
                "recommended_order_of_resolution": ["1. Address removed endpoints.", "2. Update required payload fields."],
                "recommended_regression_tests": ["Verify client requests with old payloads fail gracefully with 4xx."],
                "assumptions_and_limitations": "Deterministic algorithmic findings preserved.",
                "facts_extracted_from_openapi": breaking_list + non_breaking_list,
                "ai_generated_hypotheses": [],
                "error": str(exc),
            }
