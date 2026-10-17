# Guardrail-CI

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Guardrail-CI** is a security-conscious AI assistant that investigates failed GitHub Actions CI runs, produces evidence-grounded diagnoses, proposes minimal remediation diffs, validates changes in isolated environments, and prepares human-reviewable pull requests, **without ever autonomously merging or deploying code**.

---

## 🔒 Security Principles

1. **The Model is Not the Security Boundary:**
   The AI advises and recommends fixes; a deterministic **Policy Engine** evaluates every operation with a strict **default-deny** policy before any action can be executed.
2. **Untrusted Data Isolation:**
   All logs, workflow files, commit messages, and issue comments are treated as untrusted *data*, preventing prompt injection.
3. **Secret Redaction:**
   Logs and prompts are sanitized against regex-based credential patterns before submission to the LLM or audit storage.
4. **Isolated Validation Worker:**
   Allowlisted validation commands run inside disposable, unprivileged Docker containers (`--network=none`, zero tokens/credentials injected).
5. **No Autonomous Write/Merge/Deploy:**
   Arbitrary shell execution, automatic PR merging, and deployment paths are completely prohibited. Remote repository writes require explicit human approval via interactive CLI prompt.

---

## 🚀 Quickstart

### 1. Installation

```bash
# Clone repository
git clone https://github.com/your-org/guardrail-ci.git
cd guardrail-ci

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install package in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 2. Configuration

Copy the example environment file and configure your tokens:

```bash
cp .env.example .env
```

Set your credentials in `.env`:
* `GITHUB_TOKEN`: Fine-grained personal access token with `actions:read`, `contents:read`.
* `GITHUB_ALLOWED_REPOS`: Repositories allowed for investigation (e.g., `owner/repo-name`).
* `MODEL_API_KEY`: API key for OpenAI, Ollama, or an OpenAI-compatible endpoint.

### 3. Usage

Run an investigation on a failed GitHub Actions run:

```bash
guardrail-ci investigate --repo owner/repo-name --run-id 123456789
```

Output as structured JSON:

```bash
guardrail-ci investigate --repo owner/repo-name --run-id 123456789 --output json
```

---

## 🧪 Testing

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage report
pytest --cov=guardrail_ci tests/
```

---

## 📖 Architecture & Documentation

- [Setup Guide](./setup_guide.md)
- [Security Fixes & Hardening Log](./docs/security_fixes.md)
- [Security Audit Report](./docs/security_audit_report.md)
- [Product Requirements Document (PRD)](./docs/Guardrail-CI_MVP_PRD.md)
- [Project Plan](./docs/plan.md)
- [Implementation Guide](./docs/implementation.md)
