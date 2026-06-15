import pytest

from automation_core.config import ConfigError, ConfigSource, ConfigValue, DictConfigSource


def test_dict_config_source_reads_required_value():
    source = DictConfigSource({"timeout": 30})

    assert isinstance(source, ConfigSource)
    value = source.require("timeout", expected_type=int)

    assert value == ConfigValue(key="timeout", value=30)
    assert value.as_type(int) == 30


def test_dict_config_source_raises_for_missing_required_value():
    source = DictConfigSource({})

    with pytest.raises(ConfigError, match="missing required config: timeout"):
        source.require("timeout")


def test_dict_config_source_returns_default_for_optional_value():
    source = DictConfigSource({})

    value = source.get("timeout", default=10, expected_type=int)

    assert value == ConfigValue(key="timeout", value=10)


def test_dict_config_source_rejects_wrong_type():
    source = DictConfigSource({"timeout": "30"})

    with pytest.raises(ConfigError, match="config timeout expected int"):
        source.require("timeout", expected_type=int)


def test_dict_config_source_rejects_default_with_wrong_type():
    source = DictConfigSource({})

    with pytest.raises(ConfigError, match="config timeout expected int"):
        source.get("timeout", default=None, expected_type=int)


def test_dict_config_source_keeps_original_mapping_immutable():
    data = {"timeout": 30}
    source = DictConfigSource(data)

    data["timeout"] = 60

    assert source.require("timeout", expected_type=int).value == 30
