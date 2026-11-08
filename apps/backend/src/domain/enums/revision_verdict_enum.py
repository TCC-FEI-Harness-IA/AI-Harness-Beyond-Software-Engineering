from enum import StrEnum


class RevisionVerdictEnum(StrEnum):
    """Enum do veredito que uma tarefa revisora propõe para cada resultado sob investigação.

    Só um veredito `superseded` aprovado em B.2 tira um resultado do estado vigente; ordem
    temporal, palavras do texto ou divergência entre conclusões nunca produzem esse efeito.

    Attributes:
        CONFIRMED: A investigação sustenta a conclusão revisada, que continua vigente.
        SUPERSEDED: A investigação demonstra um erro na conclusão revisada, que deixa de ser vigente.
    """

    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"
