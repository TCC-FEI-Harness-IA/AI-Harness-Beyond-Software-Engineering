from datetime import UTC, datetime

from src.domain.entities.session.session_message import SessionMessage
from src.domain.entities.session.session_totals import SessionTotals
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_TIMESTAMP = datetime.now(tz=UTC)


def _nova_mensagem(
    tokens_input: int = 0,
    tokens_output: int = 0,
    inference_time_ms: int = 0,
) -> SessionMessage:
    return SessionMessage(
        id="msg-1",
        order=0,
        timestamp=_TIMESTAMP,
        phase=ThinkingPhaseEnum.DIRECT_INFERENCE,
        source=MessageSourceEnum.LLM_AGENT,
        content="conteudo",
        task_id=None,
        context_id=None,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        inference_time_ms=inference_time_ms,
        model_name=None,
    )


def test_defaults_de_totais_novos() -> None:
    totais = SessionTotals()

    assert totais.total_messages == 0
    assert totais.total_llm_calls == 0
    assert totais.tokens_input == 0
    assert totais.tokens_output == 0
    assert totais.inference_time_ms == 0
    assert totais.wall_time_ms == 0


def test_total_tokens_de_totais_novos_e_zero() -> None:
    assert SessionTotals().total_tokens == 0


def test_e_mutavel() -> None:
    totais = SessionTotals()

    totais.total_messages = 3

    assert totais.total_messages == 3


def test_mensagem_conta_apenas_como_mensagem_e_nunca_soma_consumo() -> None:
    """O consumo vem das invocações; somá-lo também pelas mensagens o contaria duas vezes."""
    totais = SessionTotals()

    totais.add_message(_nova_mensagem(tokens_input=10, tokens_output=20, inference_time_ms=500))
    totais.add_message(_nova_mensagem())

    assert totais.total_messages == 2
    assert totais.total_llm_calls == 0
    assert totais.total_tokens == 0
    assert totais.inference_time_ms == 0


def test_o_inicio_de_uma_invocacao_ja_conta_como_chamada() -> None:
    totais = SessionTotals()

    totais.register_invocation_start()
    totais.register_invocation_start()

    assert totais.total_llm_calls == 2
    assert totais.total_tokens == 0


def test_o_consumo_conhecido_de_uma_invocacao_e_acumulado() -> None:
    totais = SessionTotals()

    totais.add_usage(tokens_input=10, tokens_output=20, duration_ms=500)
    totais.add_usage(tokens_input=1, tokens_output=2, duration_ms=30)

    assert totais.tokens_input == 11
    assert totais.tokens_output == 22
    assert totais.total_tokens == 33
    assert totais.inference_time_ms == 530


def test_consumo_desconhecido_nao_soma_tokens_mas_soma_o_tempo() -> None:
    totais = SessionTotals()

    totais.add_usage(tokens_input=None, tokens_output=None, duration_ms=40)

    assert totais.total_tokens == 0
    assert totais.inference_time_ms == 40


def test_consumo_parcialmente_conhecido_soma_apenas_o_que_se_sabe() -> None:
    totais = SessionTotals()

    totais.add_usage(tokens_input=None, tokens_output=140, duration_ms=10)

    assert totais.tokens_input == 0
    assert totais.tokens_output == 140


def test_wall_time_nao_e_alterado_pelo_registro_de_mensagens_nem_de_consumo() -> None:
    totais = SessionTotals()

    totais.add_message(_nova_mensagem(tokens_input=10, tokens_output=20, inference_time_ms=500))
    totais.add_usage(tokens_input=10, tokens_output=20, duration_ms=500)

    assert totais.wall_time_ms == 0
