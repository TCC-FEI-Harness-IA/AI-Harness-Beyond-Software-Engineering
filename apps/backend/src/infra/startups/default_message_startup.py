from src.domain.entities.session.benchmark_details import BenchmarkDetails
from inspect import getfile

from src.application.dtos.default_message_input_dto import DefaultMessageInputDTO
from src.application.usecases.default_message_usecase import DefaultMessageUseCase
from src.domain.interfaces.settings_interface import ISettings
from src.domain.services.execution_authorization import ExecutionAuthorization
from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.adapters.id_generator_adapter import IdGeneratorAdapter
from src.infra.adapters.llm_completions_adapter import LLMCompletionsAdapter
from src.infra.adapters.model_catalog_adapter import ModelCatalogAdapter
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from src.infra.config.settings import Settings
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.model_catalog_repository_factory import ModelCatalogRepositoryFactory
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory
from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO
from src.infra.services.llm_service_factory import LLMServiceFactory


# O catálogo só complementa a allowlist: com o MongoDB fora do ar, a execução espera pouco por ele.
_MODEL_CATALOG_TIMEOUT_MS = 2000


class DefaultMessageStartup:
    """Composition root do fluxo baseline.

    Constrói o grafo de dependências concreto e traduz os DTOs de transporte
    (Pydantic) para os DTOs da camada de aplicação, e o caminho inverso na saída.
    """

    def __init__(
        self,
        owner_id: str,
        authorization: ExecutionAuthorization,
        benchmark_details: BenchmarkDetails | None = None,
    ) -> None:
        """Instancia e injeta todas as dependências do fluxo baseline.

        Args:
            owner_id: Conta autenticada dona da sessão criada.
            authorization: Autorização da requisição, com a credencial OpenRouter do usuário.
            benchmark_details: Metadados de benchmark, quando o fluxo roda dentro de uma bateria.
        """
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        llm_services = LLMServiceFactory(settings=self.settings).create_all(authorization=authorization)
        self.model_catalog = ModelCatalogAdapter(
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(ModelCatalogAdapter)),
            model_repository=ModelCatalogRepositoryFactory(
                settings=self.settings, server_selection_timeout_ms=_MODEL_CATALOG_TIMEOUT_MS
            ).create(owner_id=owner_id),
        )
        llm_completions_adapter = LLMCompletionsAdapter(
            llm_services=llm_services,
            model_catalog=self.model_catalog,
            logger=self.settings.logger(module_file=getfile(LLMCompletionsAdapter)),
            settings=self.settings,
        )
        clock = ClockAdapter()
        session_repository = SessionRepositoryFactory(
            settings=self.settings,
            mapper=SessionDocumentMapper(),
        ).create(owner_id=owner_id)
        session_recorder = SessionRecorderAdapter(
            benchmark_details=benchmark_details,
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
        await self.model_catalog.load_model_info(
            model_name=payload.llm_model_config.provider_config.model_name
        )

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
