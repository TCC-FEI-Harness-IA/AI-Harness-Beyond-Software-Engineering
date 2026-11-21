import pytest

from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.task import Task
from src.domain.enums.task_status_enum import TaskStatusEnum
from src.domain.services.task_queue import TaskQueue


def _tarefa(task_id: str) -> Task:
    return Task(
        id=task_id,
        title=f"titulo de {task_id}",
        description=f"descricao de {task_id}",
        acceptance_criteria=(AcceptanceCriterion(id=f"{task_id}-AC1", description="criterio"),),
    )


def test_fila_nova_esta_vazia_e_nao_devolve_tarefa() -> None:
    fila = TaskQueue()

    assert fila.is_empty() is True
    assert fila.pop_next() is None
    assert fila.total_created() == 0


def test_push_back_enfileira_no_fim_preservando_a_ordem() -> None:
    fila = TaskQueue()

    fila.push_back(tasks=[_tarefa("T1"), _tarefa("T2")])

    assert fila.is_empty() is False
    assert fila.pop_next().id == "T1"
    assert fila.pop_next().id == "T2"
    assert fila.pop_next() is None


def test_push_front_insere_no_topo_preservando_a_ordem_relativa() -> None:
    fila = TaskQueue()
    fila.push_back(tasks=[_tarefa("T1"), _tarefa("T2")])

    fila.push_front(tasks=[_tarefa("T3"), _tarefa("T4")])

    assert [fila.pop_next().id for _ in range(4)] == ["T3", "T4", "T1", "T2"]


def test_pop_next_marca_a_tarefa_como_em_andamento() -> None:
    fila = TaskQueue()
    fila.push_back(tasks=[_tarefa("T1")])

    tarefa = fila.pop_next()

    assert tarefa.status is TaskStatusEnum.IN_PROGRESS


def test_discard_all_esvazia_devolve_e_marca_as_removidas_como_descartadas() -> None:
    fila = TaskQueue()
    fila.push_back(tasks=[_tarefa("T1"), _tarefa("T2")])

    descartadas = fila.discard_all()

    assert [tarefa.id for tarefa in descartadas] == ["T1", "T2"]
    assert all(tarefa.status is TaskStatusEnum.DISCARDED for tarefa in descartadas)
    assert fila.is_empty() is True


def test_total_created_conta_tambem_as_tarefas_ja_consumidas() -> None:
    fila = TaskQueue()
    fila.push_back(tasks=[_tarefa("T1"), _tarefa("T2")])
    fila.pop_next()

    fila.push_front(tasks=[_tarefa("T3")])

    assert fila.total_created() == 3


def test_push_back_com_id_duplicado_e_recusado() -> None:
    fila = TaskQueue()
    fila.push_back(tasks=[_tarefa("T1")])

    with pytest.raises(ValueError, match="T1"):
        fila.push_back(tasks=[_tarefa("T1")])


def test_push_front_com_id_duplicado_e_recusado() -> None:
    fila = TaskQueue()
    fila.push_back(tasks=[_tarefa("T1")])

    with pytest.raises(ValueError, match="T1"):
        fila.push_front(tasks=[_tarefa("T1")])


def test_id_duplicado_dentro_do_mesmo_lote_e_recusado() -> None:
    fila = TaskQueue()

    with pytest.raises(ValueError, match="T1"):
        fila.push_back(tasks=[_tarefa("T1"), _tarefa("T1")])


def test_id_ja_consumido_continua_bloqueado() -> None:
    fila = TaskQueue()
    fila.push_back(tasks=[_tarefa("T1")])
    fila.pop_next()

    with pytest.raises(ValueError, match="T1"):
        fila.push_front(tasks=[_tarefa("T1")])


def test_lote_rejeitado_nao_deixa_ids_nem_contadores_pela_metade() -> None:
    fila = TaskQueue()
    fila.push_back(tasks=[_tarefa("T1")])

    with pytest.raises(ValueError, match="T2"):
        fila.push_back(tasks=[_tarefa("T3"), _tarefa("T2"), _tarefa("T2")])

    assert fila.total_created() == 1
    assert fila.known_task_ids() == frozenset({"T1"})
    fila.push_back(tasks=[_tarefa("T3")])
    assert fila.total_created() == 2


def test_known_task_ids_inclui_as_tarefas_enfileiradas_e_as_consumidas() -> None:
    fila = TaskQueue()
    fila.push_back(tasks=[_tarefa("T1"), _tarefa("T2")])
    fila.pop_next()
    fila.push_front(tasks=[_tarefa("T3")])

    assert fila.known_task_ids() == frozenset({"T1", "T2", "T3"})


def test_known_task_ids_de_fila_nova_e_vazio() -> None:
    assert TaskQueue().known_task_ids() == frozenset()
