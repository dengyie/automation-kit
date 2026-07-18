class CapabilityError(RuntimeError):
    """Base class for capability contract errors."""


class CapabilityRegistrationError(CapabilityError):
    """Raised when a provider cannot be registered safely."""


class CapabilityNotFoundError(CapabilityError):
    """Raised when a requested capability is not registered."""


class CapabilityOperationNotSupportedError(CapabilityError):
    """Raised when a provider does not declare an operation."""


class CapabilityExecutionModeError(CapabilityError):
    """Raised when an async-only provider is called synchronously."""


class CapabilityProtocolError(CapabilityError):
    """Raised when a provider violates the capability contract."""
