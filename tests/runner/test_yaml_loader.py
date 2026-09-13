import json
from pathlib import Path

import pytest

from automation_core.capabilities import CapabilityRequest
from automation_runner import cli
from automation_runner.flow_schema import FlowError
from automation_runner.policies import CapabilityPolicy
from automation_runner.schemas import load_report_schema
from automation_runner.steps import WorkflowStep
from automation_runner.yaml_loader import load_flow


FLOW = """
workflow: damai-web-flow
params:
  host: example.test
  path: /damai
steps:
  - action: open
    url: https://${param.host}${param.path}
  - assert:
      element_present:
        selector: .buy-btn
        by: css selector
        timeout: 3
  - artifact:
      type: screenshot
      name: page.png
      capture_on: failure
  - action: click
    selector: .buy-btn
"""


def write_flow(tmp_path, text):
    flow_file = tmp_path / "flow.yaml"
    flow_file.write_text(text, encoding="utf-8")
    return str(flow_file)


def test_load_flow_maps_all_step_kinds(tmp_path):
    flow = load_flow(write_flow(tmp_path, FLOW))

    assert flow.workflow_name == "damai-web-flow"
    kinds = [(step.kind, step.name) for step in flow.steps]
    assert kinds == [
        ("action", "open"),
        ("action", "wait_for_element"),
        ("artifact", "screenshot"),
        ("action", "click"),
    ]
    assert flow.steps[0].parameters == {
        "url": "https://example.test/damai"
    }
    assert flow.steps[1].parameters == {
        "selector": ".buy-btn",
        "by": "css selector",
        "timeout": 3,
    }
    assert flow.steps[2].parameters == {
        "name": "page.png",
        "capture_on": "failure",
    }


def test_cli_params_override_yaml_defaults(tmp_path):
    flow = load_flow(
        write_flow(tmp_path, FLOW),
        parameters={"path": "/other"},
    )

    assert flow.steps[0].parameters["url"] == "https://example.test/other"


def test_env_interpolation(monkeypatch, tmp_path):
    monkeypatch.setenv("DAMAI_URL", "https://env.example.test")
    text = """
workflow: env-flow
steps:
  - action: open
    url: ${env.DAMAI_URL}
"""
    flow = load_flow(write_flow(tmp_path, text), env=dict(__import__("os").environ))

    assert flow.steps[0].parameters["url"] == "https://env.example.test"


def test_capability_step_uses_builder_registry(tmp_path):
    def slider_builder(*, provider="auto", page=None):
        return CapabilityRequest(
            capability="visual.challenge",
            operation="solve",
            parameters={"provider": provider, "page": page},
        )

    text = """
workflow: cap-flow
steps:
  - capability:
      builder: slider_default
      name: solve-slider
      params:
        provider: slidex
      policy:
        timeout: 15
        max_attempts: 2
        backoff: 0.5
"""
    flow = load_flow(
        write_flow(tmp_path, text),
        capability_builders={"slider_default": slider_builder},
    )

    (step,) = flow.steps
    assert step.kind == "capability"
    assert step.name == "solve-slider"
    assert step.request.parameters["provider"] == "slidex"
    assert step.policy == CapabilityPolicy(
        timeout=15.0, max_attempts=2, backoff=0.5
    )


def test_capability_default_name_is_builder_id(tmp_path):
    def builder():
        return CapabilityRequest(
            capability="visual.challenge", operation="solve", parameters={}
        )

    text = """
workflow: cap-flow
steps:
  - capability:
      builder: slider_default
"""
    flow = load_flow(
        write_flow(tmp_path, text),
        capability_builders={"slider_default": builder},
    )

    assert flow.steps[0].name == "slider_default"
    assert flow.steps[0].policy == CapabilityPolicy()


def test_unknown_capability_builder_is_assembly_error(tmp_path):
    text = """
workflow: cap-flow
steps:
  - capability:
      builder: missing_builder
"""
    with pytest.raises(FlowError, match="unknown capability builder"):
        load_flow(write_flow(tmp_path, text))


def test_builder_returning_wrong_type_is_rejected(tmp_path):
    text = """
workflow: cap-flow
steps:
  - capability:
      builder: bad
"""
    with pytest.raises(FlowError, match="must return CapabilityRequest"):
        load_flow(
            write_flow(tmp_path, text),
            capability_builders={"bad": lambda: {"not": "a request"}},
        )


