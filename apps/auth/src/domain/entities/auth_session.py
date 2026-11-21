from dataclasses import dataclass, field, replace
from datetime import datetime


@dataclass(frozen=True)
class AuthSession:
    """Sessão de autenticação persistida.

    O token opaco entregue no cookie nunca é armazenado: só o seu resumo (`token_hash`). A expiração
    é absoluta, contada do login, e não é renovada por atividade.

    Attributes:
        id: Identificador não secreto da sessão, usado para vincular a credencial LLM a ela.
        token_hash: SHA-256 do token do cookie.
        user_id: Dono da sessão.
        created_at: Instante do login, em UTC.
        expires_at: Fim absoluto da validade, em UTC.
        csrf_token: Token anti-CSRF (padrão *synchronizer token*) vinculado a esta sessão.
        revoked_at: Instante da revogação (logout), quando houve.
    """

    id: str
    token_hash: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    csrf_token: str = field(repr=False)
    revoked_at: datetime | None = None

    def is_active(self, now: datetime) -> bool:
        """Informa se a sessão vale no instante dado: não revogada e antes do fim absoluto."""
        return self.revoked_at is None and now < self.expires_at

    def revoked(self, at: datetime) -> "AuthSession":
        """Cópia revogada da sessão."""
        return replace(self, revoked_at=at)
