from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol, Type, TypeVar, runtime_checkable


T = TypeVar("T")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ConfigValue:
    key: str
    value: Any

    def as_type(self, expected_type: Type[T]) -> T:
        if not isinstance(self.value, expected_type):
            raise ConfigError(
                f"config {self.key} expected {expected_type.__name__}, "
                f"got {type(self.value).__name__}"
            )
        return self.value


@runtime_checkable
class ConfigSource(Protocol):
    def require(
        self,
        key: str,
        expected_type: Optional[Type[T]] = None,
    ) -> ConfigValue:
        ...

    def get(
        self,
        key: str,
        default: Any = None,
        expected_type: Optional[Type[T]] = None,
    ) -> ConfigValue:
        ...


class DictConfigSource:
    def __init__(self, values: Dict[str, Any]):
        self._values = dict(values)

    def require(
        self,
        key: str,
        expected_type: Optional[Type[T]] = None,
    ) -> ConfigValue:
        if key not in self._values:
            raise ConfigError(f"missing required config: {key}")
        return self._build_value(key, self._values[key], expected_type)

    def get(
        self,
        key: str,
        default: Any = None,
        expected_type: Optional[Type[T]] = None,
    ) -> ConfigValue:
        value = self._values.get(key, default)
        return self._build_value(key, value, expected_type)

    def _build_value(
        self,
        key: str,
        value: Any,
        expected_type: Optional[Type[T]],
    ) -> ConfigValue:
        config_value = ConfigValue(key=key, value=value)
        if expected_type is not None:
            config_value.as_type(expected_type)
        return config_value


class EnvConfigSource:
    def __init__(self, values: Mapping[str, str], prefix: str = ""):
        self._values = dict(values)
        self._prefix = prefix

    def require(
        self,
        key: str,
        expected_type: Optional[Type[T]] = None,
    ) -> ConfigValue:
        env_key = self._env_key(key)
        if env_key not in self._values:
            raise ConfigError(f"missing required config: {key}")
        return self._build_value(key, self._values[env_key], expected_type)

    def get(
        self,
        key: str,
        default: Any = None,
        expected_type: Optional[Type[T]] = None,
    ) -> ConfigValue:
        value = self._values.get(self._env_key(key), default)
        return self._build_value(key, value, expected_type)

    def _env_key(self, key: str) -> str:
        return f"{self._prefix}{key}".upper()

    def _build_value(
        self,
        key: str,
        value: Any,
        expected_type: Optional[Type[T]],
    ) -> ConfigValue:
        config_value = ConfigValue(key=key, value=value)
        if expected_type is not None:
            config_value.as_type(expected_type)
        return config_value
