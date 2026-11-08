from enum import StrEnum


class ThinkingEventTypeEnum(StrEnum):
    """Enum dos tipos de evento emitidos pelo WebSocket de thinking."""

    THINKING = "thinking"
    RESULT = "result"
    DEGRADED = "degraded"
    ERROR = "error"