@pytest.mark.parametrize(
    "text, match",
    [
        ("workflow: x\nsteps: []\n", "'steps' must be a non-empty list"),
        ("params: {}\n", "flow 'workflow' must be a non-blank string"),
        (
            "workflow: x\nsteps:\n  - tap: .btn\n",
            "must declare exactly one of",
        ),
        (
            "workflow: x\nsteps:\n  - action: click\n    artifact: {type: screenshot, name: a.png}\n",
            "declares multiple step markers",
        ),
        (
            "workflow: x\nsteps:\n  - action: open\n    url: ${param.nope}\n",
            "unknown flow parameter: nope",
        ),
        (
            "workflow: x\nsteps:\n  - action: open\n    url: ${env.NOPE_VAR}\n",
            "unknown environment variable: NOPE_VAR",
        ),
        (
            "workflow: x\nsteps:\n  - artifact: {type: screenshot}\n",
            "requires a non-blank 'name'",
        ),
        (
            "workflow: x\nsteps:\n  - artifact: {type: screenshot, name: a.png, capture_on: sometimes}\n",
            "capture_on must be 'always' or 'failure'",
        ),
        (
            "workflow: x\nsteps:\n  - assert: {text_visible: {selector: a}}\n",
            "must contain exactly one of",
        ),
        (
            "workflow: x\nsteps:\n  - capability: {operation: solve}\n",
            "requires a non-blank 'builder'",
        ),
        (
            "workflow: x\nsteps:\n  - capability:\n      builder: b\n      policy: {timeout: -1}\n",
            "policy 'timeout' must be a number >= 0",
        ),
    ],
)
def test_invalid_documents_are_assembly_errors(tmp_path, text, match):
    with pytest.raises(FlowError, match=match):
        load_flow(write_flow(tmp_path, text))


def test_yaml_dependency_missing_is_clear_error(tmp_path, monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "yaml", None)
    with pytest.raises(FlowError, match="automation-kit\\[yaml\\]"):
        load_flow(write_flow(tmp_path, FLOW))


def test_flow_schema_resource_is_loadable():
    from automation_runner.flow_schema import load_flow_schema

    schema = load_flow_schema()

    assert schema["$id"] == "automation-runner/flow-schema-v1"


def test_yaml_flow_equivalent_to_python_steps(tmp_path):
    """YAML is a description layer: same steps, same report shape."""
    text = """
workflow: equiv-flow
steps:
  - action: open
    url: https://example.test
  - artifact:
      type: screenshot
      name: page.png
"""
    flow = load_flow(write_flow(tmp_path, text))

    python_steps = [
        WorkflowStep.action("open", url="https://example.test"),
        WorkflowStep.artifact("screenshot", "page.png"),
    ]

    assert [(s.kind, s.name, s.parameters) for s in flow.steps] == [
        (s.kind, s.name, s.parameters) for s in python_steps
    ]


def test_cli_run_yaml_dry_run(tmp_path, capsys):
    flow_file = tmp_path / "flow.yaml"
    flow_file.write_text(FLOW, encoding="utf-8")
    report_file = tmp_path / "report.json"

    exit_code = cli.main(
        ["run-yaml", str(flow_file), "--json", "--report-file", str(report_file)]
    )

    assert exit_code == 0
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["schema_version"] == "2"
    assert report["status"] == "succeeded"
    assert [step["step_name"] for step in report["steps"]] == [
        "open",
        "wait_for_element",
        "screenshot",
        "click",
    ]


def test_cli_run_yaml_missing_param_is_rejected(tmp_path, capsys):
    flow_file = tmp_path / "flow.yaml"
    flow_file.write_text(
        "workflow: p\nsteps:\n  - action: open\n    url: ${param.missing}\n",
        encoding="utf-8",
    )

    exit_code = cli.main(["run-yaml", str(flow_file)])

    assert exit_code == 2
    assert "unknown flow parameter" in capsys.readouterr().err


def test_cli_run_yaml_requires_factory_for_live(tmp_path, capsys):
    flow_file = tmp_path / "flow.yaml"
    flow_file.write_text(FLOW, encoding="utf-8")

    exit_code = cli.main(["run-yaml", str(flow_file), "--live"])

    assert exit_code == 2
    assert "--factory is required" in capsys.readouterr().err
