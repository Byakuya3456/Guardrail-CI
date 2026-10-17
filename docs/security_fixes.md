# Guardrail-CI Security Fixes & Hardening Log

This document records the security vulnerabilities identified during the application security audit of **Guardrail-CI**, the root causes, the remediation patches applied, and the corresponding regression tests.

---

## Summary of Applied Fixes

| Advisory ID | Severity | Category | Affected Component | Status |
|:---|:---:|:---|:---|:---:|
| **SEC-01** | **HIGH** | Path Traversal / Arbitrary File Overwrite | `guardrail_ci.remediation.constraints`<br>`guardrail_ci.remediation.patch` | **RESOLVED** |
| **SEC-03** | **LOW** | Prompt Delimiter Fencing Escape | `guardrail_ci.adapters.model.prompts` | **RESOLVED** |
| **SEC-04** | **LOW** | Container Privilege Hardening | `guardrail_ci.validation.worker` | **RESOLVED** |
| **SEC-05** | **INFO** | Documentation Alignment | `setup_guide.md` | **RESOLVED** |

---

## 1. SEC-01: Path Traversal & Arbitrary File Overwrite Prevention

### Threat Description & Root Cause
In initial builds, proposed remediation patch file paths were normalized using `PurePosixPath(path).as_posix()`. However:
1. `is_path_allowed()` did not verify whether a path was absolute (`/etc/passwd`, `C:/Windows/System32/...`) or contained relative directory traversal sequences (`../../evil.py`).
2. In Python's `pathlib.Path`, concatenating an absolute path using `/` (`workspace_dir / patch_file.path`) silently discards `workspace_dir` and targets the root of the filesystem.
3. If an adversarial prompt injection or corrupted model output proposed a patch outside the workspace, `apply_patch_to_workspace()` would write files outside the intended sandbox boundary.

### Patches Applied

#### A. Input Validation (`src/guardrail_ci/remediation/constraints.py`)
Added deterministic checks to reject:
- Empty or whitespace paths
- Paths containing drive letters (e.g., `C:`) or root slashes (`/`)
- Paths flagged as `is_absolute()` by `PurePosixPath`
- Paths whose path components (`parts`) contain directory traversal tokens (`..`)

```python
def is_path_allowed(path: str) -> tuple[bool, str]:
    if not path or not path.strip():
        return False, "Path cannot be empty."

    raw_path = path.strip().replace("\\", "/")

    # Prohibit drive letters, root slashes, or absolute paths
    if ":" in raw_path or raw_path.startswith("/"):
        return False, f"Absolute path '{path}' is strictly prohibited."

    posix = PurePosixPath(raw_path)
    if posix.is_absolute():
        return False, f"Absolute path '{path}' is strictly prohibited."

    # Prohibit directory traversal tokens
    if ".." in posix.parts:
        return False, f"Directory traversal sequence in path '{path}' is strictly prohibited."
    ...
```

#### B. Workspace Boundary Confinement (`src/guardrail_ci/remediation/patch.py`)
Added runtime confinement verification before any file write operation occurs:

```python
def apply_patch_to_workspace(workspace_dir: Path, plan: RemediationPlan) -> list[str]:
    modified_paths: list[str] = []
    resolved_workspace = workspace_dir.resolve()

    for patch_file in plan.files:
        cleaned_rel_path = patch_file.path.strip().lstrip("/\\")
        target_path = (workspace_dir / cleaned_rel_path).resolve()

        if not target_path.is_relative_to(resolved_workspace):
            raise ValueError(
                f"Path traversal security violation: '{patch_file.path}' escapes workspace directory."
            )

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(patch_file.modified_content, encoding="utf-8")
        modified_paths.append(patch_file.path)
    return modified_paths
```

### Verification & Tests
- Added test cases in `tests/unit/test_constraints.py` asserting that `../../etc/passwd`, `/etc/shadow`, `C:/Windows/system.ini`, `src/../../evil.py`, and UNC paths (`\\evil\share\file.py`) are strictly rejected.
- Added `test_apply_patch_blocks_path_traversal` in `tests/unit/test_patch.py` asserting that attempting to apply a traversal patch raises `ValueError: Path traversal security violation`.

---

## 2. SEC-03: Prompt Delimiter Fencing Escape

### Threat Description & Root Cause
Evidence logs collected from GitHub Actions are enclosed in prompt boundaries:
```text
--- BEGIN UNTRUSTED EVIDENCE DATA ---
[ ... JSON Payload ... ]
--- END UNTRUSTED EVIDENCE DATA ---
```
If an adversary intentionally created a CI log line containing the literal string `--- END UNTRUSTED EVIDENCE DATA ---`, an LLM could misinterpret subsequent lines as system instructions rather than untrusted data.

### Patches Applied (`src/guardrail_ci/adapters/model/prompts.py`)
All log excerpts embedded into the JSON payload are now sanitized to disarm triple dashes:

```python
evidence_payload = [
    {
        "job": item.job,
        "step": item.step,
        "source": item.source,
        "sanitized_excerpt": item.excerpt.replace("---", "- - -"),
    }
    for item in evidence
]
```

---

## 3. SEC-04: Container Execution Hardening

### Threat Description & Root Cause
While `DockerValidationWorker` previously specified `--network=none`, `--memory=512m`, and `--cpus=1`, it lacked explicit Linux capability drops and privilege escalation prevention.

### Patches Applied (`src/guardrail_ci/validation/worker.py`)
Added mandatory container security options to `docker_args`:
- `--security-opt=no-new-privileges`: Prevents setuid binaries or container processes from acquiring elevated permissions.
- `--cap-drop=ALL`: Drops all default Linux kernel capabilities inside the disposable validation container.

```python
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
```

---

## 4. SEC-05: Documentation Reference Alignment

### Issue & Resolution
- In `setup_guide.md`, the Docker build instruction referenced `docker/Dockerfile.worker`.
- Corrected the path to match the repository's actual file: `docker/Dockerfile.validator`.

---

## 5. Security Regression Test Results

Following the application of the above fixes, all automated test suites and static analysis tools pass with zero errors:

```bash
# Test Execution
pytest tests/ -v
# Outcome: 51 passed in 5.62s

# Static Analysis & Type Checking
ruff check .
mypy src
# Outcome: All checks passed! Success: no issues found in 39 source files.
```
