import pytest

from automation_core.execution import ExecutionFailure, FailureCategory


def test_failure_serializes_stable_category_and_safe_details():
    failure = ExecutionFailure(
        category=FailureCategory.PROVIDER,
        code="provider_exception",
        message="provider execution failed",
        retryable=True,
        source="slidex",
        details={"cookie": "private", "error_type": "RuntimeError"},
    )

    assert failure.to_dict() == {
        "category": "provider",
        "code": "provider_exception",
        "message": "provider execution failed",
        "retryable": True,
        "source": "slidex",
        "details": {"cookie": "[redacted]", "error_type": "RuntimeError"},
    }


def test_failure_rejects_blank_public_fields():
    with pytest.raises(ValueError, match="code"):
        ExecutionFailure(
            category=FailureCategory.TIMEOUT,
            code="",
            message="timed out",
            retryable=True,
            source="runtime",
        )

    with pytest.raises(ValueError, match="category"):
        ExecutionFailure(
            category="unknown",
            code="timeout",
            message="timed out",
            retryable=True,
            source="runtime",
        )
