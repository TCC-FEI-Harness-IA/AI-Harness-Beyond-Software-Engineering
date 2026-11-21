from enum import StrEnum


class PublicationStatusEnum(StrEnum):
    """Situação de uma publicação oficial: vigente ou substituída por outra (mantida no histórico)."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
