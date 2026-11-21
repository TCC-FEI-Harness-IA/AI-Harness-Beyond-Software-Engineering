import dataclasses

import pytest

from src.domain.entities.thinking.learning import Learning


def test_carrega_os_campos_informados() -> None:
    aprendizado = Learning(content="fato seco e objetivo", source_task_id="t1")

    assert aprendizado.content == "fato seco e objetivo"
    assert aprendizado.source_task_id == "t1"


def test_aprendizado_do_planejamento_nao_tem_tarefa_de_origem() -> None:
    aprendizado = Learning(content="Alternativas: A) 2; B) 4")

    assert aprendizado.source_task_id is None


def test_e_imutavel() -> None:
    aprendizado = Learning(content="fato seco e objetivo", source_task_id="t1")

    with pytest.raises(dataclasses.FrozenInstanceError):
        aprendizado.content = "outro fato"
