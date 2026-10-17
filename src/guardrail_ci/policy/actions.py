"""Action types and taxonomy for policy evaluation."""

from __future__ import annotations

from enum import Enum


class ActionType(str, Enum):
    """Categorized tool actions subject to deterministic policy checks."""

    # Allowed operations (Read-only / Sandbox)
    READ = "read"                     # Read metadata/logs from GitHub
    ANALYZE = "analyze"               # Invoke LLM adapter for diagnosis
    PREPARE_PATCH = "prepare_patch"   # Generate minimal diff within constraints
    VALIDATE = "validate"             # Run allowlisted tests in isolated container

    # Operations requiring explicit human approval
    PUBLISH = "publish"               # Create remote branch / pull request

    # Strictly prohibited operations
    EXECUTE_SHELL = "execute_shell"         # Arbitrary host or model shell command
    MERGE = "merge"                         # Autonomous PR merge
    DEPLOY = "deploy"                       # Production deployment / release
    MODIFY_SECURITY = "modify_security"     # Tamper with workflows, scanner, permissions
