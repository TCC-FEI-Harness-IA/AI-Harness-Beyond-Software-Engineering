import dataclasses

import pytest

from src.domain.entities.thinking.task_result import TaskResult


def test_carrega_os_campos_informados() -> None:
    resultado = TaskResult(task_id="t1", task_title="titulo", content="conteudo aprovado")

    assert resultado.task_id == "t1"
    assert resultado.task_title == "titulo"
    assert resultado.content == "conteudo aprovado"


def test_nao_existe_resultado_aprovado_por_degradacao() -> None:
    assert not hasattr(TaskResult(task_id="t1", task_title="titulo", content="c"), "degraded")


def test_e_imutavel() -> None:
    resultado = TaskResult(task_id="t1", task_title="titulo", content="conteudo aprovado")

    with pytest.raises(dataclasses.FrozenInstanceError):
        resultado.content = "outro"
