# Guardrail-CI
## Product Requirements Document (PRD)

**Release:** MVP  
**Version:** 0.1  
**Status:** MVP planning baseline  
**Scope:** GitHub Actions only  
**Date:** October 2026

---

## 1. Document Control

| Field | Value |
|---|---|
| Product | Guardrail-CI |
| Document | Product Requirements Document |
| Version | 0.1 |
| Status | MVP planning baseline |
| Platform scope | GitHub Actions only |
| Primary audience | Project developer, portfolio reviewers, junior DevOps/SRE/DevSecOps hiring teams |

## 2. Executive Summary

Guardrail-CI is a security-conscious AI assistant that investigates failed GitHub Actions workflows and helps prepare validated remediations. It retrieves workflow evidence, produces a structured diagnosis, proposes a minimal patch, runs permitted checks in an isolated environment, and prepares a human-reviewable result.

The MVP supports GitHub Actions only. It prioritizes one complete, demonstrable workflow over broad platform coverage. The model may recommend actions, but a separate deterministic policy layer authorizes operations. Production deployment and autonomous merging are excluded.

## 3. Problem Statement

Investigating CI failures often means searching long logs, correlating errors with repository files, identifying a root cause, and repeating tests after a fix. LLMs can help analyze evidence, but unrestricted repository access, shell execution, credentials, or deployment permissions create security risks.

Guardrail-CI aims to reduce investigation effort while keeping execution bounded, auditable, validated, and subject to human approval.

## 4. Goals and Non-Goals

### 4.1 Goals

- Connect to one configured GitHub repository using a narrowly scoped credential.
- Retrieve workflow run metadata, failed job details, and bounded log excerpts for a selected run.
- Produce an evidence-backed diagnosis with likely cause, confidence, and recommended next steps.
- Generate a minimal proposed patch for supported failure categories.
- Validate proposed changes using allowlisted checks in an isolated environment.
- Require human approval before publishing a branch or pull request.
- Enforce authorization outside the model and record tool actions and policy decisions.
- Support a configurable adapter for a local OpenAI-compatible endpoint or hosted model API.
- Provide a reproducible demo and measurable evaluation suite.

### 4.2 Non-Goals

- GitLab CI, Jenkins, Argo CD, Flux, or other platform integrations.
- Autonomous production deployment, infrastructure provisioning, merging, or rollback.
- Unrestricted shell access or model-directed arbitrary tool execution.
- Automatic merging of generated patches.
- A general-purpose multi-agent framework, model training, or enterprise SaaS control plane.
- Guaranteeing that every AI diagnosis is correct.

## 5. Target User and Primary Workflow

### 5.1 Primary User

A developer or DevOps engineer working with a GitHub repository who needs help understanding a failed Actions workflow and preparing a safe fix.

### 5.2 User Story

As a developer, I want to provide a repository and failed workflow run ID so Guardrail-CI can explain the failure using log evidence, suggest a minimal fix, validate it, and prepare a reviewable result without making unapproved changes.

### 5.3 Workflow

1. User selects a configured repository and failed workflow run.
2. System retrieves run metadata, failed jobs, and bounded logs.
3. Agent classifies the failure and returns a diagnosis with evidence.
4. Agent proposes a remediation plan and, where supported, a minimal patch.
5. Policy layer evaluates every requested operation.
6. Validation service tests the patch in an isolated workspace.
7. System presents diagnosis, diff, validation results, policy decisions, and risks.
8. After explicit approval, the system may create a branch and pull request. It never merges or deploys.

## 6. Scope and Release Boundaries

| Capability | MVP decision |
|---|---|
| CI provider | GitHub Actions only |
| Repository scope | One configured repository for the first demo; use an allowlist |
| Trigger | Manual CLI command for a selected failed run |
| Diagnosis | Common CI failures, evidence, uncertainty |
| Patch generation | Proposed patch limited to allowed paths and size |
| Validation | Allowlisted tests, lint, and configured security checks |
| Publication | Human-approved branch/PR creation, after core flow is stable |
| Deployment | Out of scope |
| Interface | CLI first; dashboard optional |
| Model provider | One adapter interface; one configured provider at a time |

## 7. Functional Requirements

### FR-01: GitHub Actions Integration

