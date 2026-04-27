from inspect import getfile

from src.application.usecases.default_message_usecase import DefaultMessageUseCase
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.llm_complitions_adapter import LLMComplitionsAdapter
from src.infra.config.settings import Settings
from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO
from src.infra.services.openrouter_service import OpenRouterService


class DefaultMessageStartup:
    def __init__(self) -> None:
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        llm_service = OpenRouterService(
            logger=self.settings.logger(module_file=getfile(OpenRouterService)),
            settings=self.settings,
        )
        llm_completions_adapter = LLMComplitionsAdapter(
            llm_service=llm_service,
            logger=self.settings.logger(module_file=getfile(LLMComplitionsAdapter)),
            settings=self.settings,
        )
        self.default_message_use_case = DefaultMessageUseCase(
            llm_completions=llm_completions_adapter,
            logger=self.settings.logger(module_file=getfile(DefaultMessageUseCase)),
        )
        self.logger.info("DefaultMessageStartup inicializado")

    def run(self, payload: DefaultInputDTO) -> DefaultOutputDTO:
        self.logger.info("Executando fluxo default message")
        return self.default_message_use_case.execute(user_input=payload)
