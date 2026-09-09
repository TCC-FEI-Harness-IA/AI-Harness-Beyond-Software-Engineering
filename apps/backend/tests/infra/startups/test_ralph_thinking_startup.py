import pytest

from src.application.usecases.ralph_thinking_usecase import RalphThinkingUseCase
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.context_window_factory_interface import IContextWindowFactory
from src.domain.interfaces.cost_guard_interface import ICostGuard
from src.domain.interfaces.id_generator_interface import IIdGenerator
from src.domain.interfaces.learnings_memory_interface import ILearningsMemory
from src.domain.interfaces.llm_completions_interface import ILLMCompletions
from src.domain.interfaces.prompt_template_provider_interface import IPromptTemplateProvider
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper
from src.domain.interfaces.session_recorder_interface import ISessionRecorder
from src.domain.interfaces.session_repository_interface import ISessionRepository
from src.domain.interfaces.structured_response_parser_interface import IStructuredResponseParser
from src.domain.interfaces.task_queue_interface import ITaskQueue
from src.domain.interfaces.thinking_phase_interface import IThinkingPhase
from src.infra.startups.ralph_thinking_startup import RalphThinkingStartup

_PHASE_ATTRIBUTES = (
    "general_criteria_phase",
    "task_decomposition_phase",
    "task_resolution_phase",
    "task_verification_phase",
    "learnings_extraction_phase",
    "global_verification_phase",
    "additional_planning_phase",
    "final_answer_phase",
)


@pytest.fixture(autouse=True)
def ambiente_de_modelo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Garante configuração suficiente para o grafo do startup ser construído."""
    monkeypatch.setenv("OPENROUTER_MODEL", "vendor/modelo")
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GENAI_AVAILABLE_MODELS", "vendor/modelo")
    monkeypatch.setenv("GENAI_AVAILABLE_PROVIDERS", "open_router")


def test_constroi_todo_o_grafo_sem_deixar_atributo_nulo() -> None:
    startup = RalphThinkingStartup()

    assert vars(startup)
    assert all(valor is not None for valor in vars(startup).values())


def test_injeta_as_oito_fases_pela_interface() -> None:
    startup = RalphThinkingStartup()

    for atributo in _PHASE_ATTRIBUTES:
        assert isinstance(getattr(startup, atributo), IThinkingPhase)


def test_injeta_os_adapters_de_infraestrutura_pela_interface() -> None:
    startup = RalphThinkingStartup()

    assert isinstance(startup.clock, IClock)
    assert isinstance(startup.id_generator, IIdGenerator)
    assert isinstance(startup.session_document_mapper, ISessionDocumentMapper)
    assert isinstance(startup.session_repository, ISessionRepository)
    assert isinstance(startup.session_recorder, ISessionRecorder)
    assert isinstance(startup.cost_guard, ICostGuard)
    assert isinstance(startup.template_provider, IPromptTemplateProvider)
    assert isinstance(startup.parser, IStructuredResponseParser)
    assert isinstance(startup.context_window_factory, IContextWindowFactory)
    assert isinstance(startup.llm_completions, ILLMCompletions)
    assert isinstance(startup.task_queue, ITaskQueue)
    assert isinstance(startup.learnings_memory, ILearningsMemory)


def test_injeta_o_caso_de_uso_do_fluxo_harness() -> None:
    startup = RalphThinkingStartup()

    assert isinstance(startup.ralph_thinking_use_case, RalphThinkingUseCase)
