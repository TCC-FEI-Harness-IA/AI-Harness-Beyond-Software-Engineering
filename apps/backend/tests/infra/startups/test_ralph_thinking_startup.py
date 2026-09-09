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


_LIMITES_DE_AMBIENTE = {
    "RALPH_MAX_TASK_ATTEMPTS": "7",
    "RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS": "4",
    "RALPH_MAX_TASKS_PER_SESSION": "9",
    "RALPH_MAX_LLM_CALLS_PER_SESSION": "33",
    "RALPH_SESSION_TOKEN_BUDGET": "5000",
    "RALPH_FINAL_ANSWER_TOKEN_RESERVE": "500",
    "RALPH_SESSION_TIMEOUT_SECONDS": "42",
}


def test_monta_o_budget_com_os_valores_do_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for variavel, valor in _LIMITES_DE_AMBIENTE.items():
        monkeypatch.setenv(variavel, valor)

    budget = RalphThinkingStartup().cost_budget

    assert budget.max_task_attempts == 7
    assert budget.max_additional_planning_rounds == 4
    assert budget.max_tasks_per_session == 9
    assert budget.max_llm_calls_per_session == 33
    assert budget.session_token_budget == 5000
    assert budget.final_answer_token_reserve == 500
    assert budget.session_timeout_seconds == 42


def test_alterar_variavel_de_ambiente_altera_o_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RALPH_MAX_TASK_ATTEMPTS", "3")
    antes = RalphThinkingStartup().cost_budget

    monkeypatch.setenv("RALPH_MAX_TASK_ATTEMPTS", "8")
    depois = RalphThinkingStartup().cost_budget

    assert antes.max_task_attempts == 3
    assert depois.max_task_attempts == 8


def test_injeta_o_mesmo_guardiao_de_custo_em_todos_os_consumidores() -> None:
    startup = RalphThinkingStartup()

    assert startup.ralph_thinking_use_case.cost_guard is startup.cost_guard
    for atributo in _PHASE_ATTRIBUTES:
        assert getattr(startup, atributo).cost_guard is startup.cost_guard


def test_o_guardiao_de_custo_usa_o_budget_montado_pelo_startup() -> None:
    startup = RalphThinkingStartup()

    assert startup.cost_guard.budget is startup.cost_budget
