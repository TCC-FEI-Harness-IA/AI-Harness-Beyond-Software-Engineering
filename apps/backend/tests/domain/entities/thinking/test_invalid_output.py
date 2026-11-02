import dataclasses

import pytest

from src.domain.entities.thinking.invalid_output import InvalidOutput
from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic


def test_carrega_a_saida_bruta_e_o_motivo_da_recusa() -> None:
    saida = InvalidOutput(raw_output="isto nao e json", reason="Nenhum objeto JSON válido.")

    assert saida.raw_output == "isto nao e json"
    assert saida.reason == "Nenhum objeto JSON válido."


def test_e_imutavel() -> None:
    saida = InvalidOutput(raw_output="x", reason="y")

    with pytest.raises(dataclasses.FrozenInstanceError):
        saida.reason = "z"


def test_sem_vinculo_informado_invocacao_e_diagnostico_ficam_ausentes() -> None:
    saida = InvalidOutput(raw_output="x", reason="y")

    assert saida.invocation_id is None
    assert saida.diagnostic is None


def test_carrega_a_invocacao_de_origem_e_o_diagnostico() -> None:
    diagnostico = OutputDiagnostic.unclassified(reason="y", finish_reason="stop")

    saida = InvalidOutput(raw_output="x", reason="y", invocation_id="inv-7", diagnostic=diagnostico)

    assert saida.invocation_id == "inv-7"
    assert saida.diagnostic is diagnostico
