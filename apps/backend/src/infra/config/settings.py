import json
import logging
import os
from pathlib import Path

from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum
from src.domain.interfaces.settings_interface import ISettings

_TRUTHY_VALUES = frozenset({"true", "1", "yes", "y", "on"})
_FALSY_VALUES = frozenset({"false", "0", "no", "n", "off"})
_REASONING_EFFORTS = frozenset({"minimal", "low", "medium", "high"})
_SRC_PACKAGE_NAME = "src"


class Settings(ISettings):
    """Mapeia todas as variáveis de ambiente da aplicação como propriedades tipadas.

    As variáveis são lidas do ambiente uma única vez, na construção. Cada propriedade
    faz a conversão de tipo no acesso e levanta `ValueError` quando o valor configurado
    é inválido, de forma que o erro aponte diretamente para a variável responsável.
    """

    def __init__(self) -> None:
        """Carrega o mapa de variáveis de ambiente e prepara o estado de logging."""
        self.__logs_configured = False
        self.__vars_env = self.__load_vars_env()

    # ── Carga ────────────────────────────────────────────────────────────────

    def __load_vars_env(self) -> dict[str, str]:
        """Lê do ambiente todas as variáveis suportadas, aplicando os defaults.

        Returns:
            dict[str, str]: Mapa de variável para valor bruto, com chaves em maiúsculas.
        """
        return {
            "APP_TITLE": os.getenv("APP_TITLE", "TCC API"),
            "APP_VERSION": os.getenv("APP_VERSION", "0.1.0"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            "CORS_ALLOWED_ORIGINS": os.getenv(
                "CORS_ALLOWED_ORIGINS",
                "http://localhost:5173,http://localhost:3000",
            ),
            "LLM_PROVIDER": os.getenv("LLM_PROVIDER", ModelProviderEnum.OPEN_ROUTER.value),
            "LLM_MODEL": os.getenv("LLM_MODEL", ""),
            "LLM_MAX_TOKENS": os.getenv("LLM_MAX_TOKENS", "1024"),
            "LLM_TEMPERATURE": os.getenv("LLM_TEMPERATURE", "0.7"),
            "LLM_TIMEOUT_SECONDS": os.getenv("LLM_TIMEOUT_SECONDS", "30"),
            "LLM_REASONING_EFFORT": os.getenv("LLM_REASONING_EFFORT", ""),
            "OPENROUTER_API_URL": os.getenv(
                "OPENROUTER_API_URL",
                "https://openrouter.ai/api/v1/chat/completions",
            ),
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
            "OPENROUTER_HTTP_REFERER": os.getenv("OPENROUTER_HTTP_REFERER", ""),
            "OPENROUTER_X_TITLE": os.getenv("OPENROUTER_X_TITLE", ""),
            "OPENAI_API_URL": os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "OPENAI_ORGANIZATION": os.getenv("OPENAI_ORGANIZATION", ""),
            "AZURE_AI_FOUNDRY_ENDPOINT": os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", ""),
            "AZURE_AI_FOUNDRY_API_KEY": os.getenv("AZURE_AI_FOUNDRY_API_KEY", ""),
            "AZURE_AI_FOUNDRY_API_VERSION": os.getenv("AZURE_AI_FOUNDRY_API_VERSION", "2024-10-21"),
            "AZURE_AI_FOUNDRY_DEPLOYMENT": os.getenv("AZURE_AI_FOUNDRY_DEPLOYMENT", ""),
            "GENAI_AVAILABLE_MODELS": os.getenv("GENAI_AVAILABLE_MODELS", ""),
            "GENAI_AVAILABLE_PROVIDERS": os.getenv("GENAI_AVAILABLE_PROVIDERS", ""),
            "RALPH_SESSION_STORAGE_BACKEND": os.getenv(
                "RALPH_SESSION_STORAGE_BACKEND", SessionStorageBackendEnum.JSON_FILE.value
            ),
            "RALPH_SESSIONS_STORAGE_PATH": os.getenv("RALPH_SESSIONS_STORAGE_PATH", "./data/sessions"),
            "MONGODB_URI": os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
            "MONGODB_DATABASE": os.getenv("MONGODB_DATABASE", "tcc"),
            "MONGODB_SESSIONS_COLLECTION": os.getenv("MONGODB_SESSIONS_COLLECTION", "sessions"),
            "RALPH_SESSION_FLUSH_EVERY_MESSAGE": os.getenv("RALPH_SESSION_FLUSH_EVERY_MESSAGE", "true"),
            "RALPH_SESSION_ID_PREFIX": os.getenv("RALPH_SESSION_ID_PREFIX", "sess"),
            "RALPH_MAX_TASK_ATTEMPTS": os.getenv("RALPH_MAX_TASK_ATTEMPTS", "3"),
            "RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS": os.getenv("RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS", "2"),
            "RALPH_MAX_TASKS_PER_SESSION": os.getenv("RALPH_MAX_TASKS_PER_SESSION", "12"),
            "RALPH_MAX_LLM_CALLS_PER_SESSION": os.getenv("RALPH_MAX_LLM_CALLS_PER_SESSION", "60"),
            "RALPH_SESSION_TOKEN_BUDGET": os.getenv("RALPH_SESSION_TOKEN_BUDGET", "120000"),
            "RALPH_FINAL_ANSWER_TOKEN_RESERVE": os.getenv("RALPH_FINAL_ANSWER_TOKEN_RESERVE", "4000"),
            "RALPH_SESSION_TIMEOUT_SECONDS": os.getenv("RALPH_SESSION_TIMEOUT_SECONDS", "600"),
            "RALPH_PROMPT_TEMPLATES_PATH": os.getenv("RALPH_PROMPT_TEMPLATES_PATH", "src/infra/templates"),
            "RALPH_JSON_PARSE_MAX_RETRIES": os.getenv("RALPH_JSON_PARSE_MAX_RETRIES", "2"),
            "RALPH_WEBSOCKET_MAX_MESSAGE_BYTES": os.getenv("RALPH_WEBSOCKET_MAX_MESSAGE_BYTES", "1048576"),
        }

    # ── Conversores ──────────────────────────────────────────────────────────

    def __get_str(self, var_name: str) -> str:
        """Devolve o valor bruto de uma variável mapeada.

        Todas as chamadas partem das propriedades públicas desta classe, que só
        informam nomes declarados em `__load_vars_env`.

        Args:
            var_name: Nome da variável de ambiente mapeada.

        Returns:
            str: Valor bruto configurado para a variável.
        """
        return self.__vars_env[var_name]

    def __get_int(self, var_name: str) -> int:
        """Converte para inteiro o valor de uma variável mapeada.

        Raises:
            ValueError: Quando o valor configurado não é um inteiro.
        """
        raw_value = self.__get_str(var_name)
        try:
            return int(raw_value)
        except ValueError as exc:
            raise ValueError(f"Variável de ambiente '{var_name}' deve ser um inteiro. Valor: '{raw_value}'.") from exc

    def __get_float(self, var_name: str) -> float:
        """Converte para decimal o valor de uma variável mapeada.

        Raises:
            ValueError: Quando o valor configurado não é um número.
        """
        raw_value = self.__get_str(var_name)
        try:
            return float(raw_value)
        except ValueError as exc:
            raise ValueError(f"Variável de ambiente '{var_name}' deve ser um número. Valor: '{raw_value}'.") from exc

    def __get_bool(self, var_name: str) -> bool:
        """Converte para booleano o valor de uma variável mapeada.

        Raises:
            ValueError: Quando o valor configurado não representa um booleano.
        """
        raw_value = self.__get_str(var_name).strip().lower()
        if raw_value in _TRUTHY_VALUES:
            return True
        if raw_value in _FALSY_VALUES:
            return False
        raise ValueError(f"Variável de ambiente '{var_name}' deve ser um booleano. Valor: '{raw_value}'.")

    def __get_list(self, var_name: str) -> list[str]:
        """Converte para lista normalizada o valor de uma variável mapeada.

        Aceita JSON array (`["a", "b"]`) ou CSV (`a,b`). Os itens são normalizados
        para minúsculas e os vazios são descartados.
        """
        raw_value = self.__get_str(var_name).strip()
        if not raw_value:
            return []

        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, list):
            return [str(item).strip().lower() for item in parsed if str(item).strip()]

        return [item.strip().lower() for item in raw_value.split(",") if item.strip()]

    # ── Aplicação ────────────────────────────────────────────────────────────

    @property
    def app_title(self) -> str:
        """Título exposto pelo FastAPI."""
        return self.__get_str("APP_TITLE")

    @property
    def app_version(self) -> str:
        """Versão exposta pelo FastAPI."""
        return self.__get_str("APP_VERSION")

    @property
    def log_level(self) -> str:
        """Nível global de log."""
        return self.__get_str("LOG_LEVEL").strip().upper()

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Origens liberadas no middleware de CORS."""
        raw_value = self.__get_str("CORS_ALLOWED_ORIGINS").strip()
        if not raw_value:
            return []
        return [item.strip() for item in raw_value.split(",") if item.strip()]

    # ── LLM (comum a todos os provedores) ────────────────────────────────────

    @property
    def llm_provider(self) -> ModelProviderEnum:
        """Provedor usado quando a requisição não especifica um.

        Raises:
            ValueError: Quando o valor configurado não é um provedor implementado.
        """
        raw_value = self.__get_str("LLM_PROVIDER").strip().lower()
        try:
            return ModelProviderEnum(raw_value)
        except ValueError as exc:
            suportados = sorted(member.value for member in ModelProviderEnum)
            raise ValueError(
                f"Variável de ambiente 'LLM_PROVIDER' deve ser um de {suportados}. Valor: '{raw_value}'."
            ) from exc

    @property
    def llm_model(self) -> str:
        """Modelo padrão usado quando a requisição não especifica um."""
        return self.__get_str("LLM_MODEL").strip()

    @property
    def llm_max_tokens(self) -> int:
        """Teto padrão de tokens de saída."""
        return self.__get_int("LLM_MAX_TOKENS")

    @property
    def llm_temperature(self) -> float:
        """Temperatura padrão de geração."""
        return self.__get_float("LLM_TEMPERATURE")

    @property
    def llm_timeout_seconds(self) -> float:
        """Timeout, em segundos, das chamadas HTTP a qualquer provedor."""
        return self.__get_float("LLM_TIMEOUT_SECONDS")

    @property
    def llm_reasoning_effort(self) -> str:
        """Esforço de raciocínio pedido ao modelo. Vazio quando não configurado.

        Raises:
            ValueError: Quando o valor configurado não é um esforço conhecido.
        """
        raw_value = self.__get_str("LLM_REASONING_EFFORT").strip().lower()
        if not raw_value:
            return ""
        if raw_value not in _REASONING_EFFORTS:
            raise ValueError(
                f"Variável de ambiente 'LLM_REASONING_EFFORT' deve ser um de "
                f"{sorted(_REASONING_EFFORTS)}, ou vazia. Valor: '{raw_value}'."
            )
        return raw_value

    # ── OpenRouter ───────────────────────────────────────────────────────────

    @property
    def openrouter_api_url(self) -> str:
        """Endpoint de chat completions da OpenRouter."""
        return self.__get_str("OPENROUTER_API_URL")

    @property
    def openrouter_api_key(self) -> str:
        """Chave de API da OpenRouter."""
        return self.__get_str("OPENROUTER_API_KEY").strip()

    @property
    def openrouter_http_referer(self) -> str:
        """Valor do header `HTTP-Referer`. Vazio quando não configurado."""
        return self.__get_str("OPENROUTER_HTTP_REFERER").strip()

    @property
    def openrouter_x_title(self) -> str:
        """Valor do header `X-Title`. Vazio quando não configurado."""
        return self.__get_str("OPENROUTER_X_TITLE").strip()

    # ── OpenAI ───────────────────────────────────────────────────────────────

    @property
    def openai_api_url(self) -> str:
        """Endpoint de chat completions da OpenAI."""
        return self.__get_str("OPENAI_API_URL")

    @property
    def openai_api_key(self) -> str:
        """Chave de API da OpenAI."""
        return self.__get_str("OPENAI_API_KEY").strip()

    @property
    def openai_organization(self) -> str:
        """Valor do header `OpenAI-Organization`. Vazio quando não configurado."""
        return self.__get_str("OPENAI_ORGANIZATION").strip()

    # ── Azure AI Foundry ─────────────────────────────────────────────────────

    @property
    def azure_ai_foundry_endpoint(self) -> str:
        """Origem do recurso no Azure AI Foundry, sem barra final.

        A barra é removida aqui porque a URL da chamada é montada concatenando o
        caminho do deployment — mantê-la produziria `//openai/deployments/...`.
        """
        return self.__get_str("AZURE_AI_FOUNDRY_ENDPOINT").strip().rstrip("/")

    @property
    def azure_ai_foundry_api_key(self) -> str:
        """Chave de API do recurso no Azure AI Foundry."""
        return self.__get_str("AZURE_AI_FOUNDRY_API_KEY").strip()

    @property
    def azure_ai_foundry_api_version(self) -> str:
        """Versão da API de chat completions passada na query string."""
        return self.__get_str("AZURE_AI_FOUNDRY_API_VERSION").strip()

    @property
    def azure_ai_foundry_deployment(self) -> str:
        """Nome do deployment. Vazio quando o nome do modelo já é o do deployment."""
        return self.__get_str("AZURE_AI_FOUNDRY_DEPLOYMENT").strip()

    # ── Catálogo GenAI ───────────────────────────────────────────────────────

    @property
    def genai_available_models(self) -> list[str]:
        """Allowlist normalizada de modelos permitidos."""
        return self.__get_list("GENAI_AVAILABLE_MODELS")

    @property
    def genai_available_providers(self) -> list[str]:
        """Allowlist normalizada de provedores permitidos."""
        return self.__get_list("GENAI_AVAILABLE_PROVIDERS")

    # ── Sessão e persistência ────────────────────────────────────────────────

    @property
    def ralph_session_storage_backend(self) -> SessionStorageBackendEnum:
        """Backend usado para persistir sessões: `json_file` ou `mongodb`.

        Raises:
            ValueError: Quando o valor configurado não é um backend implementado.
        """
        raw_value = self.__get_str("RALPH_SESSION_STORAGE_BACKEND").strip().lower()
        try:
            return SessionStorageBackendEnum(raw_value)
        except ValueError as exc:
            suportados = sorted(member.value for member in SessionStorageBackendEnum)
            raise ValueError(
                f"Variável de ambiente 'RALPH_SESSION_STORAGE_BACKEND' deve ser um de "
                f"{suportados}. Valor: '{raw_value}'."
            ) from exc

    @property
    def ralph_sessions_storage_path(self) -> str:
        """Diretório onde os JSON de sessão são gravados, quando o backend é `json_file`."""
        return self.__get_str("RALPH_SESSIONS_STORAGE_PATH")

    @property
    def mongodb_uri(self) -> str:
        """URI de conexão do MongoDB, quando o backend é `mongodb`."""
        return self.__get_str("MONGODB_URI").strip()

    @property
    def mongodb_database(self) -> str:
        """Nome do banco de dados usado no MongoDB."""
        return self.__get_str("MONGODB_DATABASE").strip()

    @property
    def mongodb_sessions_collection(self) -> str:
        """Nome da coleção que guarda os documentos de sessão no MongoDB."""
        return self.__get_str("MONGODB_SESSIONS_COLLECTION").strip()

    @property
    def ralph_session_flush_every_message(self) -> bool:
        """Persiste a sessão a cada mensagem registrada."""
        return self.__get_bool("RALPH_SESSION_FLUSH_EVERY_MESSAGE")

    @property
    def ralph_session_id_prefix(self) -> str:
        """Prefixo dos identificadores de sessão."""
        return self.__get_str("RALPH_SESSION_ID_PREFIX").strip()

    # ── Resiliência de custo ─────────────────────────────────────────────────

    @property
    def ralph_max_task_attempts(self) -> int:
        """Tentativas máximas de B.1/B.2 para a mesma tarefa."""
        return self.__get_int("RALPH_MAX_TASK_ATTEMPTS")

    @property
    def ralph_max_additional_planning_rounds(self) -> int:
        """Execuções máximas de C.2 por sessão."""
        return self.__get_int("RALPH_MAX_ADDITIONAL_PLANNING_ROUNDS")

    @property
    def ralph_max_tasks_per_session(self) -> int:
        """Total máximo de tarefas somando A.2 e todas as rodadas de C.2."""
        return self.__get_int("RALPH_MAX_TASKS_PER_SESSION")

    @property
    def ralph_max_llm_calls_per_session(self) -> int:
        """Teto absoluto de chamadas ao modelo por sessão."""
        return self.__get_int("RALPH_MAX_LLM_CALLS_PER_SESSION")

    @property
    def ralph_session_token_budget(self) -> int:
        """Teto de tokens (entrada + saída) da sessão inteira."""
        return self.__get_int("RALPH_SESSION_TOKEN_BUDGET")

    @property
    def ralph_final_answer_token_reserve(self) -> int:
        """Reserva de tokens que o loop não consome, deixada para C.3 em regime de melhor esforço."""
        return self.__get_int("RALPH_FINAL_ANSWER_TOKEN_RESERVE")

    @property
    def ralph_session_timeout_seconds(self) -> int:
        """Tempo máximo de parede da sessão."""
        return self.__get_int("RALPH_SESSION_TIMEOUT_SECONDS")

    # ── Fluxo de thinking ────────────────────────────────────────────────────

    @property
    def ralph_prompt_templates_path(self) -> str:
        """Diretório dos templates de prompt em markdown."""
        return self.__get_str("RALPH_PROMPT_TEMPLATES_PATH")

    @property
    def ralph_json_parse_max_retries(self) -> int:
        """Retentativas quando o modelo devolve JSON inválido."""
        return self.__get_int("RALPH_JSON_PARSE_MAX_RETRIES")

    # ── Transporte ───────────────────────────────────────────────────────────

    @property
    def ralph_websocket_max_message_bytes(self) -> int:
        """Tamanho máximo, em bytes, do frame recebido no WebSocket."""
        return self.__get_int("RALPH_WEBSOCKET_MAX_MESSAGE_BYTES")

    # ── Utilitários ──────────────────────────────────────────────────────────

    def logger(self, module_file: str) -> logging.Logger:
        """Devolve um logger nomeado pelo caminho relativo do módulo.

        Args:
            module_file: Caminho absoluto do arquivo do módulo chamador.

        Returns:
            logging.Logger: Logger configurado para o módulo.
        """
        if not self.__logs_configured:
            logging.basicConfig(
                level=self.log_level,
                format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            )
            self.__logs_configured = True

        return logging.getLogger(self.__get_relative_module_path(module_file=module_file))

    def __get_relative_module_path(self, module_file: str) -> str:
        """Converte o caminho de um módulo no seu caminho relativo a partir de `src/`."""
        module_path = Path(module_file).resolve()

        if _SRC_PACKAGE_NAME in module_path.parts:
            src_index = module_path.parts.index(_SRC_PACKAGE_NAME)
            return Path(*module_path.parts[src_index:]).as_posix()

        return module_path.name
