import dataclasses

import pytest

from src.domain.entities.thinking.invalid_output import InvalidOutput


def test_carrega_a_saida_bruta_e_o_motivo_da_recusa() -> None:
    saida = InvalidOutput(raw_output="isto nao e json", reason="Nenhum objeto JSON válido.")

    assert saida.raw_output == "isto nao e json"
    assert saida.reason == "Nenhum objeto JSON válido."


def test_e_imutavel() -> None:
    saida = InvalidOutput(raw_output="x", reason="y")

    with pytest.raises(dataclasses.FrozenInstanceError):
        saida.reason = "z"
