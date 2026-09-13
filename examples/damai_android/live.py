"""Live session factories for the damai Android smoke workflow.

Driver selection lives at the factory layer (not in the CLI): the smoke
steps are identical for Appium and uiautomator2, only the session factory
differs. Real device SDKs are imported lazily so the default offline tests
never require appium or uiautomator2.
"""

import os
from typing import Any, Callable, Optional

from automation_core.drivers import DriverSession

SessionFactory = Callable[[], DriverSession]

UIA2_UDID_ENV = "AUTOMATION_UIA2_UDID"


def create_session_factory(
    driver: str = "appium",
    *,
    udid: Optional[str] = None,
    artifact_root: Optional[Any] = None,
) -> SessionFactory:
    """Return a zero-arg session factory for the requested driver.

    ``driver`` accepts ``appium`` or ``uia2``; ``udid`` only applies to
    ``uia2`` (``None`` connects to the first adb device).
    """
    if driver == "appium":
        raise ValueError(
            "appium sessions require a pre-configured driver factory; "
            "pass one via --factory"
        )
    if driver == "uia2":
        return _uia2_factory(udid=udid, artifact_root=artifact_root)
    raise ValueError(f"unsupported driver: {driver}")


def uia2_session_factory() -> DriverSession:
    """Zero-arg factory target for ``automation-runner run --factory``.

    Reads the device serial from ``AUTOMATION_UIA2_UDID`` (optional; defaults
    to the first adb device).
    """
    return create_session_factory(
        "uia2",
        udid=os.environ.get(UIA2_UDID_ENV) or None,
    )()


def _uia2_factory(
    udid: Optional[str],
    artifact_root: Optional[Any],
) -> SessionFactory:
    def factory() -> DriverSession:
        from adapters.errors import AdapterStartupError
        from adapters.uia2 import Uia2Session

        try:
            device = _connect_uia2(udid)
        except Exception as exc:
            raise AdapterStartupError("failed to create uia2 device") from exc
        return Uia2Session(
            device,
            artifact_root=artifact_root,
        )

    return factory


def _connect_uia2(udid: Optional[str]):
    import uiautomator2 as u2

    return u2.connect(udid)
