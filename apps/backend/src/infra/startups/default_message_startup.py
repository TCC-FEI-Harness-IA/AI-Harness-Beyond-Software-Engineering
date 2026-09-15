from inspect import getfile

from src.application.dtos.default_message_input_dto import DefaultMessageInputDTO
from src.application.usecases.default_message_usecase import DefaultMessageUseCase
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.adapters.id_generator_adapter import IdGeneratorAdapter
from src.infra.adapters.llm_completions_adapter import LLMCompletionsAdapter
from src.infra.adapters.model_catalog_adapter import ModelCatalogAdapter
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from src.infra.config.settings import Settings
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory
from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO
from src.infra.services.llm_service_factory import LLMServiceFactory


class DefaultMessageStartup:
    """Composition root do fluxo baseline.

    Constrói o grafo de dependências concreto e traduz os DTOs de transporte
    (Pydantic) para os DTOs da camada de aplicação, e o caminho inverso na saída.
    """

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências do fluxo baseline."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        llm_services = LLMServiceFactory(settings=self.settings).create_all()
        model_catalog = ModelCatalogAdapter(
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(ModelCatalogAdapter)),
        )
        llm_completions_adapter = LLMCompletionsAdapter(
            llm_services=llm_services,
            model_catalog=model_catalog,
            logger=self.settings.logger(module_file=getfile(LLMCompletionsAdapter)),
            settings=self.settings,
        )
        clock = ClockAdapter()
        session_repository = SessionRepositoryFactory(
            settings=self.settings,
            mapper=SessionDocumentMapper(),
        ).create()
        session_recorder = SessionRecorderAdapter(
            repository=session_repository,
            clock=clock,
            id_generator=IdGeneratorAdapter(settings=self.settings),
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(SessionRecorderAdapter)),
        )
        self.default_message_use_case = DefaultMessageUseCase(
            llm_completions=llm_completions_adapter,
            session_recorder=session_recorder,
            clock=clock,
            logger=self.settings.logger(module_file=getfile(DefaultMessageUseCase)),
        )
        self.logger.info("DefaultMessageStartup inicializado")

    async def run(self, payload: DefaultInputDTO) -> DefaultOutputDTO:
        """Executa o fluxo baseline a partir do corpo da requisição.

        Args:
            payload: Corpo da requisição no contrato de transporte.

        Returns:
            DefaultOutputDTO: Corpo da resposta no contrato de transporte.
        """
        self.logger.info("Executando fluxo default message")

        resultado = await self.default_message_use_case.execute(
            user_input=DefaultMessageInputDTO(
                user_input=payload.message.user_input,
                model_name=payload.llm_model_config.provider_config.model_name,
                max_tokens=payload.llm_model_config.max_tokens,
                temperature=payload.llm_model_config.temperature,
                provider=payload.llm_model_config.provider,
            )
        )

        return DefaultOutputDTO(
            message=resultado.message,
            response=resultado.response,
            session_id=resultado.session_id,
            tokens_input=resultado.tokens_input,
            tokens_output=resultado.tokens_output,
            inference_time_ms=resultado.inference_time_ms,
        )
