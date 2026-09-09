from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.domain.errors.ralph_error import RalphError


def test_herda_de_ralph_error() -> None:
    assert issubclass(PhaseParsingError, RalphError)


def test_carrega_os_atributos_informados() -> None:
    erro = PhaseParsingError(
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        raw_output="saida sem json",
        reason="json ausente",
    )

    assert erro.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert erro.raw_output == "saida sem json"
    assert erro.reason == "json ausente"


def test_mensagem_referencia_a_fase_e_o_motivo() -> None:
    erro = PhaseParsingError(
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        raw_output="saida sem json",
        reason="json ausente",
    )

    assert "B1" in str(erro)
    assert "json ausente" in str(erro)
