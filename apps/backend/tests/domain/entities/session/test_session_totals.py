from src.domain.entities.session.session_totals import SessionTotals


def test_defaults_de_totais_novos() -> None:
    totais = SessionTotals()

    assert totais.total_messages == 0
    assert totais.total_llm_calls == 0
    assert totais.tokens_input == 0
    assert totais.tokens_output == 0
    assert totais.inference_time_ms == 0
    assert totais.wall_time_ms == 0


def test_e_mutavel() -> None:
    totais = SessionTotals()

    totais.total_messages = 3

    assert totais.total_messages == 3
