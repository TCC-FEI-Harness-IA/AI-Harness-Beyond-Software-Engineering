from enum import StrEnum


class ResultStatusEnum(StrEnum):
    """Enum do estado de um resultado armazenado em B.3.

    Attributes:
        CURRENT: Resultado vigente, entregue a C.1, C.2 e C.3 como fato aprovado.
        SUPERSEDED: Resultado substituído por um veredito aprovado; permanece só na auditoria.
        AWAITING_REVALIDATION: Resultado que depende explicitamente de um resultado que deixou de ser
            vigente; não é fato vigente até uma revisão aprovada confirmá-lo ou substituí-lo.
    """

    CURRENT = "current"
    SUPERSEDED = "superseded"
    AWAITING_REVALIDATION = "awaiting_revalidation"
