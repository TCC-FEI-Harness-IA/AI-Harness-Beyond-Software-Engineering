from dataclasses import dataclass

from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum


@dataclass(frozen=True)
class OutputProblem:
    """Problema que levou o parser a recusar uma saída do modelo.

    O parser é estrito e para no primeiro problema encontrado: cada saída recusada tem exatamente
    um problema, ao lado do motivo legível que também vai para a mensagem de correção.

    Attributes:
        code: Classe estruturada do problema.
        reason: Motivo legível da recusa, o mesmo texto entregue ao modelo na correção.
        field: Caminho do campo afetado (por exemplo, `criteria_evaluation[].met`), quando há.
        affected_ids: Identificadores dos critérios ou tarefas afetados, quando conhecidos.
    """

    code: OutputProblemCodeEnum
    reason: str
    field: str | None = None
    affected_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Exige o motivo legível.

        Raises:
            ValueError: Quando o motivo está em branco.
        """
        if not self.reason.strip():
            raise ValueError("Um problema de saída exige um motivo legível.")
