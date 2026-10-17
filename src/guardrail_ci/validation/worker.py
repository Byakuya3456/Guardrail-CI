"""Isolated validation workers executing allowlisted verification commands."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path

from guardrail_ci.config.settings import ValidationSettings
from guardrail_ci.core.exceptions import ValidationError
from guardrail_ci.core.models import ValidationResult
from guardrail_ci.validation.commands import is_command_allowlisted


class ValidationWorker(ABC):
    """Abstract interface for executing validation checks."""

    @abstractmethod
    def run_check(self, command: str, workspace_path: Path) -> ValidationResult:
        """Run a single validation command in an isolated environment."""
        ...


class DockerValidationWorker(ValidationWorker):
    """Executes validation inside a disposable, unprivileged Docker container.

    Security properties:
    - --network=none prevents data exfiltration.
    - Zero host credentials mounted into the container.
    - Resource & memory bounds.
    - Disposable container removed upon exit (--rm).
    """

    def __init__(self, settings: ValidationSettings) -> None:
        self._settings = settings

    def run_check(self, command: str, workspace_path: Path) -> ValidationResult:
        """Execute allowlisted check in a Docker container."""
        if not is_command_allowlisted(command):
            raise ValidationError(f"Command '{command}' is not in the allowlisted verification registry.")

        resolved_workspace = str(workspace_path.resolve())
        docker_args = [
            "docker",
            "run",
            "--rm",
            "--security-opt=no-new-privileges",
            "--cap-drop=ALL",
            "--memory=512m",
            "--cpus=1",
            "-v",
            f"{resolved_workspace}:/workspace:rw",
            "-w",
            "/workspace",
        ]

        if self._settings.network_disabled:
            docker_args.append("--network=none")

        docker_args.extend([self._settings.docker_image, "sh", "-c", command])

        start_time = time.monotonic()
        try:
            result = subprocess.run(
                docker_args,
                capture_output=True,
                text=True,
                timeout=self._settings.timeout_seconds,
            )
            duration = time.monotonic() - start_time
            return ValidationResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout[:5000],
                stderr=result.stderr[:5000],
                passed=result.returncode == 0,
                duration_seconds=round(duration, 2),
            )
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start_time
            return ValidationResult(
                command=command,
                exit_code=-1,
                stderr=f"Execution timed out after {self._settings.timeout_seconds} seconds.",
                passed=False,
                duration_seconds=round(duration, 2),
            )
        except OSError as e:
            raise ValidationError(f"Failed to launch Docker container: {e}") from e


class IsolatedSubprocessWorker(ValidationWorker):
    """Fallback isolated subprocess worker for local environments lacking Docker daemon.

    Security properties:
    - Environment is strictly sanitized (no tokens, API keys, or host secrets passed).
    - Hard timeouts enforced.
    - Bounded execution output.
    """

    # Safe environment variables allowed to pass through
    SAFE_ENV_VARS = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PYTHONPATH"}

    def __init__(self, timeout_seconds: int = 60) -> None:
        self.timeout_seconds = timeout_seconds

    def run_check(self, command: str, workspace_path: Path) -> ValidationResult:
        """Run command in sanitized subprocess environment."""
        if not is_command_allowlisted(command):
            raise ValidationError(f"Command '{command}' is not in the allowlisted verification registry.")

        # Build clean environment with zero secrets
        clean_env = {k: v for k, v in os.environ.items() if k.upper() in self.SAFE_ENV_VARS}

        start_time = time.monotonic()
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(workspace_path),
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            duration = time.monotonic() - start_time
            return ValidationResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout[:5000],
                stderr=result.stderr[:5000],
                passed=result.returncode == 0,
                duration_seconds=round(duration, 2),
            )
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start_time
            return ValidationResult(
                command=command,
                exit_code=-1,
                stderr=f"Execution timed out after {self.timeout_seconds} seconds.",
                passed=False,
                duration_seconds=round(duration, 2),
            )


def is_docker_available() -> bool:
    """Return True if Docker binary exists and daemon is responsive."""
    if not shutil.which("docker"):
        return False
    try:
        res = subprocess.run(["docker", "info"], capture_output=True, timeout=3)
        return res.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False
