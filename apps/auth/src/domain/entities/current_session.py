from dataclasses import dataclass

from src.domain.entities.auth_session import AuthSession
from src.domain.entities.user import User


@dataclass(frozen=True)
class CurrentSession:
    """Sessão válida e a conta a que pertence."""

    user: User
    session: AuthSession
