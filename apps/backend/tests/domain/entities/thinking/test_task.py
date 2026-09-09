from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.task import Task
from src.domain.enums.task_status_enum import TaskStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_CRITERIO = AcceptanceCriterion(id="c1", description="descricao do criterio")


def _nova_tarefa() -> Task:
    return Task(
        id="t1",
        title="titulo",
        description="descricao",
        expected_input="entrada esperada",
        expected_output="saida esperada",
        acceptance_criteria=(_CRITERIO,),
    )


def test_carrega_os_campos_obrigatorios() -> None:
    tarefa = _nova_tarefa()

    assert tarefa.id == "t1"
    assert tarefa.title == "titulo"
    assert tarefa.description == "descricao"
    assert tarefa.expected_input == "entrada esperada"
    assert tarefa.expected_output == "saida esperada"
    assert tarefa.acceptance_criteria == (_CRITERIO,)


def test_defaults_de_uma_tarefa_nova() -> None:
    tarefa = _nova_tarefa()

    assert tarefa.status is TaskStatusEnum.PENDING
    assert tarefa.origin_phase is ThinkingPhaseEnum.A2_TASK_DECOMPOSITION
    assert tarefa.attempts == []


def test_e_mutavel() -> None:
    tarefa = _nova_tarefa()

    tarefa.status = TaskStatusEnum.APPROVED

    assert tarefa.status is TaskStatusEnum.APPROVED
