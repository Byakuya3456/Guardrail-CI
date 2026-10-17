# Guardrail-CI Setup Guide

This guide walks you through setting up, configuring, running, and verifying **Guardrail-CI** in both local development and production-like CI/CD environments.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Environment Configuration](#3-environment-configuration)
4. [Setting Up GitHub Credentials](#4-setting-up-github-credentials)
5. [Configuring LLM Providers](#5-configuring-llm-providers)
   - [OpenAI](#option-a-openai)
   - [Local Models via Ollama](#option-b-local-models-via-ollama)
   - [LM Studio / vLLM / LocalAI](#option-c-lm-studio--vllm--localai)
6. [Setting Up Isolated Validation](#6-setting-up-isolated-validation)
   - [Docker Worker (Recommended)](#docker-worker-recommended)
   - [Subprocess Worker (Local Fallback)](#subprocess-worker-local-fallback)
7. [Running Guardrail-CI](#7-running-guardrail-ci)
   - [CLI Commands Overview](#cli-commands-overview)
   - [Investigating a Failed Workflow](#investigating-a-failed-workflow)
   - [Human Approval Gate Workflow](#human-approval-gate-workflow)
   - [Inspecting the Audit Trail](#inspecting-the-audit-trail)
8. [Running Verification & Tests](#8-running-verification--tests)
9. [Troubleshooting & FAQ](#9-troubleshooting--faq)

---

## 1. Prerequisites

Before getting started, make sure your system has:

| Requirement | Minimum Version | Notes |
|:---|:---|:---|
| **Python** | `3.11+` | Tested on Python 3.11 and 3.12 |
| **Git** | `2.30+` | Required for diff parsing and patch generation |
| **Docker** | `20.10+` *(Optional)* | Recommended for network-isolated validation (`--network=none`). If Docker is offline, Guardrail-CI falls back to isolated subprocess execution. |
| **GitHub Account** | N/A | To inspect CI runs and create candidate fix pull requests |
| **LLM Access** | N/A | OpenAI API key, or a local OpenAI-compatible inference server (e.g., Ollama) |

---

## 2. Installation

### 2.1 Clone Repository

```bash
git clone https://github.com/your-org/guardrail-ci.git
cd guardrail-ci
```

### 2.2 Create & Activate Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2.3 Install Dependencies

Install Guardrail-CI in editable mode along with testing, linting, and development dependencies:

```bash
pip install -e ".[dev]"
```

Verify that the CLI command is available:

```bash
guardrail-ci --help
```

---

## 3. Environment Configuration

Copy the sample environment configuration file into `.env`:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

### Configuration Parameters

Open `.env` in your text editor and adjust the settings:

```dotenv
# ==========================================
# GitHub Integration
# ==========================================
GITHUB_TOKEN=ghp_your_github_token_here
# Comma-separated list of permitted repositories (org/repo format)
GITHUB_ALLOWED_REPOS=your-org/repo-a,your-org/repo-b
GITHUB_API_URL=https://api.github.com

# ==========================================
# LLM / Model Provider
# ==========================================
MODEL_PROVIDER=openai
# Leave empty for official OpenAI, or point to http://localhost:11434/v1 for Ollama
MODEL_BASE_URL=
MODEL_API_KEY=sk-your-openai-api-key
MODEL_NAME=gpt-4o-mini
MODEL_TEMPERATURE=0.0

# ==========================================
# Local SQLite Storage
# ==========================================
DATABASE_URL=sqlite:///guardrail.db

# ==========================================
# Append-Only Audit Logging
# ==========================================
AUDIT_LOG_PATH=audit.jsonl

# ==========================================
# Patch Constraints & Policy Enforcement
# ==========================================
PATCH_MAX_MODIFIED_FILES=5
PATCH_MAX_DIFF_LINES=150
PATCH_PROHIBITED_EXTENSIONS=.env,.pem,.key,.crt,.pfx,.cer,.pub,.secret
PATCH_PROHIBITED_DIRECTORIES=.github,.git,ci,scripts/deploy

# ==========================================
# Validation Worker Configuration
# ==========================================
# Options: "docker" or "subprocess"
VALIDATION_WORKER_TYPE=docker
VALIDATION_TIMEOUT_SECONDS=60
VALIDATION_DOCKER_IMAGE=guardrail-ci-worker:latest
```

---

## 4. Setting Up GitHub Credentials

Guardrail-CI adheres to the principle of least privilege. You can use a Fine-Grained Personal Access Token (PAT) or a classic token:

### Minimal Recommended Permissions

1. Visit **GitHub Settings** &rarr; **Developer Settings** &rarr; **Personal Access Tokens** &rarr; **Fine-grained tokens**.
2. Select **Generate new token**.
3. Under **Repository Access**, select **Only select repositories** and pick the repositories Guardrail-CI is authorized to monitor.
4. Under **Repository Permissions**, grant:
   - `Actions`: **Read-only** (to read workflow runs and download step logs)
   - `Contents`: **Read and write** (Read to inspect code; Write only to push candidate fix branches)
   - `Pull requests`: **Read and write** (to open candidate remediation pull requests)
5. Copy the generated token into `.env` as `GITHUB_TOKEN`.
6. Add the allowed repository slug(s) to `GITHUB_ALLOWED_REPOS` (e.g. `GITHUB_ALLOWED_REPOS=octocat/Hello-World`).

> [!IMPORTANT]
> Guardrail-CI's GitHub client is strictly bounded: it contains **no methods** for triggering deployments, modifying branch protection rules, executing workflow dispatches, or merging pull requests.

---

## 5. Configuring LLM Providers

Guardrail-CI utilizes an OpenAI-compatible interface, enabling both commercial and self-hosted models.

### Option A: OpenAI

For standard OpenAI cloud inference:

```dotenv
MODEL_PROVIDER=openai
MODEL_BASE_URL=
MODEL_API_KEY=sk-proj-your-openai-api-key
MODEL_NAME=gpt-4o-mini
MODEL_TEMPERATURE=0.0
```

### Option B: Local Models via Ollama

To run completely offline without sending code or sanitized logs to external cloud APIs:

1. Install [Ollama](https://ollama.ai/).
2. Pull your model of choice:
   ```bash
   ollama pull llama3.1
   ```
3. Start the Ollama server:
   ```bash
   ollama serve
   ```
4. Configure `.env`:
   ```dotenv
   MODEL_PROVIDER=ollama
   MODEL_BASE_URL=http://localhost:11434/v1
   MODEL_API_KEY=ollama
   MODEL_NAME=llama3.1
   MODEL_TEMPERATURE=0.0
   ```

### Option C: LM Studio / vLLM / LocalAI

Any server that exposes `/v1/chat/completions` works out of the box:

```dotenv
MODEL_PROVIDER=openai
MODEL_BASE_URL=http://localhost:1234/v1
MODEL_API_KEY=not-needed
MODEL_NAME=qwen2.5-coder-7b-instruct
MODEL_TEMPERATURE=0.0
```

---

## 6. Setting Up Isolated Validation

Guardrail-CI validates generated patches inside isolated environments with strict command allowlists (`pytest`, `npm test`, `cargo test`, `go test`, `python -m unittest`).

### Docker Worker (Recommended)

Build the unprivileged worker container image:

```bash
docker build -t guardrail-ci-worker:latest -f docker/Dockerfile.worker .
```

Verify the image:
```bash
docker images guardrail-ci-worker
```

The container automatically runs with:
- `--network=none` (Zero network access, blocking data exfiltration)
- Non-root user (`uid 1000`)
- Dropped capabilities (`--cap-drop=ALL`)
- Read-only root filesystem with a temporary working directory mount

### Subprocess Worker (Local Fallback)

If Docker Desktop is not running or unavailable in your development environment, Guardrail-CI seamlessly falls back to the `IsolatedSubprocessWorker`. To force this explicitly in `.env`:

```dotenv
VALIDATION_WORKER_TYPE=subprocess
```

---

## 7. Running Guardrail-CI

### CLI Commands Overview

```text
Usage: guardrail-ci [OPTIONS] COMMAND [ARGS]...

  Guardrail-CI: Deterministic security-first CI incident remediator.

Options:
  --help  Show this message and exit.

Commands:
  investigate  Investigate a failed GitHub Actions CI run.
  status       Check status and details of an investigated incident.
```

### Investigating a Failed Workflow

Run an investigation against a failed CI run:

```bash
guardrail-ci investigate --repo your-org/repo-name --run-id 123456789
```

Output as structured machine-readable JSON:

```bash
guardrail-ci investigate --repo your-org/repo-name --run-id 123456789 --output json
```

### Human Approval Gate Workflow

When an investigation successfully diagnoses a failure, passes policy checks, and validates the patch:

1. Guardrail-CI prints the unified diff and verification results.
2. The interactive Human Gate prompts:
   ```text
   Review Patch Diff:
   --- a/src/parser.py
   +++ b/src/parser.py
   @@ -10,1 +10,1 @@
   -    return int(val)
   +    return int(val) if val is not None else 0

   Proceed with creating candidate branch and Pull Request? [y/N]:
   ```
3. If confirmed (`y`), Guardrail-CI pushes candidate branch `guardrail-fix/run-123456789` and opens a draft PR.
4. If declined (`N`), Guardrail-CI records the rejection in `audit.jsonl` and terminates cleanly without modifying the remote repository.

### Inspecting the Audit Trail

Every event, redaction count, policy decision, validation output, and human gate decision is logged to an immutable append-only JSONL log (`audit.jsonl`):

```bash
# View recent audit events
tail -n 20 audit.jsonl

# Or pretty-print with jq
tail -n 5 audit.jsonl | jq .
```

---

## 8. Running Verification & Tests

Guardrail-CI comes with a comprehensive test suite covering unit tests, policy engines, isolated execution, and an evaluation catalog with 22 adversarial and operational scenarios.

### Run All Unit and Integration Tests

```bash
pytest tests/unit/ -v
```

### Run With Code Coverage

```bash
pytest --cov=guardrail_ci --cov-report=term-missing tests/
```

### Run the Evaluation Suite (22 Scenarios)

The evaluation catalog tests both standard remediation paths and aggressive adversarial injection attempts (prompt injections, path traversals, secret leakage, unauthorized branch edits):

```bash
pytest tests/evaluation/ -v
```

All 22 scenarios assert:
- `100%` blocking of prohibited actions (zero leaks or prohibited commands allowed)
- Strict grounding of diagnoses in actual log evidence
- Compliance with default-deny policy constraints

### Run Linters & Type Checking

```bash
# Code style and import order
ruff check .

# Static type checks
mypy src
```

---

## 9. Troubleshooting & FAQ

### Q: Why did Guardrail-CI reject a proposed patch to `.github/workflows/ci.yml`?
**A:** This is by design. The policy engine strictly forbids modifications to sensitive directories (`.github`, `.git`, `ci`, `scripts/deploy`) to prevent privilege escalation and workflow tampering.

### Q: What happens if Docker is not running?
**A:** If `VALIDATION_WORKER_TYPE=docker` but the Docker daemon is unreachable, Guardrail-CI logs a warning and automatically falls back to `IsolatedSubprocessWorker` using temporary directories on your host, ensuring development workflow continuity.

### Q: How does Guardrail-CI prevent API keys from leaking into LLM prompts?
**A:** Before logs or context are packaged into model prompts or written to disk, the `SecretRedactor` scans the text against patterns for GitHub tokens, AWS keys, generic bearer tokens, private keys, and passwords, replacing them with sanitized placeholders like `[REDACTED_GH_TOKEN]`.

### Q: Can Guardrail-CI automatically merge PRs?
**A:** **No.** Guardrail-CI never autonomously merges or deploys code. All proposed remediations must be approved by a human engineer through the standard GitHub code review process.
