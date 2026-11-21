"""Dublês reutilizáveis da suíte do serviço de autenticação."""
from datetime import UTC, datetime, timedelta

from src.domain.entities.auth_session import AuthSession
from src.domain.entities.user import User
from src.domain.errors.email_already_registered_error import EmailAlreadyRegisteredError
from src.domain.errors.too_many_attempts_error import TooManyAttemptsError
from src.domain.interfaces.auth_session_repository_interface import IAuthSessionRepository
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.login_attempt_limiter_interface import ILoginAttemptLimiter
from src.domain.interfaces.user_repository_interface import IUserRepository
from src.infra.adapters.argon2_password_hasher import Argon2PasswordHasher

INICIO = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def fast_hasher() -> Argon2PasswordHasher:
    """Argon2id real com custo mínimo, para a suíte ficar rápida."""
    return Argon2PasswordHasher(time_cost=1, memory_cost_kib=8, parallelism=1)


class FakeClock(IClock):
    """Relógio controlável."""

    def __init__(self, now: datetime = INICIO) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)


class InMemoryUserRepository(IUserRepository):
    """Repositório de usuários em memória, com a mesma unicidade de e-mail do banco."""

    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    async def insert(self, user: User) -> None:
        if any(item.email == user.email for item in self.users.values()):
            raise EmailAlreadyRegisteredError()
        self.users[user.id] = user

    async def find_by_email(self, email: str) -> User | None:
        return next((item for item in self.users.values() if item.email == email), None)

    async def find_by_id(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    async def update(self, user: User) -> None:
        self.users[user.id] = user


class InMemoryAuthSessionRepository(IAuthSessionRepository):
    """Repositório de sessões em memória, indexado pelo resumo do token."""

    def __init__(self) -> None:
        self.sessions: dict[str, AuthSession] = {}

    async def insert(self, session: AuthSession) -> None:
        self.sessions[session.token_hash] = session

    async def find_by_token_hash(self, token_hash: str) -> AuthSession | None:
        return self.sessions.get(token_hash)

    async def revoke(self, token_hash: str, revoked_at: datetime) -> bool:
        session = self.sessions.get(token_hash)
        if session is None or session.revoked_at is not None:
            return False
        self.sessions[token_hash] = session.revoked(at=revoked_at)
        return True


class InMemoryLoginAttemptLimiter(ILoginAttemptLimiter):
    """Limitador de janela fixa em memória, com o mesmo contrato do de MongoDB."""

    def __init__(self, clock: IClock, max_attempts: int, window_seconds: int) -> None:
        self.clock = clock
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.counters: dict[str, tuple[int, datetime]] = {}

    async def ensure_allowed(self, keys: list[str]) -> None:
        for key in keys:
            count, started = self.counters.get(key, (0, self.clock.now()))
            elapsed = (self.clock.now() - started).total_seconds()
            if elapsed < self.window_seconds and count >= self.max_attempts:
                raise TooManyAttemptsError(retry_after_seconds=int(self.window_seconds - elapsed))

    async def register_failure(self, keys: list[str]) -> None:
        for key in keys:
            count, started = self.counters.get(key, (0, self.clock.now()))
            if (self.clock.now() - started).total_seconds() >= self.window_seconds:
                count, started = 0, self.clock.now()
            self.counters[key] = (count + 1, started)

    async def reset(self, key: str) -> None:
        self.counters.pop(key, None)
