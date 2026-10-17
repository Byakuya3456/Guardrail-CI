"""Core domain models for Guardrail-CI."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from guardrail_ci.core.exceptions import InvalidStateTransitionError
from guardrail_ci.core.state import IncidentState, can_transition

__all__ = [
    "Diagnosis",
    "EvidenceItem",
    "FailureCategory",
    "Incident",
    "IncidentState",
    "PatchFile",
    "PolicyDecision",
    "RemediationPlan",
    "ValidationResult",
]


class FailureCategory(str, Enum):
    """Supported CI failure categories."""

    DEPENDENCY_INSTALLATION = "dependency_installation"
    LINT_TYPE_CHECK = "lint_type_check"
    UNIT_TEST = "unit_test"
    RUNTIME_CONFIGURATION = "runtime_configuration"
    UNKNOWN = "unknown"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceItem(BaseModel):
    """A single piece of evidence from CI logs or metadata."""

    job: str = Field(description="Name of the job where the issue occurred")
    step: str = Field(description="Name or index of the step that failed")
    excerpt: str = Field(description="Relevant sanitized log snippet")
    source: str = Field(default="", description="Identifier or source reference (e.g. job:123/step:2)")
    is_observation: bool = Field(default=True, description="True = observed fact, False = model inference")


class Diagnosis(BaseModel):
    """Structured failure diagnosis produced from collected evidence."""

    failure_category: FailureCategory = Field(description="Categorization of the failure")
    summary: str = Field(description="Concise description of the failure")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Grounding evidence items")
    likely_root_cause: str = Field(description="Probable underlying technical cause")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    recommended_actions: list[str] = Field(default_factory=list, description="Prescribed remediation steps")
    unresolved_questions: list[str] = Field(default_factory=list, description="Areas of uncertainty")


class PatchFile(BaseModel):
    """A single file change in a proposed remediation patch."""

    path: str = Field(description="Relative repository path to modified file")
    original_content: str | None = Field(default=None, description="Original file content")
    modified_content: str = Field(description="Proposed new file content")
    diff: str = Field(default="", description="Unified diff representation")


class RemediationPlan(BaseModel):
    """Proposed fix plan and associated patch files."""

    description: str = Field(description="Overview of the remediation approach")
    intended_effect: str = Field(description="Expected impact of applying this fix")
    files: list[PatchFile] = Field(default_factory=list, description="List of modified files")
    risks: list[str] = Field(default_factory=list, description="Known risks or side-effects of this fix")


class ValidationResult(BaseModel):
    """Result from executing an allowlisted validation check."""

    command: str = Field(description="Validation command that was run")
    exit_code: int = Field(description="Process exit code")
    stdout: str = Field(default="", description="Standard output (bounded)")
    stderr: str = Field(default="", description="Standard error output (bounded)")
    passed: bool = Field(description="True if check passed (exit_code == 0)")
    duration_seconds: float = Field(default=0.0, description="Execution time in seconds")


class PolicyDecision(BaseModel):
    """Record of a policy evaluation on a tool action."""

    action: str = Field(description="Specific operation or function requested")
    action_type: str = Field(description="Action category (e.g., read, analyze, validate, publish)")
    allowed: bool = Field(description="Whether the policy permits this action")
    reason: str = Field(description="Detailed rationale for allow or deny")
    requires_approval: bool = Field(default=False, description="Whether human confirmation is required")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Incident(BaseModel):
    """Top-level incident entity tracking investigation lifecycle and artifacts."""

    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repository: str = Field(description="Target repository in owner/repo format")
    run_id: int = Field(description="GitHub Actions workflow run ID")
    state: IncidentState = Field(default=IncidentState.RECEIVED)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Evidence and analysis
    evidence: list[EvidenceItem] = Field(default_factory=list)
    diagnosis: Diagnosis | None = None
    remediation_plan: RemediationPlan | None = None
    validation_results: list[ValidationResult] = Field(default_factory=list)
    policy_decisions: list[PolicyDecision] = Field(default_factory=list)
    approval_status: str = Field(default="not_required")
    error_message: str | None = None

    def transition_to(self, target_state: IncidentState) -> None:
        """Safely transition to another state in the lifecycle."""
        if not can_transition(self.state, target_state):
            raise InvalidStateTransitionError(
                f"Cannot transition incident {self.incident_id} from {self.state.value} to {target_state.value}"
            )
        self.state = target_state
        self.updated_at = datetime.now(UTC)
