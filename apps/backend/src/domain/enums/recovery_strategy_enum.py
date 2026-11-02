from enum import StrEnum


class RecoveryStrategyEnum(StrEnum):
    """Enum da estratégia aplicada a uma saída recusada pelo parser.

    Attributes:
        CORRECTION_PROMPT: Nova chamada na mesma janela, com a mensagem de correção e temperatura 1.
        NONE: Nenhuma nova chamada: as retentativas de saída inválida da fase se esgotaram.
    """

    CORRECTION_PROMPT = "correction_prompt"
    NONE = "none"
