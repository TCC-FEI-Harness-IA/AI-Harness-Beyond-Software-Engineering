from enum import StrEnum


class SessionFailureReasonEnum(StrEnum):
    """Enum dos motivos que encerram uma sessão sem conclusão."""

    RESOURCE_LIMIT = "resource_limit"
    TECHNICAL_ERROR = "technical_error"
