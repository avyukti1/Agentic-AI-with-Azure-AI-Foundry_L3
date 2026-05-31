import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


@dataclass
class ContentSafetyConfig:
    """Configuration needed to call Azure AI Content Safety."""

    endpoint: str
    key: str
    api_version: str = "2024-09-01"
    threshold: int = 4

    @classmethod
    def from_env(cls) -> Optional["ContentSafetyConfig"]:
        """Build config from .env values, or disable the feature if missing."""
        endpoint = os.getenv("CONTENT_SAFETY_ENDPOINT")
        key = os.getenv("CONTENT_SAFETY_KEY")

        # Keep the app runnable for demos even when Content Safety is not set up.
        if not endpoint or not key or _is_placeholder(endpoint) or _is_placeholder(key):
            return None

        return cls(
            endpoint=endpoint.rstrip("/"),
            key=key,
            api_version=os.getenv("CONTENT_SAFETY_API_VERSION", "2024-09-01"),
            threshold=int(os.getenv("CONTENT_SAFETY_THRESHOLD", "4")),
        )


class AzureContentSafety:
    """Small wrapper around Azure AI Content Safety REST APIs."""

    def __init__(self, config: ContentSafetyConfig):
        self.config = config
        self.headers = {
            "Ocp-Apim-Subscription-Key": config.key,
            "Content-Type": "application/json",
        }

    def analyze_text(self, text: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Check text for harmful-content categories and severities."""
        result = self._post("/contentsafety/text:analyze", {"text": text})

        # Azure returns category severities. Anything at or above the configured
        # threshold is treated as blocked for this demo.
        flagged = [
            item
            for item in result.get("categoriesAnalysis", [])
            if item.get("severity", 0) >= self.config.threshold
        ]

        if flagged:
            categories = ", ".join(
                f"{item.get('category')} severity {item.get('severity')}"
                for item in flagged
            )
            return False, f"Blocked: Azure Content Safety flagged {categories}.", result

        return True, "Allowed", result

    def shield_prompt(
        self, user_prompt: str, documents: Optional[List[str]] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Check the prompt for direct or indirect prompt attacks."""
        result = self._post(
            "/contentsafety/text:shieldPrompt",
            {
                "userPrompt": user_prompt,
                "documents": documents or [],
            },
        )

        if self._prompt_attack_detected(result):
            return False, "Blocked: Azure Prompt Shields detected a prompt attack.", result

        return True, "Allowed", result

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send one POST request to an Azure AI Content Safety endpoint."""
        url = f"{self.config.endpoint}{path}?api-version={self.config.api_version}"
        response = requests.post(url, headers=self.headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _prompt_attack_detected(result: Dict[str, Any]) -> bool:
        """Read Prompt Shields response fields for attack detection."""
        direct = result.get("userPromptAnalysis", {}).get("attackDetected")
        indirect_items = result.get("documentsAnalysis", [])
        indirect = any(item.get("attackDetected") for item in indirect_items)
        return bool(direct or indirect)


def _is_placeholder(value: str) -> bool:
    """Detect values copied from .env.example instead of real credentials."""
    return "YOUR-" in value or "YOUR_" in value
