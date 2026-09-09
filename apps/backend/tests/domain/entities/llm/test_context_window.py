from src.domain.entities.llm.context_window import ContextWindow
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
