from enum import StrEnum


class RecoveryResultEnum(StrEnum):
    """Enum do resultado da recuperação de uma saída recusada.

    Attributes:
        PENDING: A correção foi pedida e ainda não terminou.
        RECOVERED: Uma chamada posterior da mesma execução de fase produziu saída aceita.
        FAILED: A execução da fase terminou sem saída aceita (retentativas esgotadas, orçamento
            negado, erro do provedor ou completions vazias).
    """

    PENDING = "pending"
    RECOVERED = "recovered"
    FAILED = "failed"
