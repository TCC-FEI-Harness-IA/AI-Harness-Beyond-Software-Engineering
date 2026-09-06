from collections.abc import AsyncGenerator
from inspect import getfile
from typing import Any

from src.application.usecases.ralph_loop_usecase import RalphLoopUseCase
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.llm_complitions_adapter import LLMComplitionsAdapter
from src.infra.config.settings import Settings
from src.infra.routes.v1.message.dtos.reasoning_input_dto import ReasoningInputDTO
from src.infra.services.azure_foundry_service import AzureFoundryService
from src.infra.services.mock_llm_service import MockLLMService
from src.infra.services.openrouter_service import OpenRouterService


class RalphLoopStartup:
    """Startup de injeção de dependências e composição para o Ralph Loop Harness."""

    def __init__(self) -> None:
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        azure_service = AzureFoundryService(
            logger=self.settings.logger(module_file=getfile(AzureFoundryService)),
            settings=self.settings,
        )
        openrouter_service = OpenRouterService(
            logger=self.settings.logger(module_file=getfile(OpenRouterService)),
            settings=self.settings,
        )
        mock_service = MockLLMService(
            logger=self.settings.logger(module_file=getfile(MockLLMService)),
            settings=self.settings,
        )

        additional_services: dict[ModelProviderEnum, ILLMService] = {
            ModelProviderEnum.OPEN_ROUTER: openrouter_service,
            ModelProviderEnum.MOCK: mock_service,
        }

        self.llm_completions_adapter = LLMComplitionsAdapter(
            llm_service=azure_service,
            logger=self.settings.logger(module_file=getfile(LLMComplitionsAdapter)),
            settings=self.settings,
            additional_services=additional_services,
        )

        self.ralph_loop_use_case = RalphLoopUseCase(
            llm_completions=self.llm_completions_adapter,
            logger=self.settings.logger(module_file=getfile(RalphLoopUseCase)),
        )

        self.logger.info("RalphLoopStartup inicializado com sucesso.")

    async def run_stream(self, payload: ReasoningInputDTO) -> AsyncGenerator[str, None]:
        """Executa streaming SSE do Ralph Loop."""
        provider = payload.llm_model_config.provider
        model_name = payload.llm_model_config.provider_config.model_name
        endpoint = payload.llm_model_config.provider_config.endpoint
        max_tokens = payload.llm_model_config.max_tokens

        async for chunk in self.ralph_loop_use_case.execute_stream(
            user_input=payload.message.user_input,
            model_name=model_name,
            provider=provider,
            endpoint=endpoint,
            max_tokens=max_tokens,
        ):
            yield chunk

    async def run_sync(self, payload: ReasoningInputDTO) -> dict[str, Any]:
        """Executa o Ralph Loop de forma síncrona/consolidada para benchmarks."""
        provider = payload.llm_model_config.provider
        model_name = payload.llm_model_config.provider_config.model_name
        endpoint = payload.llm_model_config.provider_config.endpoint
        max_tokens = payload.llm_model_config.max_tokens

        summary = await self.ralph_loop_use_case.execute_sync(
            user_input=payload.message.user_input,
            model_name=model_name,
            provider=provider,
            endpoint=endpoint,
            max_tokens=max_tokens,
        )
        return summary.to_dict()
