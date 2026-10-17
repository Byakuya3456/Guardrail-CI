"""OpenAI-compatible model adapter implementation."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from guardrail_ci.adapters.model.base import ModelAdapter
from guardrail_ci.adapters.model.prompts import (
    build_diagnosis_prompt,
    build_remediation_prompt,
)
from guardrail_ci.config.settings import ModelSettings
from guardrail_ci.core.models import (
    Diagnosis,
    EvidenceItem,
    FailureCategory,
    RemediationPlan,
)

logger = logging.getLogger(__name__)


class OpenAICompatAdapter(ModelAdapter):
    """Adapter for OpenAI and OpenAI-compatible inference endpoints (Ollama, vLLM, etc.)."""

    def __init__(self, settings: ModelSettings, client: OpenAI | None = None) -> None:
        self._settings = settings
        self._client = client or OpenAI(
            api_key=settings.api_key or "EMPTY",
            base_url=settings.api_base,
            timeout=settings.timeout_seconds,
            max_retries=settings.max_retries,
        )

    def diagnose(
        self,
        evidence: list[EvidenceItem],
        workflow_context: dict[str, Any],
    ) -> Diagnosis:
        """Call model and deserialize verified Diagnosis instance."""
        if not evidence:
            return Diagnosis(
                failure_category=FailureCategory.INSUFFICIENT_EVIDENCE,
                summary="No failed job logs or step details found in workflow run.",
                evidence=[],
                likely_root_cause="Insufficient evidence available to determine cause.",
                confidence=0.0,
                recommended_actions=["Review the workflow execution directly on GitHub."],
                unresolved_questions=["Why were no log lines captured?"],
            )

        prompts = build_diagnosis_prompt(evidence, workflow_context)

        try:
            response = self._client.chat.completions.create(
                model=self._settings.name,
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]},
                ],
                max_tokens=self._settings.max_tokens,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_content)

            # Ensure evidence references are preserved
            diagnosis = Diagnosis.model_validate(
                {
                    **parsed,
                    "evidence": [item.model_dump() for item in evidence],
                }
            )
            return diagnosis

        except Exception as e:
            logger.error("Model diagnosis failed or produced invalid format: %s", e)
            return Diagnosis(
                failure_category=FailureCategory.UNKNOWN,
                summary=f"Automated diagnosis encountered an error: {e}",
                evidence=evidence,
                likely_root_cause="Analysis could not complete due to model response failure.",
                confidence=0.0,
                recommended_actions=["Check API keys and model availability."],
                unresolved_questions=[str(e)],
            )

    def propose_remediation(
        self,
        diagnosis: Diagnosis,
        file_contents: dict[str, str],
    ) -> RemediationPlan | None:
        """Call model to propose minimal patch plan."""
        if diagnosis.confidence < 0.4:
            logger.info("Skipping remediation proposal due to low confidence (%.2f)", diagnosis.confidence)
            return None

        prompts = build_remediation_prompt(diagnosis, file_contents)

        try:
            response = self._client.chat.completions.create(
                model=self._settings.name,
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]},
                ],
                max_tokens=self._settings.max_tokens,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_content)
            if not parsed.get("files"):
                return None
            return RemediationPlan.model_validate(parsed)

        except Exception as e:
            logger.error("Failed to generate remediation plan: %s", e)
            return None
