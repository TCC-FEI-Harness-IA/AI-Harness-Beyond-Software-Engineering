from src.domain.entities.llm.context_window import ContextWindow
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.adapters.context_window_factory_adapter import ContextWindowFactoryAdapter
from tests.doubles.fake_id_generator import FakeIdGenerator


def _fabrica() -> ContextWindowFactoryAdapter:
    return ContextWindowFactoryAdapter(id_generator=FakeIdGenerator())


def test_cria_uma_janela_vazia_com_a_fase_pedida() -> None:
    janela = _fabrica().create(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION, task_id="T1")

    assert isinstance(janela, ContextWindow)
    assert janela.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert janela.task_id == "T1"
    assert janela.is_empty() is True
    assert janela.context_size == 0


def test_sem_tarefa_associada_a_janela_nasce_sem_task_id() -> None:
    janela = _fabrica().create(phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION)

    assert janela.task_id is None


def test_toda_chamada_gera_uma_identidade_nova() -> None:
    fabrica = _fabrica()

    primeira = fabrica.create(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION, task_id="T1")
    segunda = fabrica.create(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION, task_id="T1")

    assert primeira.context_id != segunda.context_id
