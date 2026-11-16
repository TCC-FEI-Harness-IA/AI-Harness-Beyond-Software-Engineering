import logging
from datetime import timedelta

from src.domain.entities.auth_session import AuthSession
from src.domain.entities.email_address import EmailAddress
from src.domain.entities.login_result import LoginResult
from src.domain.errors.invalid_credentials_error import InvalidCredentialsError
from src.domain.errors.invalid_registration_error import InvalidRegistrationError
from src.domain.interfaces.auth_session_repository_interface import IAuthSessionRepository
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.login_attempt_limiter_interface import ILoginAttemptLimiter
from src.domain.interfaces.password_hasher_interface import IPasswordHasher
from src.domain.interfaces.token_generator_interface import ITokenGenerator
from src.domain.interfaces.user_repository_interface import IUserRepository


class LoginUseCase:
    """Autentica por e-mail e senha e abre uma sessão de expiração absoluta."""

    def __init__(
        self,
        users: IUserRepository,
        sessions: IAuthSessionRepository,
        hasher: IPasswordHasher,
        tokens: ITokenGenerator,
        clock: IClock,
        limiter: ILoginAttemptLimiter,
        session_ttl_seconds: int,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso.

        Args:
            users: Contas.
            sessions: Sessões de autenticação.
            hasher: Verificação de senhas.
            tokens: Geração de token, resumo e identificadores.
            clock: Fonte de tempo.
            limiter: Limite de tentativas por e-mail e por cliente.
            session_ttl_seconds: Validade absoluta da sessão.
            logger: Logger do módulo.
        """
        self.users = users
        self.sessions = sessions
        self.hasher = hasher
        self.tokens = tokens
        self.clock = clock
        self.limiter = limiter
        self.session_ttl = timedelta(seconds=session_ttl_seconds)
        self.logger = logger

    async def execute(self, email: str, password: str, client_key: str) -> LoginResult:
        """Verifica as credenciais e cria a sessão.

        Args:
            email: E-mail como digitado.
            password: Senha em texto claro (só em memória).
            client_key: Identificação do cliente para o limite de tentativas (ex.: `ip:...`).

        Returns:
            LoginResult: Conta, sessão e token do cookie.

        Raises:
            TooManyAttemptsError: Quando o e-mail ou o cliente excedeu o limite de tentativas.
            InvalidCredentialsError: Quando e-mail ou senha não conferem.
        """
        try:
            address = EmailAddress.parse(email).value
        except InvalidRegistrationError as exc:
            raise InvalidCredentialsError() from exc
        email_key = f"email:{address}"
        keys = [email_key, client_key]
        await self.limiter.ensure_allowed(keys)

        user = await self.users.find_by_email(address)
        if user is None:
            self.hasher.burn_verification(password)
            await self.limiter.register_failure(keys)
            raise InvalidCredentialsError()
        if not self.hasher.verify(user.password_hash, password):
            await self.limiter.register_failure(keys)
            self.logger.info("Falha de login para a conta '%s'", user.id)
            raise InvalidCredentialsError()

        await self.limiter.reset(email_key)
        if self.hasher.needs_rehash(user.password_hash):
            user = user.with_password_hash(self.hasher.hash(password))
            await self.users.update(user)

        token = self.tokens.session_token()
        now = self.clock.now()
        session = AuthSession(
            id=self.tokens.session_id(),
            token_hash=self.tokens.digest(token),
            user_id=user.id,
            created_at=now,
            expires_at=now + self.session_ttl,
            csrf_token=self.tokens.csrf_token(),
        )
        await self.sessions.insert(session)
        self.logger.info("Sessão '%s' aberta para a conta '%s'", session.id, user.id)
        return LoginResult(user=user, session=session, token=token)
