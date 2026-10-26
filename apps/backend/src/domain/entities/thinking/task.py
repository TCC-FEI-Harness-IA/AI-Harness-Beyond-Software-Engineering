from dataclasses import dataclass, field

from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.task_attempt import TaskAttempt
from src.domain.entities.thinking.task_result import TaskResult
from src.domain.enums.task_status_enum import TaskStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass
class Task:
    """Representa uma tarefa de objetivo único produzida por A.2 ou C.2.

    Attributes:
        id: Identificador único da tarefa.
        title: Título curto da tarefa.
        description: Descrição da responsabilidade única da tarefa.
        acceptance_criteria: Critérios de aceite individuais da tarefa.
        status: Estado atual da tarefa no loop de execução.
        origin_phase: Fase que originou a tarefa (A.2 ou C.2).
        attempts: Tentativas de resolução já realizadas para a tarefa.
    """

    id: str
    title: str
    description: str
    acceptance_criteria: tuple[AcceptanceCriterion, ...]
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    origin_phase: ThinkingPhaseEnum = ThinkingPhaseEnum.A2_TASK_DECOMPOSITION
    attempts: list[TaskAttempt] = field(default_factory=list)

    def approved_result(self) -> TaskResult:
        """Devolve o resultado aprovado da tarefa, a única coisa que B.3 pode armazenar.

        Returns:
            TaskResult: Saída da última tentativa, cujo relatório de verificação foi aprovado.

        Raises:
            ValueError: Quando a tarefa não foi aprovada ou a última tentativa não tem
                relatório aprovado.
        """
        if self.status is not TaskStatusEnum.APPROVED:
            raise ValueError(f"A tarefa '{self.id}' não foi aprovada; só um resultado aprovado pode ser armazenado.")

        last_attempt = self.attempts[-1] if self.attempts else None
        if last_attempt is None or last_attempt.report is None or not last_attempt.report.approved:
            raise ValueError(f"A tarefa '{self.id}' não tem um relatório aprovado na última tentativa.")

        return TaskResult(task_id=self.id, task_title=self.title, content=last_attempt.output)
