import logging
from typing import Any

from src.domain.interfaces.settings_interface import ISettings

_DEFAULTS: dict[str, Any] = {
    "app_title": "TCC API",
    "app_version": "0.1.0",
    "log_level": "INFO",
    "cors_allowed_origins": ["http://localhost:5173"],
    "openrouter_api_url": "https://openrouter.test/chat/completions",
    "openrouter_api_key": "chave-de-teste",
    "openrouter_model": "vendor/modelo-padrao",
    "openrouter_max_tokens": 1024,
    "openrouter_temperature": 0.7,
    "openrouter_http_referer": "",
    "openrouter_x_title": "",
    "openrouter_timeout_seconds": 30.0,
    "openrouter_reasoning_effort": "",
    "genai_available_models": ["vendor/modelo-padrao"],
    "genai_available_providers": ["open_router"],
    "ralph_sessions_storage_path": "./data/sessions",
    "ralph_session_flush_every_message": True,
    "ralph_session_id_prefix": "sess",
    "ralph_max_task_attempts": 3,
    "ralph_max_additional_planning_rounds": 2,
    "ralph_max_tasks_per_session": 12,
    "ralph_max_llm_calls_per_session": 60,
    "ralph_session_token_budget": 120000,
    "ralph_final_answer_token_reserve": 4000,
    "ralph_session_timeout_seconds": 600,
    "ralph_prompt_templates_path": "src/infra/templates",
    "ralph_json_parse_max_retries": 2,
    "ralph_websocket_max_message_bytes": 1048576,
}


class FakeSettings(ISettings):
    """Dublê de `ISettings` com valores em memória, sobrescrevíveis por caso de teste."""

    def __init__(self, **overrides: Any) -> None:
        """Monta as configurações a partir dos defaults, aplicando as sobrescritas.

        Args:
            **overrides: Valores que substituem os defaults, pelo nome da propriedade.
        """
        desconhecidas = set(overrides) - set(_DEFAULTS)
        if desconhecidas:
            raise ValueError(f"Propriedades inexistentes em ISettings: {sorted(desconhecidas)}")

        self.values: dict[str, Any] = {**_DEFAULTS, **overrides}
        self.logger_calls: list[str] = []

    @property
    def app_title(self) -> str:
        return self.values["app_title"]

    @property
    def app_version(self) -> str:
        return self.values["app_version"]

    @property
    def log_level(self) -> str:
        return self.values["log_level"]

    @property
    def cors_allowed_origins(self) -> list[str]:
        return self.values["cors_allowed_origins"]

    @property
    def openrouter_api_url(self) -> str:
        return self.values["openrouter_api_url"]

    @property
    def openrouter_api_key(self) -> str:
        return self.values["openrouter_api_key"]

    @property
    def openrouter_model(self) -> str:
        return self.values["openrouter_model"]

    @property
    def openrouter_max_tokens(self) -> int:
        return self.values["openrouter_max_tokens"]

    @property
    def openrouter_temperature(self) -> float:
        return self.values["openrouter_temperature"]

    @property
    def openrouter_http_referer(self) -> str:
        return self.values["openrouter_http_referer"]

    @property
    def openrouter_x_title(self) -> str:
        return self.values["openrouter_x_title"]

    @property
    def openrouter_timeout_seconds(self) -> float:
        return self.values["openrouter_timeout_seconds"]

    @property
    def openrouter_reasoning_effort(self) -> str:
        return self.values["openrouter_reasoning_effort"]

    @property
    def genai_available_models(self) -> list[str]:
        return self.values["genai_available_models"]

    @property
    def genai_available_providers(self) -> list[str]:
        return self.values["genai_available_providers"]

    @property
    def ralph_sessions_storage_path(self) -> str:
        return self.values["ralph_sessions_storage_path"]

    @property
    def ralph_session_flush_every_message(self) -> bool:
        return self.values["ralph_session_flush_every_message"]

    @property
    def ralph_session_id_prefix(self) -> str:
        return self.values["ralph_session_id_prefix"]

    @property
    def ralph_max_task_attempts(self) -> int:
        return self.values["ralph_max_task_attempts"]

    @property
    def ralph_max_additional_planning_rounds(self) -> int:
        return self.values["ralph_max_additional_planning_rounds"]

    @property
    def ralph_max_tasks_per_session(self) -> int:
        return self.values["ralph_max_tasks_per_session"]

    @property
    def ralph_max_llm_calls_per_session(self) -> int:
        return self.values["ralph_max_llm_calls_per_session"]

    @property
    def ralph_session_token_budget(self) -> int:
        return self.values["ralph_session_token_budget"]

    @property
    def ralph_final_answer_token_reserve(self) -> int:
        return self.values["ralph_final_answer_token_reserve"]

    @property
    def ralph_session_timeout_seconds(self) -> int:
        return self.values["ralph_session_timeout_seconds"]

    @property
    def ralph_prompt_templates_path(self) -> str:
        return self.values["ralph_prompt_templates_path"]

    @property
    def ralph_json_parse_max_retries(self) -> int:
        return self.values["ralph_json_parse_max_retries"]

    @property
    def ralph_websocket_max_message_bytes(self) -> int:
        return self.values["ralph_websocket_max_message_bytes"]

    def logger(self, module_file: str) -> logging.Logger:
        """Registra a chamada e devolve um logger inerte nomeado pelo módulo."""
        self.logger_calls.append(module_file)
        return logging.getLogger(f"fake.{module_file}")
