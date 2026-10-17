"""Incident orchestrator coordinating the lifecycle, policy evaluation, and validation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from guardrail_ci.adapters.github.client import GitHubClient
from guardrail_ci.adapters.model.base import ModelAdapter
from guardrail_ci.audit.logger import AuditLogger
from guardrail_ci.core.exceptions import PolicyDeniedError
from guardrail_ci.core.models import Incident, IncidentState
from guardrail_ci.evidence.collector import EvidenceCollector
from guardrail_ci.policy.actions import ActionType
from guardrail_ci.policy.engine import PolicyEngine
from guardrail_ci.remediation.constraints import is_patch_allowed
from guardrail_ci.storage.repositories import IncidentRepository
from guardrail_ci.validation.runner import ValidationRunner
from guardrail_ci.validation.worker import (
    DockerValidationWorker,
    IsolatedSubprocessWorker,
    ValidationWorker,
    is_docker_available,
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates the incident investigation and remediation lifecycle."""

    def __init__(
        self,
        github_client: GitHubClient,
        model_adapter: ModelAdapter,
        policy_engine: PolicyEngine | None = None,
        audit_logger: AuditLogger | None = None,
        repository_storage: IncidentRepository | None = None,
        validation_worker: ValidationWorker | None = None,
    ) -> None:
        self._github = github_client
        self._model = model_adapter
        self._policy = policy_engine or PolicyEngine()
        self._audit = audit_logger or AuditLogger()
        self._storage = repository_storage
        self._evidence_collector = EvidenceCollector(github_client)

        if validation_worker is not None:
            self._validation_worker = validation_worker
        elif is_docker_available():
            from guardrail_ci.config.settings import ValidationSettings
            self._validation_worker = DockerValidationWorker(ValidationSettings())
        else:
            self._validation_worker = IsolatedSubprocessWorker()

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

    def investigate(
        self,
        repo: str,
        run_id: int,
        propose_fix: bool = False,
        validation_commands: list[str] | None = None,
        candidate_files: dict[str, str] | None = None,
        workspace_base_dir: Path | None = None,
    ) -> Incident:
        """Execute the incident investigation and optional patch validation workflow."""
        incident = Incident(repository=repo, run_id=run_id)
        logger.info("Initiating investigation for %s run %d (Incident: %s)", repo, run_id, incident.incident_id)

        try:
            # Step 1: Retrieve workflow run metadata
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

            # Step 2: Collect bounded, sanitized evidence
            self._authorize(
                incident,
                action="collect_evidence",
                action_type=ActionType.READ,
                context={"repository": repo, "run_id": run_id},
            )
            incident.evidence = self._evidence_collector.collect(repo, run_id)
            incident.transition_to(IncidentState.EVIDENCE_COLLECTED)

            # Step 3: Execute diagnosis via model adapter
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

            # Step 4: Optional remediation patch proposal and validation
            if propose_fix and incident.diagnosis and candidate_files:
                self._handle_remediation_and_validation(
                    incident=incident,
                    candidate_files=candidate_files,
                    validation_commands=validation_commands or [],
                    workspace_base_dir=workspace_base_dir,
                )
            else:
                incident.transition_to(IncidentState.COMPLETED_WITHOUT_WRITE)

            logger.info("Incident %s reached final state: %s", incident.incident_id, incident.state.value)

        except Exception as e:
            logger.error("Investigation halted due to error: %s", e)
            incident.error_message = str(e)
            if incident.state != IncidentState.FAILED:
                incident.transition_to(IncidentState.FAILED)

        # Persist incident to SQLite if storage is configured
        if self._storage is not None:
            try:
                self._storage.save(incident)
            except Exception as e:
                logger.error("Failed persisting incident %s to database: %s", incident.incident_id, e)

        return incident

    def _handle_remediation_and_validation(
        self,
        incident: Incident,
        candidate_files: dict[str, str],
        validation_commands: list[str],
        workspace_base_dir: Path | None = None,
    ) -> None:
        """Process remediation plan generation, constraint evaluation, and isolated validation."""
        assert incident.diagnosis is not None

        # Request patch proposal from model adapter
        plan = self._model.propose_remediation(incident.diagnosis, candidate_files)
        if not plan or not plan.files:
            logger.info("No patch proposed for incident %s", incident.incident_id)
            incident.transition_to(IncidentState.COMPLETED_WITHOUT_WRITE)
            return

        incident.remediation_plan = plan
        incident.transition_to(IncidentState.PLAN_PROPOSED)

        # Authorize patch preparation & verify deterministic constraints
        self._authorize(
            incident,
            action="prepare_patch",
            action_type=ActionType.PREPARE_PATCH,
            context={"file_count": len(plan.files)},
        )

        allowed, reason = is_patch_allowed(plan)
        if not allowed:
            logger.warning("Patch rejected by deterministic constraints: %s", reason)
            self._audit.log_action(
                incident_id=incident.incident_id,
                action="patch_constraint_check",
                action_type="prepare_patch",
                allowed=False,
                reason=reason,
            )
            incident.transition_to(IncidentState.COMPLETED_WITHOUT_WRITE)
            return

        incident.transition_to(IncidentState.POLICY_CHECKED)
        incident.transition_to(IncidentState.PATCH_PREPARED)

        # If validation checks requested, run them in isolation
        if validation_commands:
            self._authorize(
                incident,
                action="validate_patch",
                action_type=ActionType.VALIDATE,
                context={"commands": validation_commands},
            )
            incident.transition_to(IncidentState.VALIDATING)

            runner = ValidationRunner(self._validation_worker)
            passed, results = runner.validate_plan(
                plan=plan,
                commands=validation_commands,
                base_dir=workspace_base_dir,
            )
            incident.validation_results = results

            if passed:
                incident.transition_to(IncidentState.VALIDATED)
            else:
                incident.transition_to(IncidentState.VALIDATION_FAILED)
                incident.transition_to(IncidentState.COMPLETED_WITHOUT_WRITE)
        else:
            incident.transition_to(IncidentState.COMPLETED_WITHOUT_WRITE)
