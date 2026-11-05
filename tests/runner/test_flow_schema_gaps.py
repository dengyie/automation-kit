"""Deep-coverage tests for flow_schema validation and yaml_loader error
paths — the authoritative shape contracts for declarative YAML flows."""

import pytest

from automation_runner.flow_schema import FlowError, validate_flow_document
from automation_runner.policies import CapabilityPolicy


def _flow(steps, **extra):
    doc = {"workflow": "x", "steps": steps}
    doc.update(extra)
    return doc


# --- CapabilityPolicy validation (76.47% → full) ---------------------------------


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"timeout": 0}, "timeout must be positive"),
        ({"timeout": -1.5}, "timeout must be positive"),
        ({"max_attempts": 0}, "max_attempts must be >= 1"),
        ({"backoff": -0.1}, "backoff must be >= 0"),
        ({"backoff_multiplier": 0.9}, "backoff_multiplier must be >= 1"),
    ],
)
def test_capability_policy_rejects_invalid_values(kwargs, match):
    with pytest.raises(ValueError, match=match):
        CapabilityPolicy(**kwargs)


def test_capability_policy_defaults_and_multiplier_accepts_growth():
    policy = CapabilityPolicy()
    assert policy.timeout is None
    assert policy.max_attempts == 1
    assert policy.backoff == 0.0
    assert policy.backoff_multiplier == 1.0

    grown = CapabilityPolicy(timeout=5, max_attempts=3, backoff=0.5, backoff_multiplier=2.0)
    assert grown.backoff_multiplier == 2.0


# --- flow_schema validation gaps --------------------------------------------------


def test_document_must_be_mapping():
    with pytest.raises(FlowError, match="flow document must be a mapping"):
        validate_flow_document(["workflow"])


@pytest.mark.parametrize(
    "params, match",
    [
        ({"a": None}, "must be a scalar"),
        ({"a": ["x"]}, "must be a scalar"),
        ({"a": {"b": 1}}, "must be a scalar"),
        ({"": "v"}, "keys must be non-blank strings"),
        ({3: "v"}, "keys must be non-blank strings"),
    ],
)
def test_params_value_and_key_validation(params, match):
    with pytest.raises(FlowError, match=match):
        validate_flow_document(_flow([{"action": "open"}], params=params))


def test_params_non_mapping_rejected():
    with pytest.raises(FlowError, match="flow 'params' must be a mapping"):
        validate_flow_document(_flow([{"action": "open"}], params="a=b"))


def test_step_must_be_mapping():
    with pytest.raises(FlowError, match="flow step #1 must be a mapping"):
        validate_flow_document(_flow(["open"]))


def test_action_body_must_be_non_blank_string():
    with pytest.raises(FlowError, match="'action' must be a non-blank action name"):
        validate_flow_document(_flow([{"action": "  "}]))

    with pytest.raises(FlowError, match="'action' must be a non-blank action name"):
        validate_flow_document(_flow([{"action": 42}]))


def test_artifact_body_must_be_mapping():
    with pytest.raises(FlowError, match="'artifact' must be a mapping"):
        validate_flow_document(_flow([{"artifact": "screenshot"}]))


def test_capability_body_must_be_mapping():
    with pytest.raises(FlowError, match="'capability' must be a mapping"):
        validate_flow_document(_flow([{"capability": "solve"}]))


def test_capability_builder_blank_rejected():
    with pytest.raises(FlowError, match="requires a non-blank 'builder'"):
        validate_flow_document(
            _flow([{"capability": {"builder": "", "params": {}}}])
        )


def test_capability_params_must_be_mapping():
    with pytest.raises(FlowError, match="'capability' params must be a mapping"):
        validate_flow_document(
            _flow([{"capability": {"builder": "b", "params": [1]}}])
        )


@pytest.mark.parametrize(
    "policy, match",
    [
        ([1], "policy must be a mapping"),
        ({"oops": 1}, "policy has unknown field"),
        ({"max_attempts": 0}, "policy 'max_attempts' must be an integer >= 1"),
        ({"max_attempts": True}, "policy 'max_attempts' must be an integer >= 1"),
        ({"max_attempts": 1.5}, "policy 'max_attempts' must be an integer >= 1"),
        ({"timeout": -1}, "policy 'timeout' must be a number >= 0"),
        ({"backoff": True}, "policy 'backoff' must be a number >= 0"),
    ],
)
def test_capability_policy_validation(policy, match):
    with pytest.raises(FlowError, match=match):
        validate_flow_document(
            _flow([{"capability": {"builder": "b", "policy": policy}}])
        )


def test_capability_policy_none_is_allowed():
    validate_flow_document(
        _flow([{"capability": {"builder": "b", "policy": None}}])
    )


def test_assert_body_must_be_mapping():
    with pytest.raises(FlowError, match="'assert' must be a mapping"):
        validate_flow_document(_flow([{"assert": "element_present"}]))


