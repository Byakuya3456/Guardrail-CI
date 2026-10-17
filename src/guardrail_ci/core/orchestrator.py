"""Incident orchestrator coordinating the lifecycle and policy evaluation."""

from __future__ import annotations

import logging
from typing import Any

from guardrail_ci.adapters.github.client import GitHubClient
from guardrail_ci.adapters.model.base import ModelAdapter
from guardrail_ci.audit.logger import AuditLogger
from guardrail_ci.core.exceptions import PolicyDeniedError
from guardrail_ci.core.models import Incident, IncidentState
from guardrail_ci.evidence.collector import EvidenceCollector
from guardrail_ci.policy.actions import ActionType
from guardrail_ci.policy.engine import PolicyEngine

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates the investigation lifecycle through deterministic state transitions."""

    def __init__(
        self,
        github_client: GitHubClient,
        model_adapter: ModelAdapter,
        policy_engine: PolicyEngine | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._github = github_client
        self._model = model_adapter
        self._policy = policy_engine or PolicyEngine()
        self._audit = audit_logger or AuditLogger()
        self._evidence_collector = EvidenceCollector(github_client)

    def _authorize(
        self,
        incident: Incident,
        action: str,
        action_type: ActionType,
        context: dict[str, Any] | None = None,
        is_user_approved: bool = False,
    ) -> None:
        """Enforce deterministic policy authorization before executing any action."""
        decision = self._policy.evaluate(
            action=action,
            action_type=action_type.value,
            context=context,
            is_user_approved=is_user_approved,
        )
        incident.policy_decisions.append(decision)
        self._audit.log_decision(incident.incident_id, decision, details=context)

        if not decision.allowed:
            raise PolicyDeniedError(f"Policy denied action '{action}': {decision.reason}")

    def investigate(self, repo: str, run_id: int) -> Incident:
        """Execute a full, read-only failure investigation."""
        incident = Incident(repository=repo, run_id=run_id)
        logger.info("Initiating investigation for %s run %d (Incident: %s)", repo, run_id, incident.incident_id)

        try:
            # Step 1: Authorize and retrieve workflow run metadata
            self._authorize(
                incident,
                action="get_workflow_run",
                action_type=ActionType.READ,
                context={"repository": repo, "run_id": run_id},
            )
            run = self._github.get_workflow_run(repo, run_id)
            if run.conclusion != "failure":
                raise ValueError(
                    f"Workflow run {run_id} has conclusion '{run.conclusion}'; expected 'failure'."
                )

            # Step 2: Authorize and collect bounded, sanitized evidence
            self._authorize(
                incident,
                action="collect_evidence",
                action_type=ActionType.READ,
                context={"repository": repo, "run_id": run_id},
            )
            incident.evidence = self._evidence_collector.collect(repo, run_id)
            incident.transition_to(IncidentState.EVIDENCE_COLLECTED)

            # Step 3: Authorize and execute diagnosis via model adapter
            self._authorize(
                incident,
                action="diagnose_failure",
                action_type=ActionType.ANALYZE,
                context={"repository": repo, "evidence_count": len(incident.evidence)},
            )
            workflow_context = {
                "repository": repo,
                "run_id": run_id,
                "workflow_name": run.name,
                "event": run.event,
            }
            incident.diagnosis = self._model.diagnose(incident.evidence, workflow_context)
            incident.transition_to(IncidentState.DIAGNOSED)

            # Step 4: Phase 1 concludes without repository writes
            incident.transition_to(IncidentState.COMPLETED_WITHOUT_WRITE)
            logger.info("Investigation completed successfully for incident %s", incident.incident_id)

        except Exception as e:
            logger.error("Investigation halted due to error: %s", e)
            incident.error_message = str(e)
            if incident.state != IncidentState.FAILED:
                incident.transition_to(IncidentState.FAILED)

        return incident
