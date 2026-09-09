import dataclasses

import pytest

from src.domain.entities.thinking.task_attempt import TaskAttempt


def test_carrega_os_campos_informados() -> None:
    tentativa = TaskAttempt(number=1, output="resultado preliminar", report=None)

    assert tentativa.number == 1
    assert tentativa.output == "resultado preliminar"
    assert tentativa.report is None


def test_e_imutavel() -> None:
    tentativa = TaskAttempt(number=1, output="resultado preliminar", report=None)

    with pytest.raises(dataclasses.FrozenInstanceError):
        tentativa.number = 2
