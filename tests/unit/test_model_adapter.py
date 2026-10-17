"""Unit tests for the OpenAI-compatible model adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

from guardrail_ci.adapters.model.openai_compat import OpenAICompatAdapter
from guardrail_ci.config.settings import ModelSettings
from guardrail_ci.core.models import EvidenceItem, FailureCategory


def test_diagnose_empty_evidence_returns_insufficient_evidence() -> None:
    settings = ModelSettings(api_key="mock", api_base="http://mock")
    adapter = OpenAICompatAdapter(settings, client=MagicMock())

    diagnosis = adapter.diagnose([], {"repository": "owner/repo", "run_id": 123})
    assert diagnosis.failure_category == FailureCategory.INSUFFICIENT_EVIDENCE
    assert diagnosis.confidence == 0.0
    assert len(diagnosis.unresolved_questions) > 0


def test_diagnose_successful_json_parsing() -> None:
    settings = ModelSettings(api_key="mock", api_base="http://mock")
    mock_client = MagicMock()

    mock_choice = MagicMock()
    mock_choice.message.content = """
    {
      "failure_category": "unit_test",
      "summary": "AssertionError in test_auth.py line 42",
      "likely_root_cause": "Token expired in test fixture",
      "confidence": 0.85,
      "recommended_actions": ["Refresh expired test token fixture"],
      "unresolved_questions": []
    }
    """
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    adapter = OpenAICompatAdapter(settings, client=mock_client)
    evidence = [
        EvidenceItem(
            job="test",
            step="Run pytest",
            excerpt="AssertionError: token expired",
            source="job:1/step:2",
            is_observation=True,
        )
    ]

    diagnosis = adapter.diagnose(evidence, {"repository": "owner/repo", "run_id": 123})
    assert diagnosis.failure_category == FailureCategory.UNIT_TEST
    assert diagnosis.confidence == 0.85
    assert len(diagnosis.evidence) == 1
    assert "AssertionError" in diagnosis.evidence[0].excerpt


def test_diagnose_handles_model_api_error_gracefully() -> None:
    settings = ModelSettings(api_key="mock", api_base="http://mock")
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("OpenAI rate limit / network error")

    adapter = OpenAICompatAdapter(settings, client=mock_client)
    evidence = [
        EvidenceItem(
            job="test",
            step="Run pytest",
            excerpt="Some error",
            source="job:1/step:1",
            is_observation=True,
        )
    ]

    diagnosis = adapter.diagnose(evidence, {"repository": "owner/repo", "run_id": 123})
    assert diagnosis.failure_category == FailureCategory.UNKNOWN
    assert diagnosis.confidence == 0.0
    assert "OpenAI rate limit" in diagnosis.unresolved_questions[0]
