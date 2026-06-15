import pytest

from automation_core.config import ConfigError, ConfigValue


def test_config_value_returns_typed_value():
    value = ConfigValue(key="timeout", value=30)

    assert value.as_type(int) == 30


def test_config_value_rejects_wrong_type():
    value = ConfigValue(key="timeout", value="30")

    with pytest.raises(ConfigError, match="config timeout expected int"):
        value.as_type(int)
