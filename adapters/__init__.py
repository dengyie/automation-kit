"""Optional framework adapter packages live outside automation_core."""

from adapters.errors import AdapterArtifactError, AdapterStartupError

__all__ = ["AdapterArtifactError", "AdapterStartupError"]
