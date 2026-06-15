import pytest

from automation_core.config import ConfigError, ConfigValue, EnvConfigSource


def test_env_config_source_reads_prefixed_value():
    source = EnvConfigSource({"AUTOMATION_TIMEOUT": "30"}, prefix="AUTOMATION_")

    value = source.require("timeout")

    assert value == ConfigValue(key="timeout", value="30")
    assert value.as_type(str) == "30"


def test_env_config_source_reads_unprefixed_value():
    source = EnvConfigSource({"TIMEOUT": "30"})

    value = source.require("timeout", expected_type=str)

    assert value == ConfigValue(key="timeout", value="30")


def test_env_config_source_returns_default_for_missing_value():
    source = EnvConfigSource({}, prefix="AUTOMATION_")

    value = source.get("timeout", default="15")

    assert value == ConfigValue(key="timeout", value="15")


def test_env_config_source_rejects_missing_required_value():
    source = EnvConfigSource({}, prefix="AUTOMATION_")

    with pytest.raises(ConfigError, match="missing required config: timeout"):
        source.require("timeout")


def test_env_config_source_rejects_wrong_type():
    source = EnvConfigSource({"AUTOMATION_TIMEOUT": "30"}, prefix="AUTOMATION_")

    with pytest.raises(ConfigError, match="config timeout expected int"):
        source.require("timeout", expected_type=int)


def test_env_config_source_keeps_original_mapping_immutable():
    data = {"AUTOMATION_TIMEOUT": "30"}
    source = EnvConfigSource(data, prefix="AUTOMATION_")

    data["AUTOMATION_TIMEOUT"] = "60"

    assert source.require("timeout").value == "30"
