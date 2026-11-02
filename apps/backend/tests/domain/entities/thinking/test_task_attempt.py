import dataclasses

import pytest

from src.domain.entities.thinking.invalid_output import InvalidOutput
from src.domain.entities.thinking.task_attempt import TaskAttempt
from src.domain.enums.output_defect_enum import OutputDefectEnum


def test_carrega_os_campos_informados() -> None:
    tentativa = TaskAttempt(number=1, output="resultado preliminar", report=None)

    assert tentativa.number == 1
    assert tentativa.output == "resultado preliminar"
    assert tentativa.report is None


def test_e_imutavel() -> None:
    tentativa = TaskAttempt(number=1, output="resultado preliminar", report=None)

    with pytest.raises(dataclasses.FrozenInstanceError):
        tentativa.number = 2


def test_por_padrao_nao_registra_saidas_invalidas() -> None:
    tentativa = TaskAttempt(number=1, output="resultado preliminar", report=None)

    assert tentativa.resolution_invalid_outputs == ()
    assert tentativa.verification_invalid_outputs == ()


def test_guarda_as_saidas_invalidas_da_resolucao_e_da_verificacao_separadamente() -> None:
    da_resolucao = InvalidOutput(raw_output="sem json", reason="r1", defect=OutputDefectEnum.SYNTAX)
    da_verificacao = InvalidOutput(raw_output="{}", reason="r2", defect=OutputDefectEnum.CONTRACT)

    tentativa = TaskAttempt(
        number=1,
        output="resultado preliminar",
        report=None,
        resolution_invalid_outputs=(da_resolucao,),
        verification_invalid_outputs=(da_verificacao,),
    )

    assert tentativa.resolution_invalid_outputs == (da_resolucao,)
    assert tentativa.verification_invalid_outputs == (da_verificacao,)
