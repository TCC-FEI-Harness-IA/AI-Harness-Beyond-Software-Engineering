from enum import StrEnum


class OutputSyntaxStatusEnum(StrEnum):
    """Enum do estado da extração e da sintaxe JSON de uma saída do modelo."""

    VALID = "valid"
    INVALID = "invalid"
    REPAIRED = "valid_after_repair"
