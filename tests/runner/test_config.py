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
                "parameters": {
                    "account": "config-user",
                    "city": "shanghai",
                },
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
        parameters={
            "account": "config-user",
            "city": "shanghai",
        },
    )


def test_load_runner_config_reads_json_parameters():
    config = load_runner_config(
        DictConfigSource(
            {
                "parameters": '{"account":"config-user","city":"shanghai"}',
            }
        )
    )

    assert config.parameters == {
        "account": "config-user",
        "city": "shanghai",
    }


def test_load_runner_config_rejects_invalid_parameter_json():
    with pytest.raises(ValueError, match="config parameters expected object"):
        load_runner_config(DictConfigSource({"parameters": "not-json"}))


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("factory", 123),
        ("workflow_factory", {"module": "factory"}),
        ("url", ["https://example.test"]),
        ("app_id", 42),
    ],
)
def test_load_runner_config_rejects_non_string_fields(key, value):
    with pytest.raises(ValueError, match=f"config {key} expected string"):
        load_runner_config(DictConfigSource({key: value}))


def test_load_runner_config_rejects_non_string_parameter_values():
    with pytest.raises(
        ValueError,
        match="config parameters expected string keys and values",
    ):
        load_runner_config(DictConfigSource({"parameters": {"count": 3}}))


def test_load_runner_config_rejects_invalid_bool():
    with pytest.raises(ValueError, match="config live expected bool"):
        load_runner_config(DictConfigSource({"live": "maybe"}))