- Accept repository identifier and workflow run ID.
- Use a token stored outside source control with minimum required permissions.
- Retrieve run status, jobs, timestamps, and relevant logs using GitHub-supported APIs.
- Handle missing permissions, nonexistent runs, rate limits, network errors, and unavailable logs clearly.
- Limit accessible repositories, log size, and retrieved context.

### FR-02: Evidence Collection

- Collect only evidence needed for the selected incident.
- Redact recognized secret-like values before model submission or ordinary logging.
- Treat logs, repository files, workflow YAML, issue text, and dependency output as untrusted data.
- Keep evidence references such as job, step, and relevant log excerpt where possible.

### FR-03: Diagnosis

- Return structured summary, failure category, evidence, likely cause, confidence, recommendations, and unresolved questions.
- Separate observed facts from model inference.
- Support an explicit insufficient-evidence outcome.
- Bound log excerpts and prompt context.

### FR-04: Remediation Planning

- Produce a plan before any change.
- Generate a minimal patch limited by deterministic path and size rules.
- Reject changes to secrets, credentials, protected security controls, or out-of-scope files.
- Show a diff and intended effect before validation.
- Model output alone must never authorize a tool call.

### FR-05: Validation

- Run only explicitly allowlisted validation commands.
- Use a disposable isolated worker with time and resource limits.
- Do not expose GitHub tokens, model keys, or host credentials to executed code.
- Capture bounded output and exit status.
- Mark a patch unvalidated if a required check fails, is skipped, or is inconclusive.

### FR-06: Policy and Approval

- Check every tool action before execution.
- Classify actions as read, analyze, prepare patch, validate, and publish branch/PR.
- Default to deny for unknown actions, invalid inputs, or policy failures.
- Require explicit human approval before remote repository writes.
- Do not implement merge, deployment, infrastructure changes, disabling scanners, or weakening branch protection.

### FR-07: Audit and Reporting

- Record incident/run ID, tool, action, policy result, validation result, and timestamps.
- Never record raw secrets, authorization headers, or unrestricted environment dumps.
- Produce a report with evidence, patch, validation, approval status, and limitations.
- Allow evaluation cases to be reproduced from sanitized fixtures.

### FR-08: Model Adapter

- Use a common interface for bounded prompts and structured responses.
- Support a local OpenAI-compatible endpoint or hosted API through configuration.
- Isolate provider-specific logic from orchestration and policy.
- Use timeouts, bounded retries, schema validation, and graceful failure.

## 8. Security Requirements

The model is not the security boundary. A separate policy and execution layer must authorize operations.

| Risk | Required MVP control |
|---|---|
| Credentials | Keep tokens out of source control and prompts; use environment configuration or an approved secret store. |
| Least privilege | Use a fine-grained, repository-scoped token with minimum permissions; separate read and write capabilities where practical. |
| Prompt injection | Treat repository content, logs, and issue text as data. Their contents cannot alter policy or grant tool permissions. |
| Command execution | Deny arbitrary model-generated shell commands. Use fixed, allowlisted validation commands. |
| Sandboxing | Use a disposable isolated worker, no valuable credentials, restricted networking where feasible, and resource/time limits. |
| Secret handling | Redact secret-like strings; do not return secrets in reports, errors, or audit logs. |
| Repository writes | Require human approval and restrict changed paths and patch size. |
| Security controls | Deny changes that disable scanners, weaken permissions, or bypass required checks. |
| Fail-safe behavior | If policy, authorization, or required validation fails, stop and report the reason. |
| Auditability | Record allowed and denied actions without storing sensitive payloads. |

**Important caveat:** running untrusted repository code is inherently risky. Isolation reduces risk but does not eliminate it. Use a disposable test repository and never expose personal or production credentials to the runner.

## 9. Non-Functional Requirements

- **Reliability:** API, model, policy, and validation failures produce explicit states, not silent success.
- **Security:** no secrets in source control, prompts, or ordinary audit logs.
- **Traceability:** each incident can be followed from run ID to final report.
- **Maintainability:** separate GitHub adapter, model adapter, policy, validation, storage, and audit modules.
- **Portability:** run locally without Kubernetes or mandatory cloud deployment.
- **Performance target:** aim for diagnosis within 60 seconds for a typical small failed run, excluding unusually slow dependencies. This is a target, not a guarantee.
- **Cost control:** bound log size, prompt size, retries, and model calls.
- **Usability:** CLI alone must be enough to demonstrate the core flow.

