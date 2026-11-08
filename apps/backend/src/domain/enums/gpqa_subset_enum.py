from enum import StrEnum


class GPQASubsetEnum(StrEnum):
    """Subconjuntos oficiais do GPQA disponíveis para execução."""

    DIAMOND = "diamond"
    MAIN = "main"
    EXTENDED = "extended"
