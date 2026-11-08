from src.domain.errors.ralph_error import RalphError


def test_e_uma_excecao() -> None:
    assert issubclass(RalphError, Exception)


def test_carrega_a_mensagem_informada() -> None:
    erro = RalphError("mensagem qualquer")

    assert str(erro) == "mensagem qualquer"
