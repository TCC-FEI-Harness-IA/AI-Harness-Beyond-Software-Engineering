from typing import Any, AsyncGenerator

import pytest

from src.application.dtos.ralph_thinking_input_dto import RalphThinkingInputDTO
from src.application.usecases.ralph_thinking_usecase import RalphThinkingUseCase
from src.domain.entities.thinking.thinking_event import ThinkingEvent
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
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
from src.infra.routes.v1.message.dtos.reasoning_event_dto import ReasoningEventDTO
from src.infra.routes.v1.message.dtos.reasoning_input_dto import ReasoningInputDTO
from src.infra.startups.ralph_thinking_startup import RalphThinkingStartup

_PHASE_ATTRIBUTES = (
    "general_criteria_phase",
    "task_decomposition_phase",
    "planning_learnings_phase",
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
    monkeypatch.setenv("LLM_MODEL", "vendor/modelo")
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GENAI_AVAILABLE_MODELS", "vendor/modelo")
    monkeypatch.setenv("GENAI_AVAILABLE_PROVIDERS", "open_router,openai")


def test_constroi_todo_o_grafo_sem_deixar_atributo_nulo() -> None:
    startup = RalphThinkingStartup()

    assert vars(startup)
    assert all(valor is not None for valor in vars(startup).values())


def test_injeta_as_nove_fases_pela_interface() -> None:
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


def test_injeta_o_mesmo_registro_de_sessao_em_todas_as_fases_e_no_caso_de_uso() -> None:
    """As fases gravam cada invocação na mesma sessão que o caso de uso acompanha."""
    startup = RalphThinkingStartup()

    assert startup.ralph_thinking_use_case.session_recorder is startup.session_recorder
    for atributo in _PHASE_ATTRIBUTES:
        assert getattr(startup, atributo).session_recorder is startup.session_recorder


def test_o_guardiao_de_custo_usa_o_budget_montado_pelo_startup() -> None:
    startup = RalphThinkingStartup()

    assert startup.cost_guard.budget is startup.cost_budget


def test_injeta_a_mesma_porta_de_completions_em_todas_as_fases() -> None:
    startup = RalphThinkingStartup()

    for atributo in _PHASE_ATTRIBUTES:
        assert getattr(startup, atributo).llm_completions is startup.llm_completions


def test_injeta_as_pecas_de_estado_da_sessao_no_caso_de_uso() -> None:
    startup = RalphThinkingStartup()

    assert startup.ralph_thinking_use_case.task_queue is startup.task_queue
    assert startup.ralph_thinking_use_case.learnings_memory is startup.learnings_memory
    assert startup.ralph_thinking_use_case.session_recorder is startup.session_recorder
    assert startup.ralph_thinking_use_case.context_window_factory is startup.context_window_factory


def test_cada_instanciacao_produz_estado_de_sessao_proprio() -> None:
    primeiro = RalphThinkingStartup()
    segundo = RalphThinkingStartup()

    assert primeiro.task_queue is not segundo.task_queue
    assert primeiro.learnings_memory is not segundo.learnings_memory
    assert primeiro.cost_guard is not segundo.cost_guard
    assert primeiro.session_recorder is not segundo.session_recorder


_REASONING_PAYLOAD = ReasoningInputDTO.model_validate(
    {
        "message": {"user_input": "pergunta do usuario"},
        # Um provedor diferente do default do ambiente prova que o `provider` que vale é
        # o do frame de abertura, e não o de `LLM_PROVIDER`.
        "llm_model_config": {
            "provider": "openai",
            "provider_config": {"model_name": "vendor/modelo"},
            "max_tokens": 1200,
            "temperature": 0.3,
        },
    }
)

_EVENT = ThinkingEvent(
    type=ThinkingEventTypeEnum.THINKING,
    subtype=ThinkingEventSubtypeEnum.EXECUTE,
    phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
    task="T1",
    content="markdown renderizavel",
    session_id="sess_01J",
    total_tokens=642,
    context_id="3a7f2b1",
    context_size=182,
    inference_time_ms=812,
)


class _FakeUseCase:
    """Dublê do caso de uso, para isolar a tradução feita pelo `run`."""

    def __init__(self, events: list[ThinkingEvent]) -> None:
        self.events = events
        self.received_input_dto: RalphThinkingInputDTO | None = None

    async def execute(self, input_dto: RalphThinkingInputDTO) -> AsyncGenerator[ThinkingEvent, None]:
        self.received_input_dto = input_dto
        for event in self.events:
            yield event


async def _collect(generator: AsyncGenerator[Any, None]) -> list[Any]:
    return [item async for item in generator]


async def test_run_traduz_o_payload_de_transporte_para_o_dto_de_aplicacao() -> None:
    startup = RalphThinkingStartup()
    fake_use_case = _FakeUseCase(events=[_EVENT])
    startup.ralph_thinking_use_case = fake_use_case

    await _collect(startup.run(payload=_REASONING_PAYLOAD))

    assert fake_use_case.received_input_dto == RalphThinkingInputDTO(
        user_input="pergunta do usuario",
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.3,
        provider=ModelProviderEnum.OPENAI,
    )


async def test_run_converte_cada_thinking_event_em_reasoning_event_dto() -> None:
    startup = RalphThinkingStartup()
    startup.ralph_thinking_use_case = _FakeUseCase(events=[_EVENT])

    eventos = await _collect(startup.run(payload=_REASONING_PAYLOAD))

    assert eventos == [
        ReasoningEventDTO(
            type="thinking",
            subtype="execute",
            phase="B1",
            task="T1",
            session_id="sess_01J",
            content="markdown renderizavel",
            total_tokens=642,
            context_window={"context_id": "3a7f2b1", "context_size": 182},
            inference_time_ms=812,
        )
    ]


async def test_run_devolve_um_evento_por_evento_emitido_pelo_caso_de_uso() -> None:
    startup = RalphThinkingStartup()
    outro_evento = ThinkingEvent(
        type=ThinkingEventTypeEnum.RESULT,
        subtype=ThinkingEventSubtypeEnum.COMPILE,
        phase=ThinkingPhaseEnum.C3_FINAL_ANSWER,
        task="synthesis",
        content="resposta final",
        session_id="sess_01J",
        total_tokens=900,
        context_id="9f1a2b3",
        context_size=50,
        inference_time_ms=120,
    )
    startup.ralph_thinking_use_case = _FakeUseCase(events=[_EVENT, outro_evento])

    eventos = await _collect(startup.run(payload=_REASONING_PAYLOAD))

    assert [evento.type for evento in eventos] == ["thinking", "result"]
