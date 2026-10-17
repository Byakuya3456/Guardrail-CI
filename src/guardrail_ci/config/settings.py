"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from guardrail_ci.config.defaults import (
    DEFAULT_AUDIT_LOG_PATH,
    DEFAULT_DATABASE_PATH,
    DEFAULT_MAX_LOG_LINES,
    DEFAULT_MAX_PATCH_SIZE_BYTES,
    DEFAULT_MAX_PROMPT_TOKENS,
    DEFAULT_MODEL_MAX_RETRIES,
    DEFAULT_MODEL_TIMEOUT_SECONDS,
    DEFAULT_VALIDATION_DOCKER_IMAGE,
    DEFAULT_VALIDATION_TIMEOUT_SECONDS,
)


class GitHubSettings(BaseSettings):
    """GitHub API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_",
        env_file=".env",
        extra="ignore",
    )

    token: str = Field(default="", description="Fine-grained GitHub Personal Access Token")
    allowed_repos: list[str] | str = Field(
        default_factory=list,
        description="Allowed repository names in owner/repo format",
    )
    api_base: str = Field(default="https://api.github.com", description="GitHub REST API base URL")
    max_log_lines: int = Field(default=DEFAULT_MAX_LOG_LINES, description="Maximum log lines to retrieve")

    @field_validator("allowed_repos", mode="before")
    @classmethod
    def parse_allowed_repos(cls, value: object) -> list[str]:
        """Support comma-separated string or list for allowed_repos."""
        if isinstance(value, str):
            return [r.strip() for r in value.split(",") if r.strip()]
        if isinstance(value, list):
            return [str(r).strip() for r in value if str(r).strip()]
        return []


class ModelSettings(BaseSettings):
    """LLM provider configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MODEL_",
        env_file=".env",
        extra="ignore",
    )

    provider: str = Field(default="openai", description="Model provider (e.g., openai, ollama)")
    api_base: str = Field(default="https://api.openai.com/v1", description="OpenAI-compatible API base URL")
    api_key: str = Field(default="", description="API key for model access")
    name: str = Field(default="gpt-4o-mini", description="Model identifier")
    max_tokens: int = Field(default=4096, description="Max response tokens")
    timeout_seconds: int = Field(default=DEFAULT_MODEL_TIMEOUT_SECONDS, description="Request timeout in seconds")
    max_retries: int = Field(default=DEFAULT_MODEL_MAX_RETRIES, description="Max retries for transient failures")


class ValidationSettings(BaseSettings):
    """Validation worker configuration."""

    model_config = SettingsConfigDict(
        env_prefix="VALIDATION_",
        env_file=".env",
        extra="ignore",
    )

    timeout_seconds: int = Field(default=DEFAULT_VALIDATION_TIMEOUT_SECONDS, description="Worker execution timeout")
    docker_image: str = Field(default=DEFAULT_VALIDATION_DOCKER_IMAGE, description="Docker image for validation")
    network_disabled: bool = Field(default=True, description="Enforce --network=none in worker container")


class AppSettings(BaseSettings):
    """Top-level application settings combining all modules."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    github: GitHubSettings = Field(default_factory=GitHubSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)
    validation: ValidationSettings = Field(default_factory=ValidationSettings)
    database_path: str = Field(default=DEFAULT_DATABASE_PATH, description="Path to SQLite database")
    audit_log_path: str = Field(default=DEFAULT_AUDIT_LOG_PATH, description="Path to JSONL audit log")
    max_patch_size_bytes: int = Field(default=DEFAULT_MAX_PATCH_SIZE_BYTES, description="Max allowed patch bytes")
    max_prompt_tokens: int = Field(default=DEFAULT_MAX_PROMPT_TOKENS, description="Max tokens per prompt")
