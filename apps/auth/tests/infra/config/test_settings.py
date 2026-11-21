from pathlib import Path

import pytest

from src.infra.config.settings import Settings

_TOKEN = "t" * 40


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch) -> None:
    for chave in [
        "APP_ENV", "AUTH_INTERNAL_TOKEN", "AUTH_INTERNAL_TOKEN_FILE", "AUTH_COOKIE_SECURE", "PUBLIC_ORIGINS",
        "AUTH_ARGON2_TIME_COST", "AUTH_ARGON2_MEMORY_COST_KIB", "AUTH_ARGON2_PARALLELISM", "AUTH_SESSION_TTL_SECONDS",
        "AUTH_LOGIN_MAX_ATTEMPTS", "AUTH_TRUST_PROXY_HEADERS", "AUTH_MONGODB_URI", "LOG_LEVEL",
    ]:
        monkeypatch.delenv(chave, raising=False)


def test_padroes_de_desenvolvimento(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN", _TOKEN)

    settings = Settings()

    assert settings.is_production is False
    assert settings.session_ttl_seconds == 86400
    assert settings.cookie_secure is False
    assert settings.session_cookie_name == "ralph_session"
    assert settings.credential_cookie_name == "ralph_llm_credential"
    assert settings.internal_token == _TOKEN
    assert settings.mongodb_database == "tcc_auth"
    assert settings.argon2_memory_cost_kib == 65536
    assert settings.login_max_attempts == 5
    assert settings.login_window_seconds == 900
    assert settings.trust_proxy_headers is False
    assert settings.password_min_length == 12
    assert settings.public_origins == ["http://localhost:5173"]


def test_segredo_pode_vir_de_arquivo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    arquivo = tmp_path / "internal_token"
    arquivo.write_text(_TOKEN + "\n", encoding="utf-8")
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN_FILE", str(arquivo))

    assert Settings().internal_token == _TOKEN


def test_segredo_interno_ausente_ou_curto_falha_com_mensagem_clara(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="AUTH_INTERNAL_TOKEN"):
        Settings()
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN", "curto")
    with pytest.raises(ValueError, match="32"):
        Settings()


def test_arquivo_de_segredo_inexistente_falha(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN_FILE", str(tmp_path / "nao-existe"))
    with pytest.raises(ValueError, match="AUTH_INTERNAL_TOKEN_FILE"):
        Settings()


def test_producao_com_configuracao_segura(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN", _TOKEN)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("PUBLIC_ORIGINS", "https://ralph.exemplo.com")
    monkeypatch.setenv("AUTH_TRUST_PROXY_HEADERS", "true")

    settings = Settings()

    assert settings.is_production is True
    assert settings.session_cookie_name == "__Host-ralph_session"
    assert settings.credential_cookie_name == "__Secure-ralph_llm_credential"
    assert settings.trust_proxy_headers is True


@pytest.mark.parametrize(
    ("variavel", "valor", "mensagem"),
    [
        ("AUTH_COOKIE_SECURE", "false", "AUTH_COOKIE_SECURE"),
        ("PUBLIC_ORIGINS", "http://ralph.exemplo.com", "https"),
        ("AUTH_ARGON2_MEMORY_COST_KIB", "1024", "OWASP"),
        ("AUTH_SESSION_TTL_SECONDS", "999999", "24"),
    ],
)
def test_producao_recusa_excecoes_de_desenvolvimento(
    monkeypatch: pytest.MonkeyPatch, variavel: str, valor: str, mensagem: str
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN", _TOKEN)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("PUBLIC_ORIGINS", "https://ralph.exemplo.com")
    monkeypatch.setenv(variavel, valor)

    with pytest.raises(ValueError, match=mensagem):
        Settings()


@pytest.mark.parametrize(
    ("variavel", "valor"),
    [("APP_ENV", "staging"), ("AUTH_COOKIE_SECURE", "talvez"), ("AUTH_LOGIN_MAX_ATTEMPTS", "abc"),
     ("AUTH_LOGIN_MAX_ATTEMPTS", "0")],
)
def test_valores_invalidos_falham(monkeypatch: pytest.MonkeyPatch, variavel: str, valor: str) -> None:
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN", _TOKEN)
    monkeypatch.setenv(variavel, valor)
    with pytest.raises(ValueError, match=variavel):
        Settings()


def test_logger_redige_segredos(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN", _TOKEN)
    logger = Settings().logger("teste_redacao")

    with caplog.at_level("INFO", logger="teste_redacao"):
        logger.info("Authorization: Bearer %s cookie=ralph_session=abc123; senha", _TOKEN)

    assert _TOKEN not in caplog.text
    assert "abc123" not in caplog.text
    assert "[REDACTED]" in caplog.text
