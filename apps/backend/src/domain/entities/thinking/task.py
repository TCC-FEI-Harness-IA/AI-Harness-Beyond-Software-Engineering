from dataclasses import dataclass, field

from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.task_attempt import TaskAttempt
from src.domain.enums.task_status_enum import TaskStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass
class Task:
    """Representa uma tarefa de objetivo único produzida por A.2 ou C.2.

    Attributes:
        id: Identificador único da tarefa.
        title: Título curto da tarefa.
        description: Descrição da responsabilidade única da tarefa.
        expected_input: Entradas esperadas para a resolução da tarefa.
        expected_output: Saída esperada da resolução da tarefa.
        acceptance_criteria: Critérios de aceite individuais da tarefa.
        status: Estado atual da tarefa no loop de execução.
        origin_phase: Fase que originou a tarefa (A.2 ou C.2).
        attempts: Tentativas de resolução já realizadas para a tarefa.
    """

    id: str
    title: str
    description: str
    expected_input: str
    expected_output: str
    acceptance_criteria: tuple[AcceptanceCriterion, ...]
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    origin_phase: ThinkingPhaseEnum = ThinkingPhaseEnum.A2_TASK_DECOMPOSITION
    attempts: list[TaskAttempt] = field(default_factory=list)