## 10. Proposed Technical Design

| Layer | Responsibility | MVP choice |
|---|---|---|
| Interface | Input and results | Python CLI; FastAPI optional |
| Orchestrator | Coordinate incident state | Python modular monolith |
| GitHub adapter | Read runs/jobs/logs; optional PR creation | GitHub REST API |
| Model adapter | Diagnosis and patch proposal | Local OpenAI-compatible or hosted API |
| Tool layer | Validated actions | Typed schemas and allowlisted functions |
| Policy | Allow, deny, require approval | Deterministic Python policy first; OPA/Rego optional |
| Validation worker | Tests and scanners | Disposable isolated worker |
| Storage | Incident metadata and outcomes | SQLite |
| Audit | Action and decision trail | Structured JSON logs with redaction |
| Evaluation | Scenario and security tests | pytest plus sanitized fixtures |

### 10.1 Design Principle

Use a modular monolith with explicit interfaces. Do not build microservices, a plugin marketplace, vector-database memory, or multi-agent orchestration for the MVP.

### 10.2 Suggested Incident States

`RECEIVED` → `EVIDENCE_COLLECTED` → `DIAGNOSED` → `PLAN_PROPOSED` → `POLICY_CHECKED` → `PATCH_PREPARED` → `VALIDATING` → `VALIDATED` or `VALIDATION_FAILED` → `AWAITING_APPROVAL` → `PR_CREATED` or `COMPLETED_WITHOUT_WRITE`.

Unrecoverable failures transition to `FAILED` with a visible reason.

## 11. CLI and Output Contract

### 11.1 Example Command

```bash
guardrail-ci investigate --repo OWNER/REPOSITORY --run-id RUN_ID
```

### 11.2 Required Report Fields

- Incident and workflow run identifiers.
- Failed job and step.
- Failure category and concise summary.
- Evidence excerpts and source references.
- Likely root cause, confidence, and uncertainty.
- Recommended remediation plan and patch diff, if available.
- Validation checks and exit statuses.
- Policy decisions, approval state, known risks, and next action.

### 11.3 Example Structured Response

```json
{
  "incident_id": "...",
  "repository": "OWNER/REPOSITORY",
  "run_id": "...",
  "failure_category": "dependency_installation",
  "summary": "...",
  "evidence": [
    {
      "job": "...",
      "step": "...",
      "excerpt": "..."
    }
  ],
  "likely_root_cause": "...",
  "confidence": 0.0,
  "recommended_actions": ["..."],
  "patch_status": "not_created",
  "validation_status": "not_run",
  "policy_decisions": [],
  "approval_status": "not_required"
}
```

## 12. Acceptance Criteria

| ID | Acceptance criterion |
|---|---|
| AC-01 | A valid repository and failed run ID returns run and failed-job information. |
| AC-02 | Invalid access or a missing run produces a clear error without leaking credentials. |
| AC-03 | Diagnosis includes evidence and separates observations from inference. |
| AC-04 | Insufficient evidence is reported rather than replaced with a fabricated cause. |
| AC-05 | Every tool action passes deterministic policy before execution. |
| AC-06 | Unknown actions and policy failures are denied by default. |
| AC-07 | The model cannot execute arbitrary shell commands directly. |
| AC-08 | Patches are shown as diffs and restricted by path and size rules. |
| AC-09 | Validation runs without GitHub or model credentials. |
| AC-10 | Failed, skipped, or inconclusive required checks prevent a `validated` status. |
| AC-11 | Remote writes require explicit approval; merge and deploy paths are absent. |
| AC-12 | Audit records contain action outcomes but no secrets. |
| AC-13 | At least 20 documented CI failure scenarios are included in evaluation. |
| AC-14 | README documents setup, permissions, architecture, threat model, limitations, and demo. |

## 13. Evaluation and Success Metrics

Build 20 to 30 reproducible cases in a dedicated test repository or sanitized fixtures. Include dependency installation errors, lint failures, unit-test failures, incorrect runtime versions, malformed workflow YAML, missing environment variables, permission errors, and insufficient-evidence cases.

