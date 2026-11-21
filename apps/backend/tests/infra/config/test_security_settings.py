import base64
import secrets
from pathlib import Path

import pytest

from src.infra.config.security_settings import SecuritySettings

_CHAVE = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
_INTERNO = "segredo-interno-de-teste-com-mais-de-32-caracteres"
_VARIAVEIS = [
    "APP_ENV", "AUTH_SERVICE_URL", "AUTH_INTERNAL_TOKEN", "AUTH_INTERNAL_TOKEN_FILE",
    "LLM_CREDENTIAL_ENCRYPTION_KEY", "LLM_CREDENTIAL_ENCRYPTION_KEY_FILE", "COOKIE_SECURE", "PUBLIC_ORIGINS",
    "OPENROUTER_KEY_VALIDATION_URL", "AUTH_REVALIDATION_INTERVAL_SECONDS", "RUN_MAX_CONCURRENT_PER_USER",
    "RUN_MAX_STARTS_PER_WINDOW", "RUN_STARTS_WINDOW_SECONDS",
]


@pytest.fixture
def ambiente(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for chave in _VARIAVEIS:
        monkeypatch.delenv(chave, raising=False)
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN", _INTERNO)
    monkeypatch.setenv("LLM_CREDENTIAL_ENCRYPTION_KEY", _CHAVE)
    return monkeypatch


def test_padroes_de_desenvolvimento(ambiente: pytest.MonkeyPatch) -> None:
    settings = SecuritySettings.from_env()

    assert settings.is_production is False
    assert settings.auth_service_url == "http://localhost:8001"
    assert settings.credential_encryption_key == base64.urlsafe_b64decode(_CHAVE)
    assert settings.cookie_secure is False
    assert settings.session_cookie_name == "ralph_session"
    assert settings.credential_cookie_name == "ralph_llm_credential"
    assert settings.public_origins == ("http://localhost:5173",)
    assert settings.key_validation_url == "https://openrouter.ai/api/v1/key"
    assert settings.revalidation_interval_seconds == 15
    assert settings.max_concurrent_runs_per_user == 2
    assert settings.max_run_starts_per_window == 30
    assert settings.run_starts_window_seconds == 3600
    assert _CHAVE not in repr(settings) and _INTERNO not in repr(settings)


def test_segredos_por_arquivo(ambiente: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "chave").write_text(_CHAVE + "\n")
    (tmp_path / "interno").write_text(_INTERNO + "\n")
    ambiente.delenv("LLM_CREDENTIAL_ENCRYPTION_KEY")
    ambiente.delenv("AUTH_INTERNAL_TOKEN")
    ambiente.setenv("LLM_CREDENTIAL_ENCRYPTION_KEY_FILE", str(tmp_path / "chave"))
    ambiente.setenv("AUTH_INTERNAL_TOKEN_FILE", str(tmp_path / "interno"))

    settings = SecuritySettings.from_env()

    assert settings.internal_token == _INTERNO
    assert len(settings.credential_encryption_key) == 32


@pytest.mark.parametrize(
    ("variavel", "valor", "mensagem"),
    [
        ("LLM_CREDENTIAL_ENCRYPTION_KEY", "", "LLM_CREDENTIAL_ENCRYPTION_KEY"),
        ("LLM_CREDENTIAL_ENCRYPTION_KEY", "nao-e-base64!!", "LLM_CREDENTIAL_ENCRYPTION_KEY"),
        ("LLM_CREDENTIAL_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"curta").decode(), "32 bytes"),
        ("AUTH_INTERNAL_TOKEN", "curto", "AUTH_INTERNAL_TOKEN"),
        ("APP_ENV", "staging", "APP_ENV"),
        ("COOKIE_SECURE", "talvez", "COOKIE_SECURE"),
        ("RUN_MAX_CONCURRENT_PER_USER", "0", "RUN_MAX_CONCURRENT_PER_USER"),
        ("AUTH_REVALIDATION_INTERVAL_SECONDS", "x", "AUTH_REVALIDATION_INTERVAL_SECONDS"),
    ],
)
def test_configuracao_invalida_falha_com_mensagem_clara(
    ambiente: pytest.MonkeyPatch, variavel: str, valor: str, mensagem: str
) -> None:
    ambiente.setenv(variavel, valor)

    with pytest.raises(ValueError, match=mensagem):
        SecuritySettings.from_env()


def test_arquivo_de_segredo_ilegivel(ambiente: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ambiente.setenv("LLM_CREDENTIAL_ENCRYPTION_KEY_FILE", str(tmp_path / "nao-existe"))

    with pytest.raises(ValueError, match="LLM_CREDENTIAL_ENCRYPTION_KEY_FILE"):
        SecuritySettings.from_env()


def test_producao_exige_cookie_seguro_e_origem_https(ambiente: pytest.MonkeyPatch) -> None:
    ambiente.setenv("APP_ENV", "production")
    ambiente.setenv("COOKIE_SECURE", "false")
    ambiente.setenv("PUBLIC_ORIGINS", "https://ralph.exemplo.com")
    with pytest.raises(ValueError, match="COOKIE_SECURE"):
        SecuritySettings.from_env()

    ambiente.setenv("COOKIE_SECURE", "true")
    ambiente.setenv("PUBLIC_ORIGINS", "http://ralph.exemplo.com")
    with pytest.raises(ValueError, match="https"):
        SecuritySettings.from_env()

    ambiente.setenv("PUBLIC_ORIGINS", "https://ralph.exemplo.com/")
    settings = SecuritySettings.from_env()
    assert settings.is_production is True
    assert settings.public_origins == ("https://ralph.exemplo.com",)
    assert settings.session_cookie_name == "__Host-ralph_session"
    assert settings.credential_cookie_name == "__Secure-ralph_llm_credential"


def test_valores_numericos_explicitos(ambiente: pytest.MonkeyPatch) -> None:
    ambiente.setenv("AUTH_REVALIDATION_INTERVAL_SECONDS", "5")
    ambiente.setenv("RUN_MAX_STARTS_PER_WINDOW", "7")

    settings = SecuritySettings.from_env()

    assert settings.revalidation_interval_seconds == 5
    assert settings.max_run_starts_per_window == 7


def test_chave_em_base64_padrao_com_mais_e_barra_e_recusada(ambiente: pytest.MonkeyPatch) -> None:
    ambiente.setenv("LLM_CREDENTIAL_ENCRYPTION_KEY", "+/" * 22)

    with pytest.raises(ValueError, match="base64url"):
        SecuritySettings.from_env()