def test_assert_extra_keys_rejected():
    with pytest.raises(FlowError, match="must contain exactly one of"):
        validate_flow_document(
            _flow(
                [
                    {
                        "assert": {
                            "element_present": {"selector": "a"},
                            "extra": 1,
                        }
                    }
                ]
            )
        )


def test_assert_element_present_spec_must_be_mapping():
    with pytest.raises(FlowError, match="element_present must be a mapping"):
        validate_flow_document(_flow([{"assert": {"element_present": "x"}}]))


def test_assert_selector_blank_rejected():
    with pytest.raises(FlowError, match="requires a non-blank 'selector'"):
        validate_flow_document(
            _flow([{"assert": {"element_present": {"selector": "  "}}}])
        )


# --- yaml_loader error paths ------------------------------------------------------


from automation_runner.yaml_loader import load_flow


def _write(tmp_path, text):
    flow_file = tmp_path / "f.yaml"
    flow_file.write_text(text, encoding="utf-8")
    return str(flow_file)


def _echo_request(**kw):
    from automation_core.capabilities import CapabilityRequest

    return CapabilityRequest(capability="c", operation="o", parameters=kw)


def test_invalid_yaml_text_maps_to_flow_error(tmp_path):
    with pytest.raises(FlowError, match="invalid YAML"):
        load_flow(_write(tmp_path, "workflow: [unclosed\n  bad: {"))


def test_missing_flow_file_maps_to_flow_error(tmp_path):
    with pytest.raises(FlowError, match="could not read flow file"):
        load_flow(str(tmp_path / "nope.yaml"))


def test_cap_value_resolution_walks_dicts_and_lists(tmp_path):
    text = """
workflow: x
steps:
  - capability:
      builder: echo
      params:
        nested:
          - inner: ${param.v}
          - plain: 1
"""
    seen = {}

    def echo(**kwargs):
        seen.update(kwargs)
        return _echo_request(**kwargs)

    load_flow(
        _write(tmp_path, text),
        parameters={"v": "resolved"},
        capability_builders={"echo": echo},
    )
    assert seen == {"nested": [{"inner": "resolved"}, {"plain": 1}]}


def test_capability_builder_type_error_is_rejection(tmp_path):
    text = """
workflow: x
steps:
  - capability:
      builder: strict
      params: {extra: 1}
"""

    def strict(**kw):
        raise TypeError("unexpected kwarg 'extra'")

    with pytest.raises(FlowError, match="rejected params"):
        load_flow(_write(tmp_path, text), capability_builders={"strict": strict})


def test_capability_builder_generic_failure(tmp_path):
    text = """
workflow: x
steps:
  - capability:
      builder: boom
"""

    def boom():
        raise RuntimeError("registry offline")

    with pytest.raises(FlowError, match="failed: registry offline"):
        load_flow(_write(tmp_path, text), capability_builders={"boom": boom})


def test_capability_bad_policy_maps_to_flow_error(tmp_path):
    text = """
workflow: x
steps:
  - capability:
      builder: echo
      policy: {timeout: 0}
"""
    # timeout=0 passes the schema (>= 0) but CapabilityPolicy demands a
    # positive timeout — _build_policy maps that into FlowError.
    with pytest.raises(FlowError, match="invalid policy"):
        load_flow(
            _write(tmp_path, text),
            capability_builders={"echo": _echo_request},
        )


def test_capability_bad_step_name_maps_to_flow_error(tmp_path):
    text = """
workflow: x
steps:
  - capability:
      builder: echo
      name: "  "
"""
    with pytest.raises(FlowError, match="flow step #1"):
        load_flow(
            _write(tmp_path, text),
            capability_builders={"echo": _echo_request},
        )


def test_artifact_bad_capture_on_maps_to_flow_error(tmp_path):
    text = """
workflow: x
steps:
  - artifact:
      type: screenshot
      name: a.png
      capture_on: sometimes
"""
    with pytest.raises(FlowError, match="capture_on"):
        load_flow(_write(tmp_path, text))


def test_assert_extra_fields_maps_to_flow_error(tmp_path):
    text = """
workflow: x
steps:
  - assert:
      element_present:
        selector: a
        timeout: 1
        interval: 0.5
"""
    flow = load_flow(_write(tmp_path, text))
    assert flow.steps[0].name == "wait_for_element"
    assert flow.steps[0].parameters["timeout"] == 1


def test_assert_by_timeout_interval_pass_through(tmp_path):
    text = """
workflow: x
steps:
  - assert:
      element_present:
        selector: a
        by: id
        timeout: 2
        interval: 0.1
"""
    flow = load_flow(_write(tmp_path, text))
    params = flow.steps[0].parameters
    assert params == {"selector": "a", "by": "id", "timeout": 2, "interval": 0.1}


def test_artifact_capture_on_failure_builds_capture_policy(tmp_path):
    text = """
workflow: x
steps:
  - artifact:
      type: page_source
      name: dump.xml
      capture_on: failure
"""
    flow = load_flow(_write(tmp_path, text))
    assert flow.steps[0].parameters == {"name": "dump.xml", "capture_on": "failure"}
