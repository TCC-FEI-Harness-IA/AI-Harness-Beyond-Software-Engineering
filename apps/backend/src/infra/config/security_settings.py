import base64
import binascii
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

_ENVIRONMENTS = ("development", "production")
_TRUE = ("true", "1", "yes", "on")
_FALSE = ("false", "0", "no", "off")
_MIN_SECRET_LENGTH = 32
_KEY_BYTES = 32
_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


@dataclass(frozen=True)
class SecuritySettings:
    """Configuração de autenticação, credenciais e limites de execução, validada na inicialização.

    Diferente de `Settings` (lido sob demanda), é carregada de uma vez por `from_env`: a aplicação
    não sobe sem os segredos de infraestrutura. Segredos aceitam a variante `*_FILE` (segredos do
    Docker em `/run/secrets`) e nunca aparecem no `repr`.

    Attributes:
        environment: `development` ou `production`.
        auth_service_url: Endereço interno do serviço de autenticação.
        internal_token: Segredo de serviço da verificação interna de sessões.
        credential_encryption_key: Chave de aplicação (256 bits) do JWE da credencial LLM.
        cookie_secure: Cookies com `Secure` (obrigatório em produção).
        public_origins: Origens do frontend aceitas em escritas e WebSockets.
        key_validation_url: Endpoint da OpenRouter que valida a chave sem custo.
        revalidation_interval_seconds: Intervalo de revalidação da sessão durante uma execução.
        max_concurrent_runs_per_user: Execuções LLM simultâneas por conta (por instância).
        max_run_starts_per_window: Execuções iniciadas por conta na janela (por instância).
        run_starts_window_seconds: Duração da janela de inícios.
    """

    environment: str
    auth_service_url: str
    internal_token: str = field(repr=False)
    credential_encryption_key: bytes = field(repr=False)
    cookie_secure: bool
    public_origins: tuple[str, ...]
    key_validation_url: str
    revalidation_interval_seconds: float
    max_concurrent_runs_per_user: int
    max_run_starts_per_window: int
    run_starts_window_seconds: int

    @property
    def is_production(self) -> bool:
        """Informa se valem as regras de produção."""
        return self.environment == "production"

    @property
    def session_cookie_name(self) -> str:
        """Cookie de sessão emitido pelo serviço de autenticação (`__Host-` com `Secure`)."""
        return "__Host-ralph_session" if self.cookie_secure else "ralph_session"

    @property
    def credential_cookie_name(self) -> str:
        """Cookie da credencial LLM cifrada, restrito ao caminho `/v1` (`__Secure-` com `Secure`)."""
        return "__Secure-ralph_llm_credential" if self.cookie_secure else "ralph_llm_credential"

    @classmethod
    def from_env(cls) -> "SecuritySettings":
        """Lê e valida o ambiente.

        Raises:
            ValueError: Quando um segredo falta ou é inválido, ou quando uma exceção de desenvolvimento
                (cookie sem `Secure`, origem sem HTTPS) aparece em produção. A mensagem nomeia a variável.
        """
        environment = os.getenv("APP_ENV", "development").strip().lower()
        if environment not in _ENVIRONMENTS:
            raise ValueError(f"APP_ENV deve ser um de {', '.join(_ENVIRONMENTS)}.")
        settings = cls(
            environment=environment,
            auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://localhost:8001").rstrip("/"),
            internal_token=cls.__internal_token(),
            credential_encryption_key=cls.__encryption_key(),
            cookie_secure=cls.__bool("COOKIE_SECURE", False),
            public_origins=tuple(
                item.strip().rstrip("/")
                for item in os.getenv("PUBLIC_ORIGINS", "http://localhost:5173").split(",")
                if item.strip()
            ),
            key_validation_url=os.getenv("OPENROUTER_KEY_VALIDATION_URL", "https://openrouter.ai/api/v1/key"),
            revalidation_interval_seconds=cls.__positive_float("AUTH_REVALIDATION_INTERVAL_SECONDS", 15),
            max_concurrent_runs_per_user=int(cls.__positive_float("RUN_MAX_CONCURRENT_PER_USER", 2)),
            max_run_starts_per_window=int(cls.__positive_float("RUN_MAX_STARTS_PER_WINDOW", 30)),
            run_starts_window_seconds=int(cls.__positive_float("RUN_STARTS_WINDOW_SECONDS", 3600)),
        )
        if settings.is_production:
            if not settings.cookie_secure:
                raise ValueError("Em produção, COOKIE_SECURE precisa ser true.")
            if any(not origin.startswith("https://") for origin in settings.public_origins):
                raise ValueError("Em produção, PUBLIC_ORIGINS só aceita origens https://.")
        return settings

    @staticmethod
    def __secret(name: str) -> str:
        file_path = os.getenv(f"{name}_FILE")
        if file_path:
            try:
                return Path(file_path).read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise ValueError(f"Não foi possível ler {name}_FILE.") from exc
        return os.getenv(name, "").strip()

    @classmethod
    def __internal_token(cls) -> str:
        token = cls.__secret("AUTH_INTERNAL_TOKEN")
        if len(token) < _MIN_SECRET_LENGTH:
            raise ValueError(f"Defina AUTH_INTERNAL_TOKEN (ou _FILE) com pelo menos {_MIN_SECRET_LENGTH} caracteres.")
        return token

    @classmethod
    def __encryption_key(cls) -> bytes:
        raw = cls.__secret("LLM_CREDENTIAL_ENCRYPTION_KEY")
        if not raw:
            raise ValueError("Defina LLM_CREDENTIAL_ENCRYPTION_KEY (ou _FILE): 32 bytes em base64url.")
        try:
            if not _BASE64URL.fullmatch(raw):
                raise ValueError("alfabeto fora do base64url")
            key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        except (binascii.Error, ValueError) as exc:
            raise ValueError("LLM_CREDENTIAL_ENCRYPTION_KEY precisa estar em base64url.") from exc
        if len(key) != _KEY_BYTES:
            raise ValueError("LLM_CREDENTIAL_ENCRYPTION_KEY precisa decodificar para 32 bytes (256 bits).")
        return key

    @staticmethod
    def __bool(name: str, default: bool) -> bool:
        raw = os.getenv(name, "").strip().lower()
        if not raw:
            return default
        if raw in _TRUE:
            return True
        if raw in _FALSE:
            return False
        raise ValueError(f"{name} deve ser true ou false.")

    @staticmethod
    def __positive_float(name: str, default: float) -> float:
        raw = os.getenv(name, "").strip()
        if not raw:
            return default
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(f"{name} deve ser numérico.") from exc
        if value <= 0:
            raise ValueError(f"{name} deve ser positivo.")
        return value
