from dataclasses import dataclass, field
from datetime import datetime

_ADMIN_ROLE = "admin"


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identidade validada pelo serviço de autenticação para a requisição atual.

    Nunca vem do cliente: é o retorno da verificação interna do cookie de sessão.

    Attributes:
        user_id: Identificador estável da conta; é o proprietário dos dados pessoais.
        role: Perfil (`user` ou `admin`).
        session_id: Identificador não secreto da sessão de autenticação.
        session_expires_at: Fim absoluto da sessão (24 h após o login).
        csrf_token: Token anti-CSRF da sessão, comparado com o header `X-CSRF-Token`.
    """

    user_id: str
    role: str
    session_id: str
    session_expires_at: datetime
    csrf_token: str = field(repr=False)

    @property
    def is_admin(self) -> bool:
        """Informa se a conta é administradora."""
        return self.role == _ADMIN_ROLE
