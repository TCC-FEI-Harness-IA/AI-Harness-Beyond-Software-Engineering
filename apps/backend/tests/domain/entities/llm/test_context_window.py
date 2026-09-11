from datetime import UTC, datetime

from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


def test_carrega_o_id_e_a_fase() -> None:
    janela = ContextWindow(context_id="ctx-1", phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    assert janela.context_id == "ctx-1"
    assert janela.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION


def test_defaults_de_uma_janela_nova() -> None:
    janela = ContextWindow(context_id="ctx-1", phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    assert janela.task_id is None
    assert janela.messages == []
    assert janela.tokens_input == 0
    assert janela.tokens_output == 0


def test_e_mutavel() -> None:
    janela = ContextWindow(context_id="ctx-1", phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    janela.tokens_input = 10

    assert janela.tokens_input == 10


def _mensagem(texto: str) -> Message:
    return Message(
        creation_timestamp=datetime(2026, 8, 31, 12, 0, tzinfo=UTC),
        text=texto,
        source=MessageSourceEnum.USER,
    )


def _consumo(tokens_input: int, tokens_output: int) -> TokensUsage:
    return TokensUsage(
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        llm_model=GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
    )


def test_janela_nova_esta_vazia_e_nao_acumulou_tokens() -> None:
    janela = ContextWindow(context_id="ctx-1", phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    assert janela.is_empty() is True
    assert janela.context_size == 0


def test_append_preserva_a_ordem_das_mensagens() -> None:
    janela = ContextWindow(context_id="ctx-1", phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)
    primeira = _mensagem("primeira")
    segunda = _mensagem("segunda")

    janela.append(message=primeira)
    janela.append(message=segunda)

    assert janela.messages == [primeira, segunda]


def test_is_empty_muda_apos_o_primeiro_append() -> None:
    janela = ContextWindow(context_id="ctx-1", phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    assert janela.is_empty() is True

    janela.append(message=_mensagem("primeira"))

    assert janela.is_empty() is False


def test_register_usage_acumula_entrada_e_saida() -> None:
    janela = ContextWindow(context_id="ctx-1", phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    janela.register_usage(tokens=_consumo(tokens_input=10, tokens_output=5))
    janela.register_usage(tokens=_consumo(tokens_input=3, tokens_output=7))

    assert janela.tokens_input == 13
    assert janela.tokens_output == 12


def test_context_size_reflete_a_soma_dos_tokens_da_janela() -> None:
    janela = ContextWindow(context_id="ctx-1", phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    janela.register_usage(tokens=_consumo(tokens_input=10, tokens_output=5))
    janela.register_usage(tokens=_consumo(tokens_input=3, tokens_output=7))

    assert janela.context_size == 25
