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
        """Request candidate repair from local Ollama model."""
        prompt = (
            f"You are an automated code repair assistant for Dependency Guardian.\n"
            f"An external API has introduced a breaking change or schema drift:\n"
            f"- Rule: {finding_info.get('rule_id')}\n"
            f"- Path: {finding_info.get('path')}\n"
            f"- Message: {finding_info.get('message')}\n"
            f"- Evidence: {finding_info.get('evidence')}\n\n"
            f"Here is the affected application code snippet:\n"
            f"```python\n{relevant_snippet or original_code[:1000]}\n```\n\n"
            f"Here is the complete source file:\n"
            f"```python\n{original_code}\n```\n\n"
            f"Instructions:\n"
            f"1. Fix the affected code to be backwards-compatible or adapt to the new contract schema.\n"
            f"2. Return the COMPLETE repaired source file contents only.\n"
            f"3. Do not include introductory or explanatory conversational text. Output only the code.\n"
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert software engineer fixing API contract drift. Output only the repaired Python code, without markdown explanation.",
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
                return cleaned if cleaned.strip() else None

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
