import json
from pathlib import Path

from automation_core import __version__ as AUTOMATION_KIT_VERSION
from automation_core.config import DictConfigSource
import automation_runner.cli as cli
from automation_runner.cli import main
from tests.runner import fixtures


def test_cli_lists_example_workflows_without_live_execution(capsys):
    exit_code = main(["examples", "--dry-run"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "damai-web-smoke" in captured.out
    assert "damai-android-smoke" in captured.out
    assert "dry-run" in captured.out


def test_cli_lists_example_workflows_as_json(capsys):
    exit_code = main(["examples", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "dry_run": False,
        "workflows": [
            {
                "description": "Launch an Android app and capture startup artifacts.",
                "name": "damai-android-smoke",
                "platform": "android",
                "required_options": ["app_id"],
                "supports_dry_run": True,
            },
            {
                "description": "Open a web URL and capture a screenshot artifact.",
                "name": "damai-web-smoke",
                "platform": "web",
                "required_options": ["url"],
                "supports_dry_run": True,
            },
        ],
    }
    assert captured.err == ""


def test_cli_lists_example_workflows_as_json_with_dry_run(capsys):
    exit_code = main(["examples", "--dry-run", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["dry_run"] is True
    assert payload["workflows"] == [
        {
            "description": "Launch an Android app and capture startup artifacts.",
            "name": "damai-android-smoke",
            "platform": "android",
            "required_options": ["app_id"],
            "supports_dry_run": True,
        },
        {
            "description": "Open a web URL and capture a screenshot artifact.",
            "name": "damai-web-smoke",
            "platform": "web",
            "required_options": ["url"],
            "supports_dry_run": True,
        },
    ]


def test_cli_examples_json_rejects_workflow_missing_metadata(monkeypatch, capsys):
    workflows = dict(cli.WORKFLOWS)
    workflows["missing-metadata"] = object()
    monkeypatch.setattr(cli, "WORKFLOWS", workflows)

    exit_code = main(["examples", "--json"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "missing workflow metadata: missing-metadata" in captured.err


def test_cli_examples_does_not_validate_run_config(capsys):
    exit_code = main(
        ["examples", "--dry-run"],
        config_source=DictConfigSource({"live": "maybe"}),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "damai-web-smoke" in captured.out


def test_cli_prints_runner_version(capsys):
    exit_code = main(["--version"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == f"automation-runner {AUTOMATION_KIT_VERSION}\n"
    assert captured.err == ""


def test_cli_prints_report_schema_v1(capsys):
    exit_code = main(["report-schema", "--version", "1"])

    captured = capsys.readouterr()
    schema = json.loads(captured.out)

    assert exit_code == 0
    assert schema["title"] == "Automation Kit Runner Report v1"
    assert schema["properties"]["schema_version"]["const"] == "1"
    assert captured.err == ""


def test_cli_rejects_unknown_report_schema_version(capsys):
    exit_code = main(["report-schema", "--version", "2"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "unsupported report schema version: 2" in captured.err


def test_pyproject_exposes_runner_script():
    content = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'automation-runner = "automation_runner.cli:main"' in content


def test_cli_runs_dry_workflow_without_live_flag(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--json",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["schema_version"] == "1"
    assert report["workflow"] == "damai-web-smoke"
    assert report["success"] is True
    assert report["live"] is False
    assert report["workflow_factory"] is None
    assert report["session_factory"] is None
    assert report["session"] == {
        "driver_name": "dry-run",
        "platform": "dry",
        "identifier": "damai-web-smoke-dry-run",
    }
    assert [event["event_type"] for event in report["events"]] == [
        "task.start",
        "artifact",
        "task.end",
    ]
    assert report["events"][0]["task_id"] == "damai-web-smoke-dry-run"
    assert report["events"][0]["payload"]["task_name"] == "damai-web-smoke"
    assert report["actions"] == [
        {"success": True, "message": "open"},
    ]
    assert report["action_batch"] == {
        "results": [
            {"success": True, "message": "open"},
        ],
        "skipped": [],
        "success": True,
    }
    assert fixtures.CREATED_SESSIONS == []


def test_cli_uses_config_source_for_dry_workflow_defaults(capsys):
    fixtures.reset()

    exit_code = main(
        ["run", "damai-web-smoke"],
        config_source=DictConfigSource(
            {
                "json": "true",
                "url": "https://example.test/damai",
            }
        ),
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["workflow"] == "damai-web-smoke"
    assert report["live"] is False
    assert report["actions"] == [
        {"success": True, "message": "open"},
    ]
    assert fixtures.CREATED_SESSIONS == []


def test_cli_reads_runner_environment_defaults(monkeypatch, capsys):
    fixtures.reset()
    monkeypatch.setenv("AUTOMATION_RUNNER_JSON", "true")
    monkeypatch.setenv("AUTOMATION_RUNNER_URL", "https://example.test/damai")

    exit_code = main(["run", "damai-web-smoke"])

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["workflow"] == "damai-web-smoke"
    assert report["live"] is False
    assert fixtures.CREATED_SESSIONS == []


def test_cli_runs_custom_workflow_factory_in_dry_mode(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_custom_workflow",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["workflow"] == "tests.runner.fixtures:create_custom_workflow"
    assert report["workflow_factory"] == "tests.runner.fixtures:create_custom_workflow"
    assert report["session_factory"] is None
    assert report["session"] == {
        "driver_name": "dry-run",
        "platform": "dry",
        "identifier": "tests.runner.fixtures:create_custom_workflow-dry-run",
    }
    assert report["actions"] == [
        {"success": True, "message": "custom_action"},
    ]
    assert fixtures.CREATED_SESSIONS == []


def test_cli_passes_context_and_options_to_custom_workflow_factory(tmp_path, capsys):
    fixtures.reset()
    report_path = tmp_path / "reports" / "run.json"

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_context_workflow",
            "--live",
            "--json",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
            "--app-id",
            "cn.damai",
            "--param",
            "account=test-user",
            "--param",
            "city=shanghai",
            "--param",
            "token=a=b",
            "--report-file",
            str(report_path),
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["workflow"] == "tests.runner.fixtures:create_context_workflow"
    assert report["workflow_factory"] == "tests.runner.fixtures:create_context_workflow"
    assert report["session_factory"] == "tests.runner.fixtures:make_session"
    assert report["actions"] == [
        {
            "success": True,
            "message": "context_action",
        },
    ]
    assert "data" not in report["actions"][0]
    assert fixtures.CREATED_SESSIONS[0].actions == [
        (
            "context_action",
            {
                "workflow": "tests.runner.fixtures:create_context_workflow",
                "live": True,
                "workflow_factory": "tests.runner.fixtures:create_context_workflow",
                "session_factory": "tests.runner.fixtures:make_session",
                "url": "https://example.test/damai",
                "app_id": "cn.damai",
                "emit_json": True,
                "report_file": str(report_path),
                "parameters": {
                    "account": "test-user",
                    "city": "shanghai",
                    "token": "a=b",
                },
            },
        )
    ]


def test_cli_passes_context_to_custom_workflow_factory_with_kwargs(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_kwargs_context_workflow",
            "--json",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["actions"] == [
        {
            "success": True,
            "message": "kwargs_context_action",
        },
    ]


def test_cli_reads_custom_workflow_factory_from_config(capsys):
    fixtures.reset()

    exit_code = main(
        ["run"],
        config_source=DictConfigSource(
            {
                "json": "true",
                "workflow_factory": "tests.runner.fixtures:create_custom_workflow",
            }
        ),
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["workflow"] == "tests.runner.fixtures:create_custom_workflow"


def test_cli_workflow_name_overrides_config_workflow_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--json",
            "--url",
            "https://example.test/damai",
        ],
        config_source=DictConfigSource(
            {
                "workflow_factory": "tests.runner.fixtures:create_custom_workflow",
            }
        ),
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["workflow"] == "damai-web-smoke"
    assert report["workflow_factory"] is None
    assert report["actions"] == [
        {"success": True, "message": "open"},
    ]
    assert fixtures.CREATED_SESSIONS == []


def test_cli_passes_config_parameters_to_custom_workflow_factory(capsys):
    fixtures.reset()

    exit_code = main(
        ["run"],
        config_source=DictConfigSource(
            {
                "json": "true",
                "live": "true",
                "factory": "tests.runner.fixtures:make_session",
                "workflow_factory": "tests.runner.fixtures:create_context_workflow",
                "parameters": {
                    "account": "config-user",
                    "city": "beijing",
                },
            }
        ),
    )

    captured = capsys.readouterr()
    json.loads(captured.out)

    assert exit_code == 0
    assert fixtures.CREATED_SESSIONS[0].actions[0][1]["parameters"] == {
        "account": "config-user",
        "city": "beijing",
    }


def test_cli_param_overrides_config_parameters_for_custom_workflow(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--param",
            "city=shanghai",
        ],
        config_source=DictConfigSource(
            {
                "json": "true",
                "live": "true",
                "factory": "tests.runner.fixtures:make_session",
                "workflow_factory": "tests.runner.fixtures:create_context_workflow",
                "parameters": {
                    "account": "config-user",
                    "city": "beijing",
                },
            }
        ),
    )

    captured = capsys.readouterr()
    json.loads(captured.out)

    assert exit_code == 0
    assert fixtures.CREATED_SESSIONS[0].actions[0][1]["parameters"] == {
        "account": "config-user",
        "city": "shanghai",
    }


def test_cli_requires_workflow_name_or_factory(capsys):
    exit_code = main(["run"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "workflow or --workflow-factory is required" in captured.err


def test_cli_rejects_missing_workflow_factory(capsys):
    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:missing_workflow_factory",
            "--json",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "could not load factory" in captured.err


def test_cli_rejects_workflow_name_with_explicit_workflow_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--workflow-factory",
            "tests.runner.fixtures:create_custom_workflow",
            "--json",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "workflow and --workflow-factory are mutually exclusive" in captured.err
    assert fixtures.CREATED_SESSIONS == []


def test_cli_uses_config_source_for_live_workflow(capsys):
    fixtures.reset()

    exit_code = main(
        ["run", "damai-web-smoke"],
        config_source=DictConfigSource(
            {
                "live": "true",
                "json": "true",
                "factory": "tests.runner.fixtures:make_session",
                "url": "https://example.test/damai",
            }
        ),
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["live"] is True
    assert report["workflow_factory"] is None
    assert report["session_factory"] == "tests.runner.fixtures:make_session"
    assert len(fixtures.CREATED_SESSIONS) == 1


def test_cli_arguments_override_config_source(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/cli",
        ],
        config_source=DictConfigSource(
            {
                "factory": "tests.runner.fixtures:make_failing_session",
                "url": "https://example.test/config",
            }
        ),
    )

    captured = capsys.readouterr()
    json.loads(captured.out)

    assert exit_code == 0
    assert fixtures.CREATED_SESSIONS[0].actions == [
        ("open", {"url": "https://example.test/cli"})
    ]


def test_cli_rejects_non_string_config_factory_before_loading_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--url",
            "https://example.test/damai",
        ],
        config_source=DictConfigSource({"factory": 123}),
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "config factory expected string" in captured.err
    assert fixtures.CREATED_SESSIONS == []


def test_cli_rejects_invalid_config_bool(capsys):
    exit_code = main(
        ["run", "damai-web-smoke"],
        config_source=DictConfigSource({"live": "maybe"}),
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "config live expected bool" in captured.err


def test_cli_dry_workflow_does_not_load_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--json",
            "--factory",
            "missing.runner.module:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["live"] is False
    assert fixtures.CREATED_SESSIONS == []


def test_cli_requires_factory_for_live_workflow(capsys):
    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--factory" in captured.err


def test_cli_runs_live_damai_web_smoke_with_imported_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "success=True" in captured.out
    assert len(fixtures.CREATED_SESSIONS) == 1
    session = fixtures.CREATED_SESSIONS[0]
    assert session.started is True
    assert session.stopped is True
    assert session.actions == [("open", {"url": "https://example.test/damai"})]
    assert session.artifacts == [("screenshot", "home.png")]


def test_cli_requires_url_for_live_damai_web_smoke(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures:make_session",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--url" in captured.err
    assert fixtures.CREATED_SESSIONS == []
    assert fixtures.IMPORT_ATTEMPTS == []


def test_cli_requires_app_id_for_live_damai_android_smoke(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-android-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures:make_session",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--app-id" in captured.err
    assert fixtures.CREATED_SESSIONS == []
    assert fixtures.IMPORT_ATTEMPTS == []


def test_cli_validates_workflow_parameters_before_loading_factory(capsys):
    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--factory",
            "missing.runner.module:make_session",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--url" in captured.err


def test_cli_rejects_invalid_factory_import_path(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures.make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "module:object" in captured.err
    assert fixtures.CREATED_SESSIONS == []


def test_cli_rejects_missing_factory_object(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures:missing_factory",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "could not load factory" in captured.err
    assert fixtures.CREATED_SESSIONS == []


def test_cli_rejects_invalid_workflow_param_for_builtin_workflow(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--json",
            "--url",
            "https://example.test/damai",
            "--param",
            "missing-equals",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "--param must use KEY=VALUE" in captured.err
    assert fixtures.CREATED_SESSIONS == []


def test_cli_rejects_invalid_workflow_param_before_loading_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_context_workflow",
            "--live",
            "--json",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--param",
            "missing-equals",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--param must use KEY=VALUE" in captured.err
    assert fixtures.CREATED_SESSIONS == []


def test_cli_runs_live_damai_android_smoke_with_imported_factory(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-android-smoke",
            "--live",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--app-id",
            "cn.damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "success=True" in captured.out
    assert len(fixtures.CREATED_SESSIONS) == 1
    session = fixtures.CREATED_SESSIONS[0]
    assert session.started is True
    assert session.stopped is True
    assert session.actions == [("launch_app", {"app_id": "cn.damai"})]
    assert session.artifacts == [
        ("screenshot", "startup.png"),
        ("page_source", "startup.xml"),
    ]


def test_cli_can_emit_json_report_for_live_workflow(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert report["workflow"] == "damai-web-smoke"
    assert report["workflow_factory"] is None
    assert report["session_factory"] == "tests.runner.fixtures:make_session"
    assert report["success"] is True
    assert report["status"] == "succeeded"
    assert report["run_id"] == "cli-run"
    assert report["run_state"]["run_id"] == "cli-run"
    assert report["run_state"]["status"] == "succeeded"
    assert report["run_state"]["finished_at"] is not None
    assert report["run_state"]["outcome"] == "succeeded"
    assert report["live"] is True
    assert isinstance(report["elapsed_seconds"], float)
    assert report["elapsed_seconds"] >= 0
    assert [event["event_type"] for event in report["events"]] == [
        "task.start",
        "artifact",
        "task.end",
    ]
    assert report["events"][0]["task_id"] == "cli-run"
    assert report["events"][0]["payload"]["task_name"] == "damai-web-smoke"
    assert report["events"][1]["payload"] == {
        "task_name": "damai-web-smoke",
        "task_id": "cli-run",
        "artifact_type": "screenshot",
        "path": "home.png",
    }
    assert report["events"][2]["payload"]["outcome"] == "succeeded"
    assert report["error"] is None
    assert report["session"] == {
        "driver_name": "fake-cli",
        "platform": "web",
        "identifier": "cli-run",
    }
    assert report["actions"] == [
        {"success": True, "message": "open"},
    ]
    assert report["artifacts"] == [
        {"artifact_type": "screenshot", "path": "home.png", "metadata": {}},
    ]
    assert "data" not in report["actions"][0]


def test_cli_can_write_json_report_to_file(tmp_path, capsys):
    fixtures.reset()
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--report-file",
            str(report_path),
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == captured.out
    assert "damai-web-smoke" in captured.out


def test_cli_can_write_report_file_when_json_comes_from_config(tmp_path, capsys):
    fixtures.reset()
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--report-file",
            str(report_path),
        ],
        config_source=DictConfigSource(
            {
                "json": "true",
                "url": "https://example.test/damai",
            }
        ),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert report_path.read_text(encoding="utf-8") == captured.out


def test_cli_emits_json_report_when_workflow_fails(tmp_path, capsys):
    fixtures.reset()
    report_path = tmp_path / "failed.json"

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--report-file",
            str(report_path),
            "--factory",
            "tests.runner.fixtures:make_failing_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 1
    assert report_path.read_text(encoding="utf-8") == captured.out
    assert report["workflow"] == "damai-web-smoke"
    assert report["workflow_factory"] is None
    assert report["session_factory"] == "tests.runner.fixtures:make_failing_session"
    assert report["success"] is False
    assert report["status"] == "failed"
    assert report["run_id"] == "cli-run"
    assert report["run_state"]["run_id"] == "cli-run"
    assert report["run_state"]["status"] == "failed"
    assert report["run_state"]["finished_at"] is not None
    assert report["run_state"]["outcome"] == "failed"
    assert report["live"] is True
    assert report["error"] is None
    assert [event["event_type"] for event in report["events"]] == [
        "task.start",
        "task.end",
    ]
    assert report["events"][1]["payload"]["outcome"] == "failed"
    assert report["actions"] == [
        {"success": False, "message": "open failed: open failed"}
    ]
    assert report["action_batch"] == {
        "results": [
            {"success": False, "message": "open failed: open failed"},
        ],
        "skipped": [],
        "success": False,
    }
    assert report["artifacts"] == []
    assert fixtures.CREATED_SESSIONS[0].stopped is True


def test_cli_emits_json_report_when_workflow_is_cancelled(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_cancelled_workflow",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 130
    assert report["workflow"] == "tests.runner.fixtures:create_cancelled_workflow"
    assert report["workflow_factory"] == "tests.runner.fixtures:create_cancelled_workflow"
    assert report["success"] is False
    assert report["status"] == "cancelled"
    assert report["run_state"]["status"] == "cancelled"
    assert report["run_state"]["outcome"] == "cancelled"
    assert [event["event_type"] for event in report["events"]] == [
        "task.start",
        "task.end",
    ]
    assert report["events"][-1]["payload"]["outcome"] == "cancelled"


def test_cli_returns_cancelled_exit_code_without_json(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_cancelled_workflow",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 130
    assert captured.out == "tests.runner.fixtures:create_cancelled_workflow success=False\n"
    assert captured.err == ""


def test_cli_emits_json_report_when_session_factory_fails(tmp_path, capsys):
    fixtures.reset()
    report_path = tmp_path / "startup-failed.json"

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--report-file",
            str(report_path),
            "--factory",
            "tests.runner.fixtures:raise_session_startup",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 1
    assert report_path.read_text(encoding="utf-8") == captured.out
    assert report["workflow"] == "damai-web-smoke"
    assert report["success"] is False
    assert report["status"] == "failed"
    assert report["run_id"] == "damai-web-smoke-failed-run"
    assert report["run_state"]["status"] == "failed"
    assert report["live"] is True
    assert report["session"] == {
        "driver_name": "unavailable",
        "platform": "unknown",
        "identifier": "damai-web-smoke-failed-run",
    }
    assert report["actions"] == []
    assert report["artifacts"] == []
    assert report["error"] == "RuntimeError: session startup failed"
    assert [event["event_type"] for event in report["events"]] == [
        "task.start",
        "error",
        "task.end",
    ]
    assert report["events"][0]["task_id"] == "damai-web-smoke-failed-run"
    assert report["events"][1]["payload"] == {
        "task_name": "damai-web-smoke",
        "task_id": "damai-web-smoke-failed-run",
        "message": "session startup failed",
        "error_type": "RuntimeError",
    }
    assert report["events"][2]["payload"]["outcome"] == "failed"


def test_cli_emits_json_report_when_custom_workflow_factory_fails(capsys):
    fixtures.reset()

    exit_code = main(
        [
            "run",
            "--workflow-factory",
            "tests.runner.fixtures:create_raising_workflow",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 1
    assert report["workflow"] == "tests.runner.fixtures:create_raising_workflow"
    assert report["workflow_factory"] == "tests.runner.fixtures:create_raising_workflow"
    assert report["success"] is False
    assert report["run_id"] == "tests.runner.fixtures:create_raising_workflow-failed-run"
    assert report["error"] == "RuntimeError: workflow construction failed"
    assert [event["event_type"] for event in report["events"]] == [
        "task.start",
        "error",
        "task.end",
    ]
    assert report["events"][1]["payload"] == {
        "task_name": "tests.runner.fixtures:create_raising_workflow",
        "task_id": "tests.runner.fixtures:create_raising_workflow-failed-run",
        "message": "workflow construction failed",
        "error_type": "RuntimeError",
    }


def test_cli_creates_report_file_parent_directories(tmp_path, capsys):
    fixtures.reset()
    report_path = tmp_path / "nested" / "reports" / "report.json"

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--report-file",
            str(report_path),
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    capsys.readouterr()

    assert exit_code == 0
    assert report_path.exists()


def test_cli_rejects_report_file_without_json(capsys):
    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--report-file",
            "report.json",
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--report-file requires --json" in captured.err


def test_cli_handles_report_file_write_failure_without_partial_stdout(
    tmp_path,
    capsys,
):
    fixtures.reset()
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory", encoding="utf-8")

    exit_code = main(
        [
            "run",
            "damai-web-smoke",
            "--live",
            "--json",
            "--report-file",
            str(blocked_parent / "report.json"),
            "--factory",
            "tests.runner.fixtures:make_session",
            "--url",
            "https://example.test/damai",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "could not write report file" in captured.err
    assert "Traceback" not in captured.err
