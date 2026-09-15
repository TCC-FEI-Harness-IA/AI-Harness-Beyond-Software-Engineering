import logging
from typing import Any

import pytest

from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum
from src.infra.config.settings import Settings

_ENV_VARS = (
    "APP_TITLE",
    "APP_VERSION",
    "LOG_LEVEL",
    "CORS_ALLOWED_ORIGINS",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "LLM_MAX_TOKENS",
    "LLM_TEMPERATURE",
    "LLM_TIMEOUT_SECONDS",
    "LLM_REASONING_EFFORT",
    "OPENROUTER_API_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_HTTP_REFERER",
    "OPENROUTER_X_TITLE",
    "OPENAI_API_URL",
    "OPENAI_API_KEY",
    "OPENAI_ORGANIZATION",
    "AZURE_AI_FOUNDRY_ENDPOINT",
    "AZURE_AI_FOUNDRY_API_KEY",
    "AZURE_AI_FOUNDRY_API_VERSION",
    "AZURE_AI_FOUNDRY_DEPLOYMENT",
    "GENAI_AVAILABLE_MODELS",
    "GENAI_AVAILABLE_PROVIDERS",
    "RALPH_SESSION_STORAGE_BACKEND",
    "RALPH_SESSIONS_STORAGE_PATH",
    "MONGODB_URI",
    "MONGODB_DATABASE",
    "MONGODB_SESSIONS_COLLECTION",
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
    assert settings.llm_provider is ModelProviderEnum.OPEN_ROUTER
    assert settings.llm_model == ""
    assert settings.llm_max_tokens == 1024
    assert settings.llm_temperature == 0.7
    assert settings.llm_timeout_seconds == 30.0
    assert settings.llm_reasoning_effort == ""
    assert settings.openrouter_api_url == "https://openrouter.ai/api/v1/chat/completions"
    assert settings.openrouter_api_key == ""
    assert settings.openrouter_http_referer == ""
    assert settings.openrouter_x_title == ""
    assert settings.openai_api_url == "https://api.openai.com/v1/chat/completions"
    assert settings.openai_api_key == ""
    assert settings.openai_organization == ""
    assert settings.azure_ai_foundry_endpoint == ""
    assert settings.azure_ai_foundry_api_key == ""
    assert settings.azure_ai_foundry_api_version == "2024-10-21"
    assert settings.azure_ai_foundry_deployment == ""
    assert settings.genai_available_models == []
    assert settings.genai_available_providers == []
    assert settings.ralph_session_storage_backend is SessionStorageBackendEnum.JSON_FILE
    assert settings.ralph_sessions_storage_path == "./data/sessions"
    assert settings.mongodb_uri == "mongodb://localhost:27017"
    assert settings.mongodb_database == "tcc"
    assert settings.mongodb_sessions_collection == "sessions"
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


# ── Configuração comum a todos os provedores ─────────────────────────────────

def test_le_do_ambiente_as_variaveis_unificadas_de_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "  vendor/modelo  ")
    monkeypatch.setenv("LLM_MAX_TOKENS", "2048")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("LLM_REASONING_EFFORT", "  LOW  ")

    settings = Settings()

    assert settings.llm_model == "vendor/modelo"
    assert settings.llm_max_tokens == 2048
    assert settings.llm_temperature == 0.2
    assert settings.llm_timeout_seconds == 45.0
    assert settings.llm_reasoning_effort == "low"


@pytest.mark.parametrize("provider", list(ModelProviderEnum))
def test_aceita_todos_os_provedores_implementados(
    monkeypatch: pytest.MonkeyPatch, provider: ModelProviderEnum
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", f"  {provider.value.upper()}  ")

    assert Settings().llm_provider is provider


def test_provedor_desconhecido_levanta_erro_citando_a_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "provedor_inexistente")

    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        _ = Settings().llm_provider


@pytest.mark.parametrize("raw_value", ["minimal", "low", "medium", "high"])
def test_aceita_todos_os_esforcos_de_raciocinio(monkeypatch: pytest.MonkeyPatch, raw_value: str) -> None:
    monkeypatch.setenv("LLM_REASONING_EFFORT", raw_value)

    assert Settings().llm_reasoning_effort == raw_value


def test_esforco_de_raciocinio_desconhecido_levanta_erro_citando_a_variavel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_REASONING_EFFORT", "altissimo")

    with pytest.raises(ValueError, match="LLM_REASONING_EFFORT"):
        _ = Settings().llm_reasoning_effort


# ── Configuração específica de cada provedor ─────────────────────────────────

def test_le_do_ambiente_as_variaveis_de_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_URL", "https://exemplo.test/chat")
    monkeypatch.setenv("OPENROUTER_API_KEY", "  chave-secreta  ")
    monkeypatch.setenv("OPENROUTER_HTTP_REFERER", "  https://referer.test  ")
    monkeypatch.setenv("OPENROUTER_X_TITLE", "  Titulo  ")

    settings = Settings()

    assert settings.openrouter_api_url == "https://exemplo.test/chat"
    assert settings.openrouter_api_key == "chave-secreta"
    assert settings.openrouter_http_referer == "https://referer.test"
    assert settings.openrouter_x_title == "Titulo"


