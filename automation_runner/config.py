from dataclasses import dataclass
from typing import Optional

from automation_core.config import ConfigSource


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class RunnerConfig:
    live: bool = False
    emit_json: bool = False
    factory: Optional[str] = None
    url: Optional[str] = None
    app_id: Optional[str] = None


def _optional_string(source: ConfigSource, key: str) -> Optional[str]:
    value = source.get(key, default=None).value
    if value is None:
        return None
    return str(value)


def _optional_bool(source: ConfigSource, key: str, default: bool = False) -> bool:
    value = source.get(key, default=default).value
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in TRUE_VALUES:
            return True
        if normalized in FALSE_VALUES:
            return False
    raise ValueError(f"config {key} expected bool")


def load_runner_config(source: ConfigSource) -> RunnerConfig:
    return RunnerConfig(
        live=_optional_bool(source, "live"),
        emit_json=_optional_bool(source, "json"),
        factory=_optional_string(source, "factory"),
        url=_optional_string(source, "url"),
        app_id=_optional_string(source, "app_id"),
    )
