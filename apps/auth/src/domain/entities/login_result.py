from dataclasses import dataclass, field

from src.domain.entities.auth_session import AuthSession
from src.domain.entities.user import User


@dataclass(frozen=True)
class LoginResult:
    """Resultado de um login: a conta, a sessão criada e o token a entregar no cookie.

    Attributes:
        user: Conta autenticada.
        session: Sessão persistida.
        token: Token opaco; só existe aqui, em memória, até virar cookie.
    """

    user: User
    session: AuthSession
    token: str = field(repr=False)
