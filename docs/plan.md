# Guardrail-CI — Project Plan

**Version:** 0.1  
**Date:** October 2026  
**Source PRD:** `Guardrail-CI_MVP_PRD.md` v0.1  

---

## 1. Project Overview

Guardrail-CI is a security-conscious AI assistant that investigates failed GitHub Actions workflows. It retrieves evidence, diagnoses failures, proposes minimal patches, validates them in isolation, and prepares human-reviewable results — all governed by a deterministic policy layer that sits *outside* the AI model.

**Core principle:** The model recommends; a separate policy layer authorizes. No autonomous merging or deployment.

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌───────────────────────────────────────────────────────────┐
│                       CLI / FastAPI                       │
│                    (User Interface Layer)                  │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                      Orchestrator                         │
│            (Incident State Machine & Coordination)        │
│                                                           │
│   RECEIVED → EVIDENCE_COLLECTED → DIAGNOSED →             │
│   PLAN_PROPOSED → POLICY_CHECKED → PATCH_PREPARED →       │
│   VALIDATING → VALIDATED/VALIDATION_FAILED →              │
│   AWAITING_APPROVAL → PR_CREATED/COMPLETED_WITHOUT_WRITE  │
└──┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬───────┘
   │      │      │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐
│GH   ││Model││Tool ││Poli-││Vali-││Stor-││Audit││Eval │
│Adapt││Adapt││Layer││cy   ││dator││age  ││     ││     │
│er   ││er   ││     ││     ││     ││     ││     ││     │
└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘
```

### 2.2 Module Breakdown

| Module | Responsibility |
|---|---|
| **CLI** | Parse commands, display reports, collect approval input |
| **Orchestrator** | Drive incident state machine, coordinate all modules |
| **GitHub Adapter** | Interact with GitHub REST API (runs, jobs, logs, PR creation) |
| **Model Adapter** | Send bounded prompts, receive structured diagnosis/patch responses |
| **Tool Layer** | Typed tool schemas, allowlisted function registry |
| **Policy Engine** | Deterministic allow/deny/require-approval decisions |
| **Validation Worker** | Execute allowlisted checks in disposable isolated environments |
| **Storage** | SQLite for incident metadata and outcomes |
| **Audit Logger** | Structured JSON logs with automatic secret redaction |
| **Evaluation Suite** | pytest-based scenarios with sanitized fixtures |

---

## 3. Technology Stack

| Component | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Rapid development, rich ecosystem, easy CLI tooling |
| CLI Framework | `click` or `typer` | Ergonomic CLI with type hints |
| HTTP Client | `httpx` (async-capable) | Modern, testable, timeout support |
| API Integration | GitHub REST API v3 | Well-documented, fine-grained token support |
| LLM Interface | OpenAI-compatible API | Portable across local (Ollama/vLLM) and hosted providers |
| Database | SQLite via `sqlite3` or `sqlmodel` | Zero-config, file-based, sufficient for MVP |
| Isolation | Docker containers (`docker run --rm --network=none`) | Disposable workers without credential leakage |
| Testing | `pytest`, `pytest-asyncio`, `responses`/`respx` | Standard Python testing with HTTP mocking |
| Schema Validation | `pydantic` v2 | Typed models, JSON serialization, validation |
| Packaging | `pyproject.toml` + `pip` | Modern Python packaging |
| Linting/Formatting | `ruff`, `mypy` | Fast linting + static type checking |

---

## 4. Delivery Phases

The PRD defines 5 phases. Each phase below maps to specific functional requirements (FRs), acceptance criteria (ACs), and deliverables.

### Phase 1: Read-Only Investigator
**Goal:** Retrieve evidence from a failed GitHub Actions run and produce a structured diagnosis — zero repository writes.

| Item | Detail |
|---|---|
| **FRs** | FR-01 (GitHub Integration), FR-02 (Evidence Collection), FR-03 (Diagnosis), FR-08 (Model Adapter) |
| **ACs** | AC-01, AC-02, AC-03, AC-04 |
| **Duration** | ~2 weeks |
| **Key Deliverables** | GitHub adapter, model adapter, evidence collector, diagnosis engine, CLI skeleton, basic structured output |

**Milestones:**
1. Project scaffolding (directory structure, pyproject.toml, dev tooling)
2. GitHub adapter: authenticate, fetch run metadata, jobs, bounded log excerpts
3. Evidence collector: extract relevant log snippets, redact secrets
4. Model adapter: interface + first provider (OpenAI-compatible)
5. Diagnosis engine: structured output (category, evidence, confidence, cause)
6. CLI `investigate` command: end-to-end read-only flow
7. Unit tests for each module + 3 fixture-based integration tests

### Phase 2: Policy & Audit
**Goal:** Every tool action passes through deterministic authorization. Actions are recorded. Prohibited operations are denied and testable.

| Item | Detail |
|---|---|
| **FRs** | FR-06 (Policy & Approval), FR-07 (Audit & Reporting) |
| **ACs** | AC-05, AC-06, AC-07, AC-12 |
| **Duration** | ~1.5 weeks |
| **Key Deliverables** | Policy engine, typed tool layer, audit logger with redaction, policy test suite |

**Milestones:**
1. Define tool action taxonomy: `read`, `analyze`, `prepare_patch`, `validate`, `publish`
2. Policy engine: deterministic rules, default-deny for unknowns
3. Tool layer: typed schemas wrapping every external operation
4. Audit logger: structured JSON, automatic secret pattern redaction
5. Integration with orchestrator — all actions route through policy
6. Policy test suite: prohibited action tests (100% block rate target)

### Phase 3: Patch & Validation
**Goal:** Generate minimal patches for supported failure categories and validate them in isolation.

| Item | Detail |
|---|---|
| **FRs** | FR-04 (Remediation Planning), FR-05 (Validation) |
| **ACs** | AC-08, AC-09, AC-10 |
| **Duration** | ~2 weeks |
| **Key Deliverables** | Patch generator, diff display, validation worker, allowlisted command registry |

**Milestones:**
1. Patch generator: model-proposed changes → deterministic path/size validation
2. Diff engine: generate and display unified diffs
3. Validation worker: disposable execution environment (Docker-based)
4. Allowlisted command registry: configurable set of permitted validation commands
5. Credential isolation: ensure no tokens leak into validation environment
6. End-to-end: diagnose → patch → validate flow for 3 failure categories
7. Tests: patch rejection for out-of-scope paths, size violations, credential files

### Phase 4: Human-Reviewed PR
**Goal:** After explicit user approval, create a branch and pull request. Never merge or deploy.

| Item | Detail |
|---|---|
| **FRs** | FR-06 (approval gates) |
| **ACs** | AC-11 |
| **Duration** | ~1 week |
| **Key Deliverables** | Approval flow in CLI, branch/PR creation via GitHub API, merge/deploy path absence tests |

**Milestones:**
1. Approval prompt in CLI with clear diff + risk summary
2. Branch creation on GitHub (deterministic naming)
3. PR creation with structured body (diagnosis, diff, validation results)
4. Negative tests: confirm no merge endpoint, no deploy capability
5. Policy gate: `publish` action requires explicit approval

### Phase 5: Evaluation & Polish
**Goal:** Build a comprehensive evaluation suite, document everything, produce a reproducible demo.

| Item | Detail |
|---|---|
| **FRs** | FR-07 (reporting completeness) |
| **ACs** | AC-13, AC-14 |
| **Duration** | ~1.5 weeks |
| **Key Deliverables** | 20-30 evaluation scenarios, metrics report, README, demo recording |

**Milestones:**
1. Build/curate 20-30 CI failure scenarios across categories
2. Sanitized fixture creation for reproducible offline tests
3. Evaluation runner: automated scenario execution + metrics collection
4. Metrics report: diagnosis accuracy, patch pass rate, block rate, secret leakage
5. README: setup, architecture diagram, threat model, limitations, demo instructions
6. Demo: recorded or live walkthrough of end-to-end flow

---

## 5. Initial Failure Categories (MVP)

Per the PRD's open decisions, start with these 3 categories:

| Category | Example Failures |
|---|---|
| **Dependency Installation** | `pip install` failure, missing package, version conflict, network timeout |
| **Lint / Type-Check** | `ruff` errors, `mypy` type errors, `eslint` failures |
| **Unit Test** | `pytest` assertion failures, missing test fixtures, import errors |

Expand after baseline metrics are established.

---

## 6. Open Decisions & Recommendations

| Decision | Recommendation | Rationale |
|---|---|---|
| **First model provider** | OpenAI GPT-4o-mini via API, with Ollama local fallback | Low cost, good structured output, adapter-preserving |
| **Validation isolation** | Docker containers (`docker run --rm --network=none`) | True isolation, no credentials, disposable, well-understood |
| **Branch/PR in first demo** | Defer to Phase 4 — demo Phase 1-3 first | Diagnosis + validation is the core value; PR creation is mechanical |
| **GitHub API operations** | Map in Phase 1: `GET /repos/.../actions/runs`, `/jobs`, `/logs` | Minimum token permissions: `actions:read`, `contents:read` |
| **Secret redaction patterns** | Regex-based: `GITHUB_TOKEN`, `AWS_*`, `API_KEY`, Bearer tokens, base64-like strings | Start conservative, iterate on false positive rate |

---

## 7. Risk Management

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Incorrect diagnosis | Medium | Medium | Evidence grounding, confidence scores, human review | Diagnosis module |
| Prompt injection via logs | Medium | High | Content-as-data separation, policy outside model | Policy engine |
| Validation environment escape | Low | Critical | Docker isolation, no credentials, network restriction | Validation worker |
| Overbroad GitHub token | Medium | High | Fine-grained PAT, repository-scoped, minimal permissions | GitHub adapter |
| Unbounded API costs | Medium | Medium | Bounded logs, prompt size limits, capped retries | Model adapter |
| Scope creep | High | Medium | Strict adherence to MVP scope; no multi-platform | Project planning |

---

## 8. Timeline Summary

| Phase | Duration | Cumulative |
|---|---|---|
| Phase 1: Read-Only Investigator | 2 weeks | Week 2 |
| Phase 2: Policy & Audit | 1.5 weeks | Week 3.5 |
| Phase 3: Patch & Validation | 2 weeks | Week 5.5 |
| Phase 4: Human-Reviewed PR | 1 week | Week 6.5 |
| Phase 5: Evaluation & Polish | 1.5 weeks | Week 8 |
| **Total estimated MVP** | **~8 weeks** | |

> **Note:** Timeline assumes a single developer working part-time (~20 hrs/week). Adjust for available capacity.

---

## 9. Success Criteria (from PRD)

| Metric | MVP Target |
|---|---|
| Diagnosis quality | ≥ 80% materially correct against known root causes |
| Evidence grounding | 100% of diagnoses have evidence or explicit "insufficient" |
| Patch validation | Establish baseline, then improve |
| Unsafe action blocking | 100% of prohibited actions blocked |
| Secret leakage | Zero known secrets in prompts, logs, or reports |
| Reproducibility | Every eval case has documented rerun instructions |
| Operational visibility | Every incident has a final status and traceable history |

---

## 10. Definition of Done (MVP)

- [ ] A user can investigate a failed GitHub Actions run from the CLI
- [ ] Diagnosis is evidence-backed and can report insufficient evidence
- [ ] Limited patches can be proposed and validated without credential exposure
- [ ] Deterministic policy layer blocks prohibited actions independently of model
- [ ] Remote writes require human approval; merge/deploy not implemented
- [ ] Audit logs and reproducible evaluation suite included
- [ ] Another developer can reproduce the demo from documented setup instructions
