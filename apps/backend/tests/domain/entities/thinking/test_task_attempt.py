import dataclasses

import pytest

from src.domain.entities.thinking.invalid_output import InvalidOutput
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


def test_sem_saidas_invalidas_do_validador_por_padrao() -> None:
    tentativa = TaskAttempt(number=1, output="resultado preliminar", report=None)

    assert tentativa.invalid_verifier_outputs == ()


def test_guarda_as_saidas_invalidas_que_o_validador_corrigiu() -> None:
    invalida = InvalidOutput(raw_output="{}", reason="Faltam avaliações")

    tentativa = TaskAttempt(number=1, output="resultado", report=None, invalid_verifier_outputs=(invalida,))

    assert tentativa.invalid_verifier_outputs == (invalida,)
