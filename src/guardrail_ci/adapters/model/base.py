"""Abstract model adapter interface for LLM operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from guardrail_ci.core.models import Diagnosis, EvidenceItem, RemediationPlan


class ModelAdapter(ABC):
    """Abstract interface defining required LLM diagnosis and remediation capabilities."""

    @abstractmethod
    def diagnose(
        self,
        evidence: list[EvidenceItem],
        workflow_context: dict[str, Any],
    ) -> Diagnosis:
        """Analyze evidence and return a structured, validated Diagnosis model."""
        ...

    @abstractmethod
    def propose_remediation(
        self,
        diagnosis: Diagnosis,
        file_contents: dict[str, str],
    ) -> RemediationPlan | None:
        """Propose a remediation plan and minimal patch based on confirmed diagnosis."""
        ...
