import pytest
from fastapi.middleware.cors import CORSMiddleware

from src.main import create_app


def test_titulo_e_versao_vem_das_configuracoes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_TITLE", "API do TCC")
    monkeypatch.setenv("APP_VERSION", "9.9.9")

    app = create_app()

    assert app.title == "API do TCC"
    assert app.version == "9.9.9"


def test_origens_de_cors_vem_das_configuracoes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.test,https://outro.test")

    app = create_app()

    middlewares = [item for item in app.user_middleware if item.cls is CORSMiddleware]
    assert middlewares[0].kwargs["allow_origins"] == ["https://app.test", "https://outro.test"]


def test_registra_o_roteador_da_v1() -> None:
    caminhos = {route.path for route in create_app().routes}

    assert "/v1/health" in caminhos
    assert "/v1/message/default" in caminhos


def test_producao_monta_sempre_os_servicos_reais_de_seguranca() -> None:
    from src.infra.security.auth_service_identity_provider import AuthServiceIdentityProvider
    from src.infra.security.openrouter_key_validator import OpenRouterKeyValidator

    seguranca = create_app().state.security

    assert isinstance(seguranca.identity_provider, AuthServiceIdentityProvider)
    assert isinstance(seguranca.key_validator, OpenRouterKeyValidator)


def test_sem_chave_de_criptografia_a_aplicacao_nao_sobe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_CREDENTIAL_ENCRYPTION_KEY")

    with pytest.raises(ValueError, match="LLM_CREDENTIAL_ENCRYPTION_KEY"):
        create_app()


def test_politica_de_cache_separa_publico_de_privado() -> None:
    from fastapi.testclient import TestClient

    from tests.doubles.security_doubles import build_security

    client = TestClient(create_app(security=build_security()))

    privado = client.get("/v1/health")

    assert privado.headers["cache-control"] == "no-store, private"
    assert privado.headers["vary"] == "Cookie"
