import dataclasses

import pytest

from src.domain.entities.thinking.task_result import TaskResult


def _resultado() -> TaskResult:
    return TaskResult(
        task_id="t1",
        task_title="titulo",
        task_description="enunciado",
        content="conteudo aprovado",
        conclusion="conclusao",
    )


def test_carrega_os_campos_informados() -> None:
    resultado = _resultado()

    assert resultado.task_id == "t1"
    assert resultado.task_title == "titulo"
    assert resultado.task_description == "enunciado"
    assert resultado.content == "conteudo aprovado"
    assert resultado.conclusion == "conclusao"


def test_nao_existe_resultado_aprovado_por_degradacao() -> None:
    assert not hasattr(_resultado(), "degraded")


def test_e_imutavel() -> None:
    resultado = _resultado()

    with pytest.raises(dataclasses.FrozenInstanceError):
        resultado.content = "outro"
