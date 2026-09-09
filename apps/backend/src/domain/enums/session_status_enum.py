from enum import StrEnum


class SessionStatusEnum(StrEnum):
    """Enum dos estados possíveis de uma sessão."""

    RUNNING = "running"
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"
