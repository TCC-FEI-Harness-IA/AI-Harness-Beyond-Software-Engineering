from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptanceCriterion:
    """Representa um critério de aceite, geral ou de uma tarefa.

    Attributes:
        id: Identificador único do critério.
        description: Descrição do que deve ser satisfeito.
    """

    id: str
    description: str