| Metric | Initial MVP target |
|---|---|
| Diagnosis quality | At least 80% materially correct diagnoses against known root causes. |
| Evidence grounding | Every diagnosis has evidence or explicitly states evidence is insufficient. |
| Patch validation | Measure and report the percentage of generated patches passing required checks; establish a baseline before setting a target. |
| Unsafe action blocking | 100% of defined prohibited-action tests blocked in the test suite. |
| Secret leakage | Zero known test secrets in prompts, ordinary audit logs, or user-facing reports. |
| Reproducibility | Each evaluation case has expected outcomes and documented rerun instructions. |
| Operational visibility | Every incident has a final status and traceable action history. |

These are proposed targets, not measured results. Publish actual measurements, test conditions, and limitations in the README.

## 14. Delivery Plan

| Phase | Deliverable | Definition of done |
|---|---|---|
| 1. Read-only investigator | GitHub API, CLI, evidence collection, structured diagnosis | Investigates a real failed run without repository writes. |
| 2. Policy and audit | Typed tools, authorization, redaction, audit | Prohibited actions are denied and testable; actions are traceable. |
| 3. Patch and validation | Patch proposal, diff, isolated validation | A supported failure can be patched and checked in a disposable workspace. |
| 4. Human-reviewed PR | Approval and controlled branch/PR creation | Only approved changes are published; no merge/deploy path exists. |
| 5. Evaluation and polish | Scenario suite, metrics, documentation, demo | Acceptance tests pass and actual results and limitations are documented. |

**Priority:** finish Phase 1 before Phase 2. Defer memory, dashboards, and platform adapters until the diagnosis flow is reliable.

## 15. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Incorrect diagnosis | Evidence-backed output, uncertainty, deterministic checks, human review. |
| Prompt injection | Treat content as untrusted; enforce permissions outside the model. |
| Malicious validation code | Disposable isolation, no secrets, restricted network/resources, allowlisted commands. |
| Overbroad GitHub token | Repository-scoped fine-grained token and minimum permissions. |
| Unbounded cost | Bounded logs/context, timeouts, capped retries and calls. |
| Scope creep | GitHub Actions only; no deployment or extra platforms. |
| Weak portfolio evidence | Publish architecture, threat model, reproducible results, demo, and limitations. |

## 16. Required Repository Deliverables

- Working Python application and CLI.
- GitHub Actions API integration and documented permissions.
- Model adapter and structured response schemas.
- Deterministic policy module with tests.
- Credential redaction and structured audit logging.
- Isolated validation workflow with allowlisted checks.
- Sanitized fixtures or a dedicated sample repository with intentional failures.
- Unit, integration, and security tests.
- README with setup, architecture, threat model, limitations, and demo steps.
- Evaluation report with actual metrics and known failure cases.

## 17. Definition of MVP Complete

- A user can investigate a failed GitHub Actions run from the CLI.
- The diagnosis is evidence-backed and can report insufficient evidence.
- A limited patch can be proposed and validated without exposing credentials to executed code.
- A deterministic policy layer blocks prohibited actions independently of the model.
- Remote writes require human approval; merging and deployment are not implemented.
- Audit logs and a reproducible evaluation suite are included.
- Another developer can reproduce the demo from documented setup instructions.

## 18. Open Decisions

- Select the first model provider while preserving the adapter interface.
- Choose the initial isolated validation approach. An ordinary subprocess alone should not be treated as a security sandbox.
- Start with three failure categories: dependency installation, lint/type-check failures, and unit-test failures.
- Decide whether branch/PR creation is included in the first public demo or deferred until diagnosis and validation are stable.
- Map the exact GitHub API operations before setting token permissions.

## 19. Glossary

| Term | Meaning |
|---|---|
| CI | Continuous Integration |
| Workflow run | A specific execution of a GitHub Actions workflow. |
| Evidence-backed diagnosis | A diagnosis tied to observed logs or metadata, with inference distinguished from fact. |
| Policy engine | Deterministic logic that allows, denies, or requires approval for an action. |
| Isolated validation | Testing in an environment separated from valuable credentials and systems. |
| PR | Pull request, a proposed repository change submitted for review. |
| Prompt injection | Untrusted content attempting to manipulate model instructions or tool use. |
