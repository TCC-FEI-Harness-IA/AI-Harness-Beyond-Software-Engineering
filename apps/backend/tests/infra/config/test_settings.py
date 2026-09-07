import logging
from typing import Any

import pytest

from src.infra.config.settings import Settings

_ENV_VARS = (
    "APP_TITLE",
    "APP_VERSION",
    "LOG_LEVEL",
    "CORS_ALLOWED_ORIGINS",
    "OPENROUTER_API_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "OPENROUTER_MAX_TOKENS",
    "OPENROUTER_TEMPERATURE",
    "OPENROUTER_HTTP_REFERER",
    "OPENROUTER_X_TITLE",
    "OPENROUTER_TIMEOUT_SECONDS",
    "GENAI_AVAILABLE_MODELS",
    "GENAI_AVAILABLE_PROVIDERS",
    "RALPH_SESSIONS_STORAGE_PATH",
    "RALPH_SESSION_FLUSH_EVERY_MESSAGE",
    "RALPH_SESSION_ID_PREFIX",
    "RALPH_MAX_TASK_ATTEMPTS",
    "RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS",
    "RALPH_MAX_TASKS_PER_SESSION",
    "RALPH_MAX_LLM_CALLS_PER_SESSION",
    "RALPH_SESSION_TOKEN_BUDGET",
    "RALPH_FINAL_ANSWER_TOKEN_RESERVE",
    "RALPH_SESSION_TIMEOUT_SECONDS",
    "RALPH_PROMPT_TEMPLATES_PATH",
    "RALPH_JSON_PARSE_MAX_RETRIES",
    "RALPH_WEBSOCKET_MAX_MESSAGE_BYTES",
)


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove do ambiente todas as variáveis do sistema antes de cada caso."""
    for var_name in _ENV_VARS:
        monkeypatch.delenv(var_name, raising=False)


def test_le_valores_presentes_no_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_TITLE", "API do TCC")
    monkeypatch.setenv("APP_VERSION", "9.9.9")

    settings = Settings()

    assert settings.app_title == "API do TCC"
    assert settings.app_version == "9.9.9"


def test_aplica_os_defaults_documentados_quando_a_variavel_esta_ausente() -> None:
    settings = Settings()

    assert settings.app_title == "TCC API"
    assert settings.app_version == "0.1.0"
    assert settings.log_level == "INFO"
    assert settings.cors_allowed_origins == ["http://localhost:5173", "http://localhost:3000"]
    assert settings.openrouter_api_url == "https://openrouter.ai/api/v1/chat/completions"
    assert settings.openrouter_api_key == ""
    assert settings.openrouter_model == ""
    assert settings.openrouter_max_tokens == 1024
    assert settings.openrouter_temperature == 0.7
    assert settings.openrouter_http_referer == ""
    assert settings.openrouter_x_title == ""
    assert settings.openrouter_timeout_seconds == 30.0
    assert settings.genai_available_models == []
    assert settings.genai_available_providers == []
    assert settings.ralph_sessions_storage_path == "./data/sessions"
    assert settings.ralph_session_flush_every_message is True
    assert settings.ralph_session_id_prefix == "sess"
    assert settings.ralph_max_task_attempts == 3
    assert settings.ralph_max_additional_planning_rounds == 2
    assert settings.ralph_max_tasks_per_session == 12
    assert settings.ralph_max_llm_calls_per_session == 60
    assert settings.ralph_session_token_budget == 120000
    assert settings.ralph_final_answer_token_reserve == 4000
    assert settings.ralph_session_timeout_seconds == 600
    assert settings.ralph_prompt_templates_path == "src/infra/templates"
    assert settings.ralph_json_parse_max_retries == 2
    assert settings.ralph_websocket_max_message_bytes == 1048576


def test_le_do_ambiente_todas_as_variaveis_de_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_URL", "https://exemplo.test/chat")
    monkeypatch.setenv("OPENROUTER_API_KEY", "  chave-secreta  ")
    monkeypatch.setenv("OPENROUTER_MODEL", "  vendor/modelo  ")
    monkeypatch.setenv("OPENROUTER_HTTP_REFERER", "  https://referer.test  ")
    monkeypatch.setenv("OPENROUTER_X_TITLE", "  Titulo  ")

    settings = Settings()

    assert settings.openrouter_api_url == "https://exemplo.test/chat"
    assert settings.openrouter_api_key == "chave-secreta"
    assert settings.openrouter_model == "vendor/modelo"
    assert settings.openrouter_http_referer == "https://referer.test"
    assert settings.openrouter_x_title == "Titulo"


def test_le_do_ambiente_as_variaveis_de_sessao_e_thinking(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", "/tmp/sessoes")
    monkeypatch.setenv("RALPH_SESSION_ID_PREFIX", "  run  ")
    monkeypatch.setenv("RALPH_PROMPT_TEMPLATES_PATH", "outro/caminho")

    settings = Settings()

    assert settings.ralph_sessions_storage_path == "/tmp/sessoes"
    assert settings.ralph_session_id_prefix == "run"
    assert settings.ralph_prompt_templates_path == "outro/caminho"


def test_log_level_e_normalizado_para_maiusculas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "  debug  ")

    assert Settings().log_level == "DEBUG"


# ── Conversão para inteiro ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("var_name", "attribute"),
    [
        ("OPENROUTER_MAX_TOKENS", "openrouter_max_tokens"),
        ("RALPH_MAX_TASK_ATTEMPTS", "ralph_max_task_attempts"),
        ("RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS", "ralph_max_additional_planning_rounds"),
        ("RALPH_MAX_TASKS_PER_SESSION", "ralph_max_tasks_per_session"),
        ("RALPH_MAX_LLM_CALLS_PER_SESSION", "ralph_max_llm_calls_per_session"),
        ("RALPH_SESSION_TOKEN_BUDGET", "ralph_session_token_budget"),
        ("RALPH_FINAL_ANSWER_TOKEN_RESERVE", "ralph_final_answer_token_reserve"),
        ("RALPH_SESSION_TIMEOUT_SECONDS", "ralph_session_timeout_seconds"),
        ("RALPH_JSON_PARSE_MAX_RETRIES", "ralph_json_parse_max_retries"),
        ("RALPH_WEBSOCKET_MAX_MESSAGE_BYTES", "ralph_websocket_max_message_bytes"),
    ],
)
def test_converte_para_inteiro(monkeypatch: pytest.MonkeyPatch, var_name: str, attribute: str) -> None:
    monkeypatch.setenv(var_name, "42")

    assert getattr(Settings(), attribute) == 42


def test_valor_nao_inteiro_levanta_erro_citando_a_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_MAX_TOKENS", "abc")

    with pytest.raises(ValueError, match="OPENROUTER_MAX_TOKENS"):
        Settings().openrouter_max_tokens


# ── Conversão para decimal ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("var_name", "attribute"),
    [
        ("OPENROUTER_TEMPERATURE", "openrouter_temperature"),
        ("OPENROUTER_TIMEOUT_SECONDS", "openrouter_timeout_seconds"),
    ],
)
def test_converte_para_decimal(monkeypatch: pytest.MonkeyPatch, var_name: str, attribute: str) -> None:
    monkeypatch.setenv(var_name, "0.7")

    assert getattr(Settings(), attribute) == 0.7


def test_valor_nao_numerico_levanta_erro_citando_a_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_TEMPERATURE", "x")

    with pytest.raises(ValueError, match="OPENROUTER_TEMPERATURE"):
        Settings().openrouter_temperature


# ── Conversão para booleano ──────────────────────────────────────────────────

@pytest.mark.parametrize("raw_value", ["true", "TRUE", "1", "yes", "  Y  ", "on"])
def test_valores_verdadeiros(monkeypatch: pytest.MonkeyPatch, raw_value: str) -> None:
    monkeypatch.setenv("RALPH_SESSION_FLUSH_EVERY_MESSAGE", raw_value)

    assert Settings().ralph_session_flush_every_message is True


@pytest.mark.parametrize("raw_value", ["false", "FALSE", "0", "no", "  N  ", "off"])
def test_valores_falsos(monkeypatch: pytest.MonkeyPatch, raw_value: str) -> None:
    monkeypatch.setenv("RALPH_SESSION_FLUSH_EVERY_MESSAGE", raw_value)

    assert Settings().ralph_session_flush_every_message is False


def test_valor_nao_booleano_levanta_erro_citando_a_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RALPH_SESSION_FLUSH_EVERY_MESSAGE", "talvez")

    with pytest.raises(ValueError, match="RALPH_SESSION_FLUSH_EVERY_MESSAGE"):
        Settings().ralph_session_flush_every_message


# ── Conversão para lista ─────────────────────────────────────────────────────

def test_allowlist_em_json_array_e_normalizada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENAI_AVAILABLE_MODELS", '["a", "B", " ", "c "]')

    assert Settings().genai_available_models == ["a", "b", "c"]


def test_allowlist_em_csv_e_normalizada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENAI_AVAILABLE_PROVIDERS", "a, B ,,c")

    assert Settings().genai_available_providers == ["a", "b", "c"]


def test_allowlist_vazia_vira_lista_vazia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENAI_AVAILABLE_MODELS", "   ")

    assert Settings().genai_available_models == []


def test_allowlist_com_json_que_nao_e_array_cai_no_modo_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENAI_AVAILABLE_MODELS", '{"modelo": "x"}')

    assert Settings().genai_available_models == ['{"modelo": "x"}']


# ── Origens de CORS ──────────────────────────────────────────────────────────

def test_origens_de_cors_preservam_a_caixa_original(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://App.Test , http://localhost:3000 ,")

    assert Settings().cors_allowed_origins == ["https://App.Test", "http://localhost:3000"]


def test_origens_de_cors_vazias_viram_lista_vazia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "   ")

    assert Settings().cors_allowed_origins == []


# ── Logger ───────────────────────────────────────────────────────────────────

def test_logger_configura_o_logging_uma_unica_vez(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: chamadas.append(kwargs))

    settings = Settings()
    settings.logger(module_file=__file__)
    settings.logger(module_file=__file__)

    assert len(chamadas) == 1


def test_logger_usa_o_nivel_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: chamadas.append(kwargs))
    monkeypatch.setenv("LOG_LEVEL", "debug")

    Settings().logger(module_file=__file__)

    assert chamadas[0]["level"] == "DEBUG"


def test_logger_de_modulo_dentro_de_src_usa_o_caminho_relativo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: None)

    logger = Settings().logger(module_file="/qualquer/lugar/src/infra/config/settings.py")

    assert logger.name == "src/infra/config/settings.py"


def test_logger_de_modulo_fora_de_src_usa_apenas_o_nome_do_arquivo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: None)

    logger = Settings().logger(module_file="/fora/do/pacote/script.py")

    assert logger.name == "script.py"
