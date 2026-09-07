from inspect import getfile

from src.application.dtos.default_message_input_dto import DefaultMessageInputDTO
from src.application.usecases.default_message_usecase import DefaultMessageUseCase
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.llm_completions_adapter import LLMCompletionsAdapter
from src.infra.adapters.model_catalog_adapter import ModelCatalogAdapter
from src.infra.config.settings import Settings
from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO
from src.infra.services.openrouter_service import OpenRouterService


class DefaultMessageStartup:
    """Composition root do fluxo baseline.

    Constrói o grafo de dependências concreto e traduz os DTOs de transporte
    (Pydantic) para os DTOs da camada de aplicação, e o caminho inverso na saída.
    """

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências do fluxo baseline."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        llm_service = OpenRouterService(
            logger=self.settings.logger(module_file=getfile(OpenRouterService)),
            settings=self.settings,
        )
        model_catalog = ModelCatalogAdapter(
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(ModelCatalogAdapter)),
        )
        llm_completions_adapter = LLMCompletionsAdapter(
            llm_service=llm_service,
            model_catalog=model_catalog,
            logger=self.settings.logger(module_file=getfile(LLMCompletionsAdapter)),
            settings=self.settings,
        )
        self.default_message_use_case = DefaultMessageUseCase(
            llm_completions=llm_completions_adapter,
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
            )
        )

        return DefaultOutputDTO(message=resultado.message, response=resultado.response)
