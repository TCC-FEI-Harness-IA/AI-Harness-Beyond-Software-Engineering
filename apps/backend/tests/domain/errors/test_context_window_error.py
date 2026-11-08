from src.domain.errors.context_window_error import ContextWindowError
from src.domain.errors.ralph_error import RalphError


def test_herda_de_ralph_error() -> None:
    assert issubclass(ContextWindowError, RalphError)


def test_carrega_a_mensagem_informada() -> None:
    erro = ContextWindowError("operacao invalida")

    assert str(erro) == "operacao invalida"
