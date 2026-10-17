"""Custom exception hierarchy for Guardrail-CI."""

from __future__ import annotations


class GuardrailError(Exception):
    """Base exception for all Guardrail-CI errors."""


class GitHubError(GuardrailError):
    """Base exception for GitHub API interactions."""


class GitHubAuthError(GitHubError):
    """Raised when authentication to GitHub API fails."""


class GitHubNotFoundError(GitHubError):
    """Raised when a requested GitHub repository, run, or job is not found."""


class GitHubRateLimitError(GitHubError):
    """Raised when GitHub API rate limits are exceeded."""


class RepositoryNotAllowedError(GuardrailError):
    """Raised when an operation targets a repository not present in the allowlist."""


class PolicyDeniedError(GuardrailError):
    """Raised when a requested action violates deterministic security policy."""


class ValidationError(GuardrailError):
    """Raised when isolated patch validation encounters fatal setup or timeout errors."""


class InvalidStateTransitionError(GuardrailError):
    """Raised when attempting an invalid incident state machine transition."""
