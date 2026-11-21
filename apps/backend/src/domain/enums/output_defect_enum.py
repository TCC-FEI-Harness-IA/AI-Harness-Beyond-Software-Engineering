from enum import StrEnum


class OutputDefectEnum(StrEnum):
    """Enum dos defeitos que levam o parser a recusar uma saída estruturada do modelo.

    Cada defeito pede uma correção diferente: `syntax` só precisa do mesmo conteúdo serializado
    como JSON válido; `contract` é um JSON legível que contraria o schema ou a coerência exigida
    pela fase e precisa ser conferido pelo próprio modelo; `truncated` é uma saída interrompida pelo
    limite de comprimento, que precisa ser refeita por inteiro, de forma mais concisa.
    """

    SYNTAX = "syntax"
    CONTRACT = "contract"
    TRUNCATED = "truncated"

    @property
    def label(self) -> str:
        """Nome legível do defeito, usado na auditoria da sessão e no histórico da tarefa.

        Returns:
            str: Descrição curta do defeito, em português.
        """
        return _LABEL_BY_DEFECT[self]


_LABEL_BY_DEFECT = {
    OutputDefectEnum.SYNTAX: "erro de sintaxe",
    OutputDefectEnum.CONTRACT: "violação de contrato",
    OutputDefectEnum.TRUNCATED: "interrupção por comprimento",
}
