from src.domain.errors.ralph_error import RalphError
from src.domain.errors.session_not_found_error import SessionNotFoundError


def test_herda_de_ralph_error() -> None:
    assert issubclass(SessionNotFoundError, RalphError)


def test_carrega_o_session_id_informado() -> None:
    erro = SessionNotFoundError(session_id="sess_123")

    assert erro.session_id == "sess_123"


def test_mensagem_referencia_o_session_id() -> None:
    erro = SessionNotFoundError(session_id="sess_123")

    assert "sess_123" in str(erro)
