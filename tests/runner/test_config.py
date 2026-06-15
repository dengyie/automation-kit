import pytest

from automation_core.config import DictConfigSource
from automation_runner.config import RunnerConfig, load_runner_config


def test_load_runner_config_defaults_to_dry_non_json():
    config = load_runner_config(DictConfigSource({}))

    assert config == RunnerConfig()


def test_load_runner_config_reads_runtime_values():
    config = load_runner_config(
        DictConfigSource(
            {
                "live": "true",
                "json": "yes",
                "factory": "tests.runner.fixtures:make_session",
                "workflow_factory": "tests.runner.fixtures:create_custom_workflow",
                "url": "https://example.test/damai",
                "app_id": "cn.damai",
            }
        )
    )

    assert config == RunnerConfig(
        live=True,
        emit_json=True,
        factory="tests.runner.fixtures:make_session",
        workflow_factory="tests.runner.fixtures:create_custom_workflow",
        url="https://example.test/damai",
        app_id="cn.damai",
    )


def test_load_runner_config_rejects_invalid_bool():
    with pytest.raises(ValueError, match="config live expected bool"):
        load_runner_config(DictConfigSource({"live": "maybe"}))
