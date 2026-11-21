from dataclasses import dataclass


@dataclass(frozen=True)
class CriterionEvaluation:
    """Representa o veredito de um critério individual dentro de uma verificação.

    Attributes:
        criterion_id: Identificador do critério avaliado.
        met: Indica se o critério foi satisfeito.
        justification: Justificativa do veredito.
    """

    criterion_id: str
    met: bool
    justification: str
