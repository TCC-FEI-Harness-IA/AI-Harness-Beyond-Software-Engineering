from enum import StrEnum


class SessionStatusEnum(StrEnum):
    """Enum dos estados possíveis de uma sessão.

    `DEGRADED` é legado: o fluxo atual não o produz, mas sessões antigas continuam legíveis com ele.
    """

    RUNNING = "running"
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"
