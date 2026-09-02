import pytest

from automation_core.redaction import SENSITIVE_KEY_TERMS, REDACTED, redact


def test_sensitive_term_list_matches_development_contract():
    assert SENSITIVE_KEY_TERMS == (
        "authorization",
        "cookie",
        "password",
        "secret",
        "token",
        "x5sec",
        "x5secdata",
    )


@pytest.mark.parametrize(
    "key",
    [
        "authorization",
        "Authorization",
        "X5Sec",
        "x5secdata",
        "session-token",
        "access_token",
        "PASSWORD_HASH",
        "my.cookie.jar",
    ],
)
def test_sensitive_keys_are_redacted_case_insensitively_at_any_depth(key):
    value = {key: "leak", "safe": {"nested": {key: "leak"}}}

    safe = redact(value)

    assert safe[key] == REDACTED
    assert safe["safe"]["nested"][key] == REDACTED


def test_primitives_and_safe_structures_pass_through():
    value = {
        "count": 3,
        "ratio": 1.5,
        "flag": True,
        "name": "open",
        "none": None,
        "items": [1, "two", {"inner": "x"}],
    }

    assert redact(value) == value


def test_objects_are_replaced_by_type_placeholders():
    class Page:
        pass

    safe = redact({"page": Page(), "items": [Page()]})

    assert safe["page"] == "<Page>"
    assert safe["items"] == ["<Page>"]


def test_to_dict_objects_are_unwrapped_and_recursed():
    class Envelope:
        def to_dict(self):
            return {"token": "leak", "ok": True}

    assert redact(Envelope()) == {"token": REDACTED, "ok": True}


def test_paths_are_serialized_as_strings():
    from pathlib import Path

    assert redact({"artifact": Path("artifacts/run-1/x.png")}) == {
        "artifact": "artifacts/run-1/x.png"
    }
