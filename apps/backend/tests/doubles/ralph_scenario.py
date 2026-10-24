import logging
from typing import AsyncGenerator

from src.application.dtos.ralph_thinking_input_dto import RalphThinkingInputDTO
from src.application.phases.additional_planning_phase import AdditionalPlanningPhase
from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.application.phases.final_answer_phase import FinalAnswerPhase
from src.application.phases.general_criteria_phase import GeneralCriteriaPhase
from src.application.phases.global_verification_phase import GlobalVerificationPhase
from src.application.phases.learnings_extraction_phase import LearningsExtractionPhase
from src.application.phases.task_decomposition_phase import TaskDecompositionPhase
from src.application.phases.task_resolution_phase import TaskResolutionPhase
from src.application.phases.task_verification_phase import TaskVerificationPhase
from src.application.usecases.ralph_thinking_usecase import RalphThinkingUseCase
from src.domain.entities.resilience.cost_budget import CostBudget
from src.domain.entities.thinking.thinking_event import ThinkingEvent
from src.domain.interfaces.cost_guard_interface import ICostGuard
from src.domain.interfaces.llm_completions_interface import ILLMCompletions
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.services.learnings_memory import LearningsMemory
from src.domain.services.task_queue import TaskQueue
from src.infra.adapters.context_window_factory_adapter import ContextWindowFactoryAdapter
from src.infra.adapters.cost_guard_adapter import CostGuardAdapter
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_id_generator import FakeIdGenerator
from tests.doubles.fake_prompt_template_provider import FakePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.in_memory_session_repository import InMemorySessionRepository
from tests.doubles.scripted_llm_completions import ScriptedLLMCompletions

_PERGUNTA_DO_PAPER = "Qual dos seguintes números é simultaneamente primo, par e maior que 2? A) 2 B) 4 C) 6 D) NDA"
_MODELO = "vendor/modelo-padrao"
_MAX_TOKENS = 1200
_TEMPERATURA = 0.3
_PROVEDOR = ModelProviderEnum.OPEN_ROUTER
_PASSO_MONOTONICO_MS = 7
_CHAMADAS_MAXIMAS = 400


