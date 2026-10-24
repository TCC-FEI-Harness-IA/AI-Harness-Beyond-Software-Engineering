from enum import StrEnum


class TaskStatusEnum(StrEnum):
    """Enum dos estados possíveis de uma tarefa do loop de execução."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    FAILED = "failed"
    DISCARDED = "discarded"
