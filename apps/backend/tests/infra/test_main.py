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
