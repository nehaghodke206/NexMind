import ast
import logging
import re
from typing import Any, Dict, Optional
import httpx
from .settings import get_settings, normalize_ollama_url

logger = logging.getLogger("repair_agent.ollama_client")


class OllamaRepairClient:
    """Minimal client for local Ollama code repair inference."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        shared = get_settings()
        self.base_url = normalize_ollama_url(base_url or shared.ollama_base_url)
        self.model = model or shared.ollama_model
        self.timeout = timeout if timeout is not None else shared.ollama_timeout_seconds

    def is_available(self) -> bool:
        """Check if local Ollama daemon is reachable and model is available."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    # Check if selected model or prefix is in models
                    return any(self.model in m or m.startswith(self.model.split(":")[0]) for m in models)
        except Exception as exc:
            logger.debug(f"Ollama is_available check failed: {exc}")
        return False

    def generate_repair(
        self,
        finding_info: Dict[str, Any],
        original_code: str,
        relevant_snippet: Optional[str] = None,
    ) -> Optional[str]:
        """Request candidate repair from local Ollama model with AST syntax validation."""
        prompt = (
            "You are an automated code repair assistant for Dependency Guardian.\n"
            "An external API has introduced a breaking change or schema drift:\n"
            f"- Rule: {finding_info.get('rule_id')}\n"
            f"- Path: {finding_info.get('path')}\n"
            f"- Message: {finding_info.get('message')}\n"
            f"- Evidence: {finding_info.get('evidence')}\n\n"
            "Here is the affected application code snippet:\n"
            f"```python\n{relevant_snippet or original_code[:1000]}\n```\n\n"
            "Here is the complete source file:\n"
            f"```python\n{original_code}\n```\n\n"
            "Instructions:\n"
            "1. Fix the affected code to be backwards-compatible or adapt to the new contract schema.\n"
            "2. Preserve all existing function signatures, indentation, and imports.\n"
            "3. Enclose the COMPLETE repaired source file contents in a single ```python ... ``` markdown code block.\n"
            "4. Do NOT include introductory, conversational, or explanatory text outside the code block.\n"
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an expert Python software engineer fixing API contract drift. "
                                "Return strictly the complete valid Python source file enclosed in ```python ... ```."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.1},
                }
                res = client.post(f"{self.base_url}/api/chat", json=payload)
                if res.status_code != 200:
                    logger.warning(f"Ollama returned status {res.status_code}: {res.text}")
                    return None

                raw_content = res.json().get("message", {}).get("content", "")
                cleaned = self._clean_code_fence(raw_content)

                if not cleaned or not cleaned.strip():
                    logger.warning("Ollama response contained empty code content.")
                    return None

                if cleaned.strip() == original_code.strip():
                    logger.info("Ollama produced code identical to original without modification.")
                    return None

                # Validate AST syntax before returning
                try:
                    ast.parse(cleaned)
                except SyntaxError as syn_err:
                    logger.warning(
                        f"Ollama candidate repair failed AST syntax validation at line {syn_err.lineno}: {syn_err.msg}"
                    )
                    return None
                except Exception as parse_err:
                    logger.warning(f"Ollama candidate repair failed AST parsing: {parse_err}")
                    return None

                return cleaned

        except httpx.TimeoutException:
            logger.warning(f"Ollama repair generation timed out after {self.timeout}s.")
            return None
        except Exception as exc:
            logger.warning(f"Ollama repair generation failed: {exc}")
            return None

    def _clean_code_fence(self, text: str) -> str:
        """Extract code from markdown code fences if present."""
        text = text.strip()
        match = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            if len(lines) >= 2:
                return "\n".join(lines[1:-1]).strip()
        return text
