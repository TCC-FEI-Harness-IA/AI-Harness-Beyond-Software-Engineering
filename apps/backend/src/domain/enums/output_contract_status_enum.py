from enum import StrEnum


class OutputContractStatusEnum(StrEnum):
    """Enum do estado do contrato (schema e coerência) de uma saída do modelo.

    `NOT_EVALUATED` indica que o contrato nem chegou a ser conferido, porque não havia
    objeto JSON a conferir ou porque a fase não tem saída estruturada.
    """

    VALID = "valid"
    INVALID = "invalid"
    NOT_EVALUATED = "not_evaluated"
