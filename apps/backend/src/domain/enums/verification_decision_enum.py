from enum import StrEnum


class VerificationDecisionEnum(StrEnum):
    """Enum das decisões possíveis de uma verificação de critérios."""

    APPROVED = "approved"
    REPROVED = "reproved"
