from enum import StrEnum


class InvocationOutcomeEnum(StrEnum):
    """Enum dos desfechos possíveis de uma invocação ao modelo."""

    STARTED = "started"
    SUCCESS = "success"
    EMPTY_COMPLETION = "empty_completion"
    PROVIDER_ERROR = "provider_error"