class RalphScenario:
    """Monta o `RalphThinkingUseCase` inteiro com dublês e expõe cada peça.

    Só a porta de completions é falsa por obrigação; o parser, o gravador de
    sessão, a fila e a memória de aprendizados são as implementações reais, de
    forma que o cenário exercite a fiação completa do fluxo. O guardião de custo
    é o dublê programável por padrão; informar `budget` troca-o pelo
    `CostGuardAdapter` real, para os cenários que provam a política de orçamento.
    """

    def __init__(
        self,
        responses: list[str],
        cost_guard: FakeCostGuard | None = None,
        settings: FakeSettings | None = None,
        tokens_input: int = 10,
        tokens_output: int = 5,
        error: Exception | None = None,
        budget: CostBudget | None = None,
        llm: ILLMCompletions | None = None,
        clock_step_ms: int = _PASSO_MONOTONICO_MS,
        max_tokens: int = _MAX_TOKENS,
        temperature: float = _TEMPERATURA,
        repository: InMemorySessionRepository | None = None,
    ) -> None:
        """Monta o grafo do caso de uso para um roteiro de respostas do modelo.

        Args:
            responses: Fila de saídas brutas do modelo, uma por chamada.
            cost_guard: Guardião de custo programável do cenário.
            settings: Configurações do cenário.
            tokens_input: Tokens de entrada contabilizados por chamada.
            tokens_output: Tokens de saída contabilizados por chamada.
            error: Exceção levantada pela porta de completions, quando informada.
            budget: Limites do guardião real; quando informado, substitui `cost_guard`.
            llm: Porta de completions alternativa; quando informada, substitui o roteiro de `responses`.
            clock_step_ms: Avanço do relógio monotônico a cada leitura.
            max_tokens: Teto de tokens de saída pedido ao modelo em cada chamada.
            temperature: Temperatura pedida ao modelo em cada chamada.
            repository: Repositório de sessões alternativo, para os cenários de falha de persistência.
        """
        self.max_tokens = max_tokens
        self.temperature = temperature
        logger = logging.getLogger("teste.ralph")
        self.llm = llm or ScriptedLLMCompletions(
            responses=responses,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            error=error,
        )
        self.template_provider = FakePromptTemplateProvider()
        self.parser = StructuredResponseParserAdapter(logger=logger)
        self.settings = settings or FakeSettings()
        self.clock = FakeClock(
            monotonic_values=[passo * clock_step_ms for passo in range(_CHAMADAS_MAXIMAS)]
        )
        self.cost_guard: ICostGuard = (
            CostGuardAdapter(budget=budget, clock=self.clock, logger=logger)
            if budget is not None
            else cost_guard or FakeCostGuard()
        )
        self.id_generator = FakeIdGenerator()
        self.repository = repository or InMemorySessionRepository()
        self.recorder = SessionRecorderAdapter(
            repository=self.repository,
            clock=self.clock,
            id_generator=self.id_generator,
            settings=self.settings,
            logger=logger,
        )
        self.context_window_factory = ContextWindowFactoryAdapter(id_generator=self.id_generator)
        self.task_queue = TaskQueue()
        self.learnings_memory = LearningsMemory()
        self.use_case = RalphThinkingUseCase(
            general_criteria_phase=self.__phase(GeneralCriteriaPhase),
            task_decomposition_phase=self.__phase(TaskDecompositionPhase),
            task_resolution_phase=self.__phase(TaskResolutionPhase),
            task_verification_phase=self.__phase(TaskVerificationPhase),
            learnings_extraction_phase=self.__phase(LearningsExtractionPhase),
            global_verification_phase=self.__phase(GlobalVerificationPhase),
            additional_planning_phase=self.__phase(AdditionalPlanningPhase),
            final_answer_phase=self.__phase(FinalAnswerPhase),
            task_queue=self.task_queue,
            learnings_memory=self.learnings_memory,
            context_window_factory=self.context_window_factory,
            cost_guard=self.cost_guard,
            session_recorder=self.recorder,
            clock=self.clock,
            settings=self.settings,
            logger=logger,
        )

    @property
    def session(self):
        """Sessão persistida pelo cenário.

        Returns:
            Session: Última versão gravada no repositório em memória.
        """
        return self.repository.sessions[self.recorder.session.id]

    def stream(self, question: str = _PERGUNTA_DO_PAPER) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa o fluxo devolvendo o gerador de eventos.

        Args:
            question: Pergunta do usuário submetida ao fluxo.

        Returns:
            AsyncGenerator[ThinkingEvent, None]: Fluxo de eventos do pensamento.
        """
        return self.use_case.execute(
            input_dto=RalphThinkingInputDTO(
                user_input=question,
                model_name=_MODELO,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                provider=_PROVEDOR,
            )
        )

    async def run(self, question: str = _PERGUNTA_DO_PAPER) -> list[ThinkingEvent]:
        """Executa o fluxo inteiro e coleta todos os eventos emitidos.

        Args:
            question: Pergunta do usuário submetida ao fluxo.

        Returns:
            list[ThinkingEvent]: Eventos emitidos, em ordem.
        """
        return [event async for event in self.stream(question=question)]

    def __phase(self, phase_class: type[BaseThinkingPhase]) -> BaseThinkingPhase:
        """Monta uma fase com as dependências compartilhadas do cenário."""
        return phase_class(
            llm_completions=self.llm,
            template_provider=self.template_provider,
            parser=self.parser,
            cost_guard=self.cost_guard,
            session_recorder=self.recorder,
            clock=self.clock,
            settings=self.settings,
            logger=logging.getLogger("teste.fase"),
        )
