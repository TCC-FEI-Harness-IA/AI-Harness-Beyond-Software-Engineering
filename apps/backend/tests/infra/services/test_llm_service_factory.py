from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.services.llm_service_factory import LLMServiceFactory
from src.infra.services.openrouter_service import OpenRouterService
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.security_doubles import authorization_for


def test_hospedado_cria_apenas_a_openrouter_com_a_credencial_da_execucao() -> None:
    autorizacao = authorization_for()

    servicos = LLMServiceFactory(settings=FakeSettings()).create_all(authorization=autorizacao)

    assert len(servicos) == 1
    assert isinstance(servicos[0], OpenRouterService)
    assert servicos[0].provider is ModelProviderEnum.OPEN_ROUTER
    assert servicos[0].authorization is autorizacao


def test_sem_autorizacao_a_openrouter_fica_sem_credencial() -> None:
    servico = LLMServiceFactory(settings=FakeSettings()).create_all(authorization=None)[0]

    assert servico.verify_provider_settings() is False


def test_nomeia_o_logger_pelo_modulo() -> None:
    settings = FakeSettings()

    LLMServiceFactory(settings=settings).create_all(authorization=None)

    assert any("openrouter_service" in modulo for modulo in settings.logger_calls)
