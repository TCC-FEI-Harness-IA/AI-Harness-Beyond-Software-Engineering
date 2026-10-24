import dataclasses

import pytest

from src.domain.entities.thinking.validation_context import ValidationContext


def test_contexto_vazio_nao_impoe_nenhuma_restricao() -> None:
    contexto = ValidationContext()

    assert contexto.expected_criteria_ids is None
    assert contexto.max_tasks is None
    assert contexto.known_task_ids == frozenset()


def test_carrega_os_ids_esperados_o_teto_de_tarefas_e_os_ids_conhecidos() -> None:
    contexto = ValidationContext(
        expected_criteria_ids=("AC1", "AC2"),
        max_tasks=3,
        known_task_ids=frozenset({"T1"}),
    )

    assert contexto.expected_criteria_ids == ("AC1", "AC2")
    assert contexto.max_tasks == 3
    assert contexto.known_task_ids == frozenset({"T1"})


def test_e_imutavel() -> None:
    contexto = ValidationContext(max_tasks=1)

    with pytest.raises(dataclasses.FrozenInstanceError):
        contexto.max_tasks = 2
