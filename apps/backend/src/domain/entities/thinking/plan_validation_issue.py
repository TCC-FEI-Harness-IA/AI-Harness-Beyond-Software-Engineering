from dataclasses import dataclass


@dataclass(frozen=True)
class PlanValidationIssue:
    """Problema impeditivo apontado pela validação da decomposição (A.3) num plano candidato.

    O escopo é dado pelas referências: ambas nulas, o plano inteiro; só a tarefa, a tarefa; tarefa e
    critério, o critério daquela tarefa. Um critério sem tarefa não tem escopo definido. Que as
    referências existam no candidato julgado é verificado pelo parser, contra o plano da chamada.

    Attributes:
        task_id: Tarefa afetada, ou `None` num problema do plano inteiro.
        criterion_id: Critério afetado da tarefa, ou `None`.
        problem: Defeito concreto encontrado.
        adjustment: Alteração de investigação necessária, sem antecipar o resultado.
    """

    task_id: str | None
    criterion_id: str | None
    problem: str
    adjustment: str

    def __post_init__(self) -> None:
        """Recusa um problema sem texto ou com um critério fora de qualquer tarefa.

        Raises:
            ValueError: Quando `problem` ou `adjustment` está em branco, ou quando há critério sem tarefa.
        """
        if not self.problem.strip() or not self.adjustment.strip():
            raise ValueError("Um problema do plano precisa descrever o defeito e o ajuste necessário.")
        if self.criterion_id is not None and self.task_id is None:
            raise ValueError("Um critério apontado precisa pertencer a uma tarefa apontada.")

    @property
    def scope_task_id(self) -> str | None:
        """Tarefa a que o problema se refere, ou `None` num problema do plano inteiro."""
        return self.task_id

    @property
    def is_plan_wide(self) -> bool:
        """Informa se o problema atinge o plano inteiro, sem tarefa específica."""
        return self.task_id is None