def test_le_do_ambiente_as_variaveis_de_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_URL", "https://exemplo.test/v1/chat/completions")
    monkeypatch.setenv("OPENAI_API_KEY", "  sk-chave  ")
    monkeypatch.setenv("OPENAI_ORGANIZATION", "  org-123  ")

    settings = Settings()

    assert settings.openai_api_url == "https://exemplo.test/v1/chat/completions"
    assert settings.openai_api_key == "sk-chave"
    assert settings.openai_organization == "org-123"


def test_le_do_ambiente_as_variaveis_de_azure_ai_foundry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_AI_FOUNDRY_ENDPOINT", "  https://recurso.services.ai.azure.com/  ")
    monkeypatch.setenv("AZURE_AI_FOUNDRY_API_KEY", "  chave-azure  ")
    monkeypatch.setenv("AZURE_AI_FOUNDRY_API_VERSION", "  2025-01-01-preview  ")
    monkeypatch.setenv("AZURE_AI_FOUNDRY_DEPLOYMENT", "  meu-deployment  ")

    settings = Settings()

    assert settings.azure_ai_foundry_endpoint == "https://recurso.services.ai.azure.com"
    assert settings.azure_ai_foundry_api_key == "chave-azure"
    assert settings.azure_ai_foundry_api_version == "2025-01-01-preview"
    assert settings.azure_ai_foundry_deployment == "meu-deployment"


def test_endpoint_de_azure_perde_a_barra_final(monkeypatch: pytest.MonkeyPatch) -> None:
    """A URL é montada concatenando caminho; uma barra final produziria `//openai/...`."""
    monkeypatch.setenv("AZURE_AI_FOUNDRY_ENDPOINT", "https://recurso.services.ai.azure.com///")

    assert Settings().azure_ai_foundry_endpoint == "https://recurso.services.ai.azure.com"


def test_le_do_ambiente_as_variaveis_de_sessao_e_thinking(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", "/tmp/sessoes")
    monkeypatch.setenv("RALPH_SESSION_ID_PREFIX", "  run  ")
    monkeypatch.setenv("RALPH_PROMPT_TEMPLATES_PATH", "outro/caminho")

    settings = Settings()

    assert settings.ralph_sessions_storage_path == "/tmp/sessoes"
    assert settings.ralph_session_id_prefix == "run"
    assert settings.ralph_prompt_templates_path == "outro/caminho"


@pytest.mark.parametrize("backend", list(SessionStorageBackendEnum))
def test_aceita_todos_os_backends_de_sessao_implementados(
    monkeypatch: pytest.MonkeyPatch, backend: SessionStorageBackendEnum
) -> None:
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", f"  {backend.value.upper()}  ")

    assert Settings().ralph_session_storage_backend is backend


def test_backend_de_sessao_desconhecido_levanta_erro_citando_a_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "backend_inexistente")

    with pytest.raises(ValueError, match="RALPH_SESSION_STORAGE_BACKEND"):
        _ = Settings().ralph_session_storage_backend


def test_le_do_ambiente_as_variaveis_de_mongodb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MONGODB_URI", "  mongodb://mongo:27017  ")
    monkeypatch.setenv("MONGODB_DATABASE", "  banco_de_teste  ")
    monkeypatch.setenv("MONGODB_SESSIONS_COLLECTION", "  colecao_de_teste  ")

    settings = Settings()

    assert settings.mongodb_uri == "mongodb://mongo:27017"
    assert settings.mongodb_database == "banco_de_teste"
    assert settings.mongodb_sessions_collection == "colecao_de_teste"


def test_log_level_e_normalizado_para_maiusculas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "  debug  ")

    assert Settings().log_level == "DEBUG"


# ── Conversão para inteiro ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("var_name", "attribute"),
    [
        ("LLM_MAX_TOKENS", "llm_max_tokens"),
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
    monkeypatch.setenv("LLM_MAX_TOKENS", "abc")

    with pytest.raises(ValueError, match="LLM_MAX_TOKENS"):
        Settings().llm_max_tokens


# ── Conversão para decimal ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("var_name", "attribute"),
    [
        ("LLM_TEMPERATURE", "llm_temperature"),
        ("LLM_TIMEOUT_SECONDS", "llm_timeout_seconds"),
    ],
)
def test_converte_para_decimal(monkeypatch: pytest.MonkeyPatch, var_name: str, attribute: str) -> None:
    monkeypatch.setenv(var_name, "0.7")

    assert getattr(Settings(), attribute) == 0.7


def test_valor_nao_numerico_levanta_erro_citando_a_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_TEMPERATURE", "x")

    with pytest.raises(ValueError, match="LLM_TEMPERATURE"):
        Settings().llm_temperature


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
