"""Fixture module loaded via import path by --capability-builders CLI tests."""
from automation_core.capabilities import CapabilityRequest


def fake_slider_builder(*, provider="auto"):
    return CapabilityRequest(
        capability="visual.challenge",
        operation="solve",
        parameters={"provider": provider},
    )


BUILDERS = {"fake_slider": fake_slider_builder}


def get_builders():
    return dict(BUILDERS)
