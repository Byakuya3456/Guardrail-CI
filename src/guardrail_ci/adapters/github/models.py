"""Pydantic models representing GitHub Actions REST API entities."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    """A step within a GitHub Actions job."""

    name: str = Field(description="Step name")
    status: str = Field(description="queued, in_progress, completed")
    conclusion: str | None = Field(default=None, description="success, failure, skipped, cancelled")
    number: int = Field(description="Step sequence number")
    started_at: datetime | None = None
    completed_at: datetime | None = None


class WorkflowJob(BaseModel):
    """A job within a GitHub Actions workflow run."""

    id: int = Field(description="Unique job identifier")
    run_id: int = Field(description="Parent workflow run ID")
    name: str = Field(description="Job name")
    status: str = Field(description="queued, in_progress, completed")
    conclusion: str | None = Field(default=None, description="success, failure, cancelled")
    started_at: datetime | None = None
    completed_at: datetime | None = None
    steps: list[WorkflowStep] = Field(default_factory=list)


class WorkflowRun(BaseModel):
    """A workflow run execution metadata."""

    id: int = Field(description="Unique run identifier")
    name: str = Field(description="Workflow name")
    head_branch: str | None = None
    head_sha: str | None = None
    event: str = Field(description="Trigger event: push, pull_request, workflow_dispatch")
    status: str = Field(description="completed, in_progress, queued")
    conclusion: str | None = Field(default=None, description="success, failure, cancelled, timed_out")
    html_url: str = Field(default="")
    created_at: datetime | None = None
    updated_at: datetime | None = None
