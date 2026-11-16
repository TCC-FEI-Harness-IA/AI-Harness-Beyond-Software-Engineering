from motor.motor_asyncio import AsyncIOMotorClient

from src.application.usecases.login_usecase import LoginUseCase
from src.application.usecases.logout_usecase import LogoutUseCase
from src.application.usecases.provision_admin_usecase import ProvisionAdminUseCase
from src.application.usecases.register_user_usecase import RegisterUserUseCase
from src.application.usecases.resolve_session_usecase import ResolveSessionUseCase
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.password_hasher_interface import IPasswordHasher
from src.domain.services.password_policy import PasswordPolicy
from src.infra.adapters.secure_token_generator import SecureTokenGenerator
from src.infra.config.settings import Settings
from src.infra.repositories.mongo_auth_session_repository import MongoAuthSessionRepository
from src.infra.repositories.mongo_login_attempt_limiter import MongoLoginAttemptLimiter
from src.infra.repositories.mongo_user_repository import MongoUserRepository


class AuthContainer:
    """Composition root do serviço: um cliente MongoDB e os casos de uso, criados uma vez por processo."""

    def __init__(
        self,
        settings: Settings,
        mongo_client: AsyncIOMotorClient,
        clock: IClock,
        hasher: IPasswordHasher,
    ) -> None:
        """Monta repositórios e casos de uso.

        Args:
            settings: Configuração validada.
            mongo_client: Cliente do MongoDB (o real ou um dublê em memória).
            clock: Fonte de tempo.
            hasher: Hash de senhas.
        """
        self.settings = settings
        database = mongo_client[settings.mongodb_database]
        logger = settings.logger("auth")
        self.users = MongoUserRepository(collection=database[settings.users_collection], logger=logger)
        self.sessions = MongoAuthSessionRepository(collection=database[settings.sessions_collection], logger=logger)
        self.limiter = MongoLoginAttemptLimiter(
            collection=database[settings.login_attempts_collection],
            clock=clock,
            max_attempts=settings.login_max_attempts,
            window_seconds=settings.login_window_seconds,
        )
        tokens = SecureTokenGenerator()
        policy = PasswordPolicy(min_length=settings.password_min_length, max_length=settings.password_max_length)
        self.register_user = RegisterUserUseCase(
            users=self.users, hasher=hasher, tokens=tokens, clock=clock, policy=policy, logger=logger
        )
        self.login = LoginUseCase(
            users=self.users,
            sessions=self.sessions,
            hasher=hasher,
            tokens=tokens,
            clock=clock,
            limiter=self.limiter,
            session_ttl_seconds=settings.session_ttl_seconds,
            logger=logger,
        )
        self.logout = LogoutUseCase(sessions=self.sessions, tokens=tokens, clock=clock, logger=logger)
        self.resolve_session = ResolveSessionUseCase(
            users=self.users, sessions=self.sessions, tokens=tokens, clock=clock
        )
        self.provision_admin = ProvisionAdminUseCase(
            users=self.users, hasher=hasher, tokens=tokens, clock=clock, policy=policy, logger=logger
        )
        self.clock = clock

    async def ensure_indexes(self) -> None:
        """Cria os índices únicos e TTL (idempotente)."""
        await self.users.ensure_indexes()
        await self.sessions.ensure_indexes()
        await self.limiter.ensure_indexes()
