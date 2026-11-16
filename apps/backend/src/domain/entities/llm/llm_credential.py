from dataclasses import dataclass, field
from datetime import datetime

_REDACTED = "[REDACTED]"


@dataclass(frozen=True)
class LLMCredential:
    """Chave OpenRouter do usuário, decifrada só para a requisição ou execução que a usa.

    Nunca é persistida: vive em memória e chega a cada requisição dentro do cookie cifrado. A
    representação textual omite a chave para que ela não vaze em logs, tracebacks ou mensagens.

    Attributes:
        api_key: Chave em claro.
        owner_id: Conta à qual a credencial foi vinculada.
        session_id: Sessão de autenticação à qual a credencial foi vinculada.
        expires_at: Fim da validade (nunca depois do fim da sessão).
    """

    api_key: str = field(repr=False)
    owner_id: str
    session_id: str
    expires_at: datetime

    def __post_init__(self) -> None:
        """Recusa uma chave vazia."""
        if not self.api_key.strip():
            raise ValueError("A credencial LLM não pode ser vazia.")

    def redact(self, text: str) -> str:
        """Substitui a chave por `[REDACTED]` num texto (ex.: corpo de erro do provedor)."""
        return text.replace(self.api_key, _REDACTED)
