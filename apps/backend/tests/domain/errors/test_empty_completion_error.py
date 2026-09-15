import pytest

from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.domain.errors.ralph_error import RalphError


def test_herda_de_ralph_error() -> None:
    assert issubclass(EmptyCompletionError, RalphError)


def test_carrega_o_motivo_de_termino_informado() -> None:
    erro = EmptyCompletionError(finish_reason="length")

    assert erro.finish_reason == "length"


@pytest.mark.parametrize("finish_reason", ["stop", "content_filter", None])
def test_mensagem_cita_o_motivo_de_termino(finish_reason: str | None) -> None:
    erro = EmptyCompletionError(finish_reason=finish_reason)

    assert "sem conteúdo de texto" in str(erro)
    assert str(finish_reason) in str(erro)


def test_motivo_length_explica_o_teto_de_tokens() -> None:
    """A causa mais comum: o raciocínio do modelo consumiu todo o `max_tokens`."""
    erro = EmptyCompletionError(finish_reason="length")

    assert "max_tokens" in str(erro)
    assert "OPENROUTER_REASONING_EFFORT" in str(erro)


@pytest.mark.parametrize("finish_reason", ["stop", None])
def test_outros_motivos_nao_recebem_a_explicacao_de_teto(finish_reason: str | None) -> None:
    assert "max_tokens" not in str(EmptyCompletionError(finish_reason=finish_reason))
