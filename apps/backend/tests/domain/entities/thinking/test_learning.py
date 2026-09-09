import dataclasses

import pytest

from src.domain.entities.thinking.learning import Learning


def test_carrega_os_campos_informados() -> None:
    aprendizado = Learning(content="fato seco e objetivo", source_task_id="t1")

    assert aprendizado.content == "fato seco e objetivo"
    assert aprendizado.source_task_id == "t1"


def test_e_imutavel() -> None:
    aprendizado = Learning(content="fato seco e objetivo", source_task_id="t1")

    with pytest.raises(dataclasses.FrozenInstanceError):
        aprendizado.content = "outro fato"
