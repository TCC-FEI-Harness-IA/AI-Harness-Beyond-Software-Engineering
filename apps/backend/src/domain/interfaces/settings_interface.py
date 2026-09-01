import logging
from abc import ABC, abstractmethod


class ISettings(ABC):
    """Contrato de acesso às configurações da aplicação.

    Toda variável de ambiente do sistema é exposta como uma propriedade tipada.
    Nenhum consumidor lê `os.environ` diretamente nem converte tipos por conta própria.
    """

    # ── Aplicação ────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def app_title(self) -> str:
        """Título exposto pelo FastAPI."""
        raise NotImplementedError

    @property
    @abstractmethod
    def app_version(self) -> str:
        """Versão exposta pelo FastAPI."""
        raise NotImplementedError

    @property
    @abstractmethod
    def log_level(self) -> str:
        """Nível global de log."""
        raise NotImplementedError

    @property
    @abstractmethod
    def cors_allowed_origins(self) -> list[str]:
        """Origens liberadas no middleware de CORS."""
        raise NotImplementedError

    # ── OpenRouter ───────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def openrouter_api_url(self) -> str:
        """Endpoint de chat completions da OpenRouter."""
        raise NotImplementedError

    @property
    @abstractmethod
    def openrouter_api_key(self) -> str:
        """Chave de API da OpenRouter."""
        raise NotImplementedError

    @property
    @abstractmethod
    def openrouter_model(self) -> str:
        """Modelo padrão usado quando a requisição não especifica um."""
        raise NotImplementedError

    @property
    @abstractmethod
    def openrouter_max_tokens(self) -> int:
        """Teto padrão de tokens de saída."""
        raise NotImplementedError

    @property
    @abstractmethod
    def openrouter_temperature(self) -> float:
        """Temperatura padrão de geração."""
        raise NotImplementedError

    @property
    @abstractmethod
    def openrouter_http_referer(self) -> str:
        """Valor do header `HTTP-Referer`. Vazio quando não configurado."""
        raise NotImplementedError

    @property
    @abstractmethod
    def openrouter_x_title(self) -> str:
        """Valor do header `X-Title`. Vazio quando não configurado."""
        raise NotImplementedError

    @property
    @abstractmethod
    def openrouter_timeout_seconds(self) -> float:
        """Timeout, em segundos, das chamadas HTTP à OpenRouter."""
        raise NotImplementedError

    # ── Catálogo GenAI ───────────────────────────────────────────────────────

    @property
    @abstractmethod
    def genai_available_models(self) -> list[str]:
        """Allowlist normalizada de modelos permitidos."""
        raise NotImplementedError

    @property
    @abstractmethod
    def genai_available_providers(self) -> list[str]:
        """Allowlist normalizada de provedores permitidos."""
        raise NotImplementedError

    # ── Sessão e persistência ────────────────────────────────────────────────

    @property
    @abstractmethod
    def ralph_sessions_storage_path(self) -> str:
        """Diretório onde os JSON de sessão são gravados."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ralph_session_flush_every_message(self) -> bool:
        """Persiste a sessão a cada mensagem registrada."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ralph_session_id_prefix(self) -> str:
        """Prefixo dos identificadores de sessão."""
        raise NotImplementedError

    # ── Resiliência de custo ─────────────────────────────────────────────────

    @property
    @abstractmethod
    def ralph_max_task_attempts(self) -> int:
        """Tentativas máximas de B.1/B.2 para a mesma tarefa."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ralph_max_additional_planning_rounds(self) -> int:
        """Execuções máximas de C.2 por sessão."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ralph_max_tasks_per_session(self) -> int:
        """Total máximo de tarefas somando A.2 e todas as rodadas de C.2."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ralph_max_llm_calls_per_session(self) -> int:
        """Teto absoluto de chamadas ao modelo por sessão."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ralph_session_token_budget(self) -> int:
        """Teto de tokens (entrada + saída) da sessão inteira."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ralph_final_answer_token_reserve(self) -> int:
        """Reserva de tokens que o loop nunca consome, garantindo a execução de C.3."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ralph_session_timeout_seconds(self) -> int:
        """Tempo máximo de parede da sessão."""
        raise NotImplementedError

    # ── Fluxo de thinking ────────────────────────────────────────────────────

    @property
    @abstractmethod
    def ralph_prompt_templates_path(self) -> str:
        """Diretório dos templates de prompt em markdown."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ralph_json_parse_max_retries(self) -> int:
        """Retentativas quando o modelo devolve JSON inválido."""
        raise NotImplementedError

    # ── Transporte ───────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def ralph_websocket_max_message_bytes(self) -> int:
        """Tamanho máximo, em bytes, do frame recebido no WebSocket."""
        raise NotImplementedError

    # ── Utilitários ──────────────────────────────────────────────────────────

    @abstractmethod
    def logger(self, module_file: str) -> logging.Logger:
        """Devolve um logger nomeado pelo caminho relativo do módulo.

        Args:
            module_file: Caminho absoluto do arquivo do módulo chamador.

        Returns:
            logging.Logger: Logger configurado para o módulo.
        """
        raise NotImplementedError
