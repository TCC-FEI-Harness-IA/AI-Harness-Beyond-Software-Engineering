from inspect import getfile
from typing import AsyncGenerator

from src.application.dtos.ralph_thinking_input_dto import RalphThinkingInputDTO
from src.application.phases.additional_planning_phase import AdditionalPlanningPhase
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
from src.domain.interfaces.settings_interface import ISettings
from src.domain.services.learnings_memory import LearningsMemory
from src.domain.services.task_queue import TaskQueue
from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.adapters.context_window_factory_adapter import ContextWindowFactoryAdapter
from src.infra.adapters.cost_guard_adapter import CostGuardAdapter
from src.infra.adapters.id_generator_adapter import IdGeneratorAdapter
from src.infra.adapters.llm_completions_adapter import LLMCompletionsAdapter
from src.infra.adapters.model_catalog_adapter import ModelCatalogAdapter
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from src.infra.config.settings import Settings
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory
from src.infra.routes.v1.message.dtos.context_window_dto import ContextWindowDTO
from src.infra.routes.v1.message.dtos.reasoning_event_dto import ReasoningEventDTO
from src.infra.routes.v1.message.dtos.reasoning_input_dto import ReasoningInputDTO
from src.infra.services.llm_service_factory import LLMServiceFactory


class RalphThinkingStartup:
    """Composition root do fluxo harness (Ralph Loop adaptado).

    É instanciado uma vez por conexão WebSocket, porque `TaskQueue`,
    `LearningsMemory`, `CostGuardAdapter` e `SessionRecorderAdapter` carregam
    estado da sessão em execução.
    """

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências do fluxo harness."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        self.clock = ClockAdapter()
        self.id_generator = IdGeneratorAdapter(settings=self.settings)

        self.session_document_mapper = SessionDocumentMapper()
        self.session_repository = SessionRepositoryFactory(
            settings=self.settings,
            mapper=self.session_document_mapper,
        ).create()
        self.session_recorder = SessionRecorderAdapter(
            repository=self.session_repository,
            clock=self.clock,
            id_generator=self.id_generator,
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(SessionRecorderAdapter)),
        )

        self.cost_budget = CostBudget(
            max_task_attempts=self.settings.ralph_max_task_attempts,
            max_additional_planning_rounds=self.settings.ralph_max_additional_planning_rounds,
            max_tasks_per_session=self.settings.ralph_max_tasks_per_session,
            max_llm_calls_per_session=self.settings.ralph_max_llm_calls_per_session,
            session_token_budget=self.settings.ralph_session_token_budget,
            final_answer_token_reserve=self.settings.ralph_final_answer_token_reserve,
            session_timeout_seconds=self.settings.ralph_session_timeout_seconds,
        )
        self.cost_guard = CostGuardAdapter(
            budget=self.cost_budget,
            clock=self.clock,
            logger=self.settings.logger(module_file=getfile(CostGuardAdapter)),
        )

        self.template_provider = FilePromptTemplateProvider(
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(FilePromptTemplateProvider)),
        )
        self.parser = StructuredResponseParserAdapter(
            logger=self.settings.logger(module_file=getfile(StructuredResponseParserAdapter)),
        )
        self.context_window_factory = ContextWindowFactoryAdapter(id_generator=self.id_generator)

        llm_services = LLMServiceFactory(settings=self.settings).create_all()
        model_catalog = ModelCatalogAdapter(
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(ModelCatalogAdapter)),
        )
        self.llm_completions = LLMCompletionsAdapter(
            llm_services=llm_services,
            model_catalog=model_catalog,
            logger=self.settings.logger(module_file=getfile(LLMCompletionsAdapter)),
            settings=self.settings,
        )

        self.general_criteria_phase = GeneralCriteriaPhase(**self.__phase_dependencies(GeneralCriteriaPhase))
        self.task_decomposition_phase = TaskDecompositionPhase(**self.__phase_dependencies(TaskDecompositionPhase))
        self.task_resolution_phase = TaskResolutionPhase(**self.__phase_dependencies(TaskResolutionPhase))
        self.task_verification_phase = TaskVerificationPhase(**self.__phase_dependencies(TaskVerificationPhase))
        self.learnings_extraction_phase = LearningsExtractionPhase(
            **self.__phase_dependencies(LearningsExtractionPhase)
        )
        self.global_verification_phase = GlobalVerificationPhase(
            **self.__phase_dependencies(GlobalVerificationPhase)
        )
        self.additional_planning_phase = AdditionalPlanningPhase(
            **self.__phase_dependencies(AdditionalPlanningPhase)
        )
        self.final_answer_phase = FinalAnswerPhase(**self.__phase_dependencies(FinalAnswerPhase))

        self.task_queue = TaskQueue()
        self.learnings_memory = LearningsMemory()

        self.ralph_thinking_use_case = RalphThinkingUseCase(
            general_criteria_phase=self.general_criteria_phase,
            task_decomposition_phase=self.task_decomposition_phase,
            task_resolution_phase=self.task_resolution_phase,
            task_verification_phase=self.task_verification_phase,
            learnings_extraction_phase=self.learnings_extraction_phase,
            global_verification_phase=self.global_verification_phase,
            additional_planning_phase=self.additional_planning_phase,
            final_answer_phase=self.final_answer_phase,
            task_queue=self.task_queue,
            learnings_memory=self.learnings_memory,
            context_window_factory=self.context_window_factory,
            cost_guard=self.cost_guard,
            session_recorder=self.session_recorder,
            clock=self.clock,
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(RalphThinkingUseCase)),
        )
        self.logger.info("RalphThinkingStartup inicializado")

    async def run(self, payload: ReasoningInputDTO) -> AsyncGenerator[ReasoningEventDTO, None]:
        """Executa o fluxo harness a partir do frame de abertura do WebSocket.

        Args:
            payload: Frame de abertura no contrato de transporte.

        Yields:
            ReasoningEventDTO: Evento de transporte equivalente a cada `ThinkingEvent`
            emitido pelo caso de uso.
        """
        input_dto = RalphThinkingInputDTO(
            user_input=payload.message.user_input,
            model_name=payload.llm_model_config.provider_config.model_name,
            max_tokens=payload.llm_model_config.max_tokens,
            temperature=payload.llm_model_config.temperature,
            provider=payload.llm_model_config.provider,
        )
        async for event in self.ralph_thinking_use_case.execute(input_dto=input_dto):
            yield self.__to_event_dto(event=event)

    def __to_event_dto(self, event: ThinkingEvent) -> ReasoningEventDTO:
        """Converte um `ThinkingEvent` de domínio no seu equivalente de transporte.

        Args:
            event: Evento emitido pelo caso de uso.

        Returns:
            ReasoningEventDTO: Evento pronto para ser serializado no WebSocket.
        """
        return ReasoningEventDTO(
            type=event.type.value,
            subtype=event.subtype.value,
            phase=event.phase.value,
            task=event.task,
            session_id=event.session_id,
            content=event.content,
            total_tokens=event.total_tokens,
            context_window=ContextWindowDTO(context_id=event.context_id, context_size=event.context_size),
            inference_time_ms=event.inference_time_ms,
        )

    def __phase_dependencies(self, phase_class: type) -> dict[str, object]:
        """Monta o mapa de dependências comuns injetadas em toda `IThinkingPhase`.

        Args:
            phase_class: Classe concreta da fase, usada para nomear o logger.

        Returns:
            dict[str, object]: Dependências prontas para desempacotar no construtor da fase.
        """
        return {
            "llm_completions": self.llm_completions,
            "template_provider": self.template_provider,
            "parser": self.parser,
            "cost_guard": self.cost_guard,
            "clock": self.clock,
            "settings": self.settings,
            "logger": self.settings.logger(module_file=getfile(phase_class)),
        }
