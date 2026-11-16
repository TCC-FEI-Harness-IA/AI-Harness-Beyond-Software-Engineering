import logging
import os
from pathlib import Path

from src.infra.config.redacting_filter import RedactingFilter

_ENVIRONMENTS = ("development", "production")
_TRUE = ("true", "1", "yes")
_FALSE = ("false", "0", "no")
_MIN_SECRET_LENGTH = 32
# Mínimo recomendado pela OWASP para Argon2id: m=19 MiB, t=2, p=1.
_OWASP_MIN_MEMORY_KIB = 19456
_OWASP_MIN_TIME_COST = 2
_REQUIRED_SESSION_TTL = 24 * 60 * 60
_DEFAULT_ORIGIN = "http://localhost:5173"


class Settings:
    """Configuração do serviço de autenticação, lida e validada na construção.

    Segredos aceitam a variante `*_FILE` (ex.: segredos do Docker Compose em `/run/secrets`). Em
    produção (`APP_ENV=production`) as exceções de desenvolvimento são recusadas: cookie sem
    `Secure`, origem sem HTTPS, parâmetros de Argon2 abaixo do mínimo da OWASP ou sessão diferente
    de 24 horas.
    """

    def __init__(self) -> None:
        """Lê e valida as variáveis de ambiente.

        Raises:
            ValueError: Quando alguma variável está ausente ou inválida; a mensagem a nomeia.
        """
        self.environment = self.__choice("APP_ENV", "development", _ENVIRONMENTS)
        self.mongodb_uri = os.getenv("AUTH_MONGODB_URI", "mongodb://localhost:27017")
        self.mongodb_database = os.getenv("AUTH_MONGODB_DATABASE", "tcc_auth")
        self.users_collection = os.getenv("AUTH_USERS_COLLECTION", "users")
        self.sessions_collection = os.getenv("AUTH_SESSIONS_COLLECTION", "sessions")
        self.login_attempts_collection = os.getenv("AUTH_LOGIN_ATTEMPTS_COLLECTION", "login_attempts")
        self.session_ttl_seconds = self.__positive_int("AUTH_SESSION_TTL_SECONDS", _REQUIRED_SESSION_TTL)
        self.cookie_secure = self.__bool("AUTH_COOKIE_SECURE", False)
        self.internal_token = self.__secret("AUTH_INTERNAL_TOKEN")
        self.public_origins = self.__list("PUBLIC_ORIGINS", [_DEFAULT_ORIGIN])
        self.login_max_attempts = self.__positive_int("AUTH_LOGIN_MAX_ATTEMPTS", 5)
        self.login_window_seconds = self.__positive_int("AUTH_LOGIN_WINDOW_SECONDS", 900)
        self.trust_proxy_headers = self.__bool("AUTH_TRUST_PROXY_HEADERS", False)
        self.password_min_length = self.__positive_int("AUTH_PASSWORD_MIN_LENGTH", 12)
        self.password_max_length = self.__positive_int("AUTH_PASSWORD_MAX_LENGTH", 128)
        self.argon2_time_cost = self.__positive_int("AUTH_ARGON2_TIME_COST", 3)
        self.argon2_memory_cost_kib = self.__positive_int("AUTH_ARGON2_MEMORY_COST_KIB", 65536)
        self.argon2_parallelism = self.__positive_int("AUTH_ARGON2_PARALLELISM", 4)
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        if self.is_production:
            self.__validate_production()

    @property
    def is_production(self) -> bool:
        """Informa se o serviço roda com as regras de produção."""
        return self.environment == "production"

    @property
    def session_cookie_name(self) -> str:
        """Nome do cookie de sessão; com `Secure`, usa o prefixo `__Host-` (sem domínio, caminho `/`)."""
        return "__Host-ralph_session" if self.cookie_secure else "ralph_session"

    @property
    def credential_cookie_name(self) -> str:
        """Nome do cookie da credencial LLM emitido pelo backend; o logout o remove."""
        return "__Secure-ralph_llm_credential" if self.cookie_secure else "ralph_llm_credential"

    def logger(self, name: str) -> logging.Logger:
        """Logger com nível configurado e redação de segredos."""
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        if not any(isinstance(item, RedactingFilter) for item in logger.filters):
            logger.addFilter(RedactingFilter())
        return logger

    def __validate_production(self) -> None:
        if not self.cookie_secure:
            raise ValueError("Em produção, AUTH_COOKIE_SECURE precisa ser true.")
        if any(not origin.startswith("https://") for origin in self.public_origins):
            raise ValueError("Em produção, PUBLIC_ORIGINS só aceita origens https://.")
        if self.argon2_memory_cost_kib < _OWASP_MIN_MEMORY_KIB or self.argon2_time_cost < _OWASP_MIN_TIME_COST:
            raise ValueError("Parâmetros do Argon2 abaixo do mínimo recomendado pela OWASP (m=19 MiB, t=2).")
        if self.session_ttl_seconds != _REQUIRED_SESSION_TTL:
            raise ValueError("Em produção, a sessão dura exatamente 24 horas (AUTH_SESSION_TTL_SECONDS=86400).")

    @staticmethod
    def __secret(name: str) -> str:
        file_path = os.getenv(f"{name}_FILE")
        if file_path:
            try:
                value = Path(file_path).read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise ValueError(f"Não foi possível ler {name}_FILE.") from exc
        else:
            value = os.getenv(name, "").strip()
        if not value:
            raise ValueError(f"Defina {name} (ou {name}_FILE).")
        if len(value) < _MIN_SECRET_LENGTH:
            raise ValueError(f"{name} precisa ter pelo menos {_MIN_SECRET_LENGTH} caracteres.")
        return value

    @staticmethod
    def __choice(name: str, default: str, options: tuple[str, ...]) -> str:
        value = os.getenv(name, default).strip().lower()
        if value not in options:
            raise ValueError(f"{name} deve ser um de {', '.join(options)}.")
        return value

    @staticmethod
    def __bool(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None or not raw.strip():
            return default
        normalized = raw.strip().lower()
        if normalized in _TRUE:
            return True
        if normalized in _FALSE:
            return False
        raise ValueError(f"{name} deve ser true ou false.")

    @staticmethod
    def __positive_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None or not raw.strip():
            return default
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{name} deve ser um inteiro.") from exc
        if value <= 0:
            raise ValueError(f"{name} deve ser positivo.")
        return value

    @staticmethod
    def __list(name: str, default: list[str]) -> list[str]:
        raw = os.getenv(name)
        if raw is None or not raw.strip():
            return list(default)
        return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
