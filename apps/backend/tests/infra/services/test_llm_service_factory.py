from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.services.azure_ai_foundry_service import AzureAIFoundryService
from src.infra.services.llm_service_factory import LLMServiceFactory
from src.infra.services.openai_service import OpenAIService
from src.infra.services.openrouter_service import OpenRouterService
from tests.doubles.fake_settings import FakeSettings


def _build_factory(**settings_overrides: object) -> LLMServiceFactory:
    return LLMServiceFactory(settings=FakeSettings(**settings_overrides))


def test_cria_um_servico_para_cada_provedor_implementado() -> None:
    servicos = _build_factory().create_all()

    assert {servico.provider for servico in servicos} == set(ModelProviderEnum)


def test_cada_servico_e_a_implementacao_do_seu_provedor() -> None:
    por_provedor = {servico.provider: servico for servico in _build_factory().create_all()}

    assert isinstance(por_provedor[ModelProviderEnum.OPEN_ROUTER], OpenRouterService)
    assert isinstance(por_provedor[ModelProviderEnum.OPENAI], OpenAIService)
    assert isinstance(por_provedor[ModelProviderEnum.AZURE_AI_FOUNDRY], AzureAIFoundryService)


def test_nomeia_o_logger_de_cada_servico_pelo_seu_modulo() -> None:
    settings = FakeSettings()

    LLMServiceFactory(settings=settings).create_all()

    modulos = [chamada for chamada in settings.logger_calls]
    assert any("openrouter_service" in modulo for modulo in modulos)
    assert any("openai_service" in modulo for modulo in modulos)
    assert any("azure_ai_foundry_service" in modulo for modulo in modulos)
