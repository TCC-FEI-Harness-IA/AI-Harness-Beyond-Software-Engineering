import dataclasses

import pytest

from src.domain.entities.thinking.invalid_output import InvalidOutput
from src.domain.enums.output_defect_enum import OutputDefectEnum


def test_carrega_a_saida_bruta_e_o_motivo_da_recusa() -> None:
    saida = InvalidOutput(raw_output="isto nao e json", reason="Nenhum objeto JSON válido.")

    assert saida.raw_output == "isto nao e json"
    assert saida.reason == "Nenhum objeto JSON válido."


def test_e_imutavel() -> None:
    saida = InvalidOutput(raw_output="x", reason="y")

    with pytest.raises(dataclasses.FrozenInstanceError):
        saida.reason = "z"


def test_sem_classificacao_explicita_o_defeito_e_violacao_de_contrato() -> None:
    assert InvalidOutput(raw_output="x", reason="y").defect is OutputDefectEnum.CONTRACT


def test_carrega_o_defeito_que_motivou_a_recusa() -> None:
    saida = InvalidOutput(raw_output="x", reason="y", defect=OutputDefectEnum.SYNTAX)

    assert saida.defect is OutputDefectEnum.SYNTAX
