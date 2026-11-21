import logging

from src.domain.interfaces.auth_session_repository_interface import IAuthSessionRepository
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.token_generator_interface import ITokenGenerator


class LogoutUseCase:
    """Revoga a sessão do cookie. A revogação é permanente: o mesmo token nunca volta a valer."""

    def __init__(
        self,
        sessions: IAuthSessionRepository,
        tokens: ITokenGenerator,
        clock: IClock,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso."""
        self.sessions = sessions
        self.tokens = tokens
        self.clock = clock
        self.logger = logger

    async def execute(self, token: str) -> bool:
        """Revoga a sessão do token.

        Args:
            token: Valor do cookie de sessão.

        Returns:
            bool: `True` quando uma sessão ativa foi revogada.
        """
        if not token:
            return False
        revoked = await self.sessions.revoke(self.tokens.digest(token), revoked_at=self.clock.now())
        if revoked:
            self.logger.info("Sessão revogada por logout")
        return revoked
