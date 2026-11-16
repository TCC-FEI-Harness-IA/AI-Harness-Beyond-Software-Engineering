from src.domain.entities.current_session import CurrentSession
from src.domain.errors.session_invalid_error import SessionInvalidError
from src.domain.interfaces.auth_session_repository_interface import IAuthSessionRepository
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.token_generator_interface import ITokenGenerator
from src.domain.interfaces.user_repository_interface import IUserRepository


class ResolveSessionUseCase:
    """Valida o token de um cookie e devolve a sessão e a conta correspondentes."""

    def __init__(
        self,
        users: IUserRepository,
        sessions: IAuthSessionRepository,
        tokens: ITokenGenerator,
        clock: IClock,
    ) -> None:
        """Inicializa o caso de uso com as portas de contas, sessões, resumo de token e tempo."""
        self.users = users
        self.sessions = sessions
        self.tokens = tokens
        self.clock = clock

    async def execute(self, token: str) -> CurrentSession:
        """Resolve o token.

        Args:
            token: Valor do cookie de sessão.

        Returns:
            CurrentSession: Sessão ativa e conta.

        Raises:
            SessionInvalidError: Token vazio, desconhecido, revogado, expirado ou de conta inexistente.
        """
        if not token:
            raise SessionInvalidError()
        session = await self.sessions.find_by_token_hash(self.tokens.digest(token))
        if session is None or not session.is_active(now=self.clock.now()):
            raise SessionInvalidError()
        user = await self.users.find_by_id(session.user_id)
        if user is None:
            raise SessionInvalidError()
        return CurrentSession(user=user, session=session)
