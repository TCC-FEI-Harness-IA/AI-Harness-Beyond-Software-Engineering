import logging
from dataclasses import dataclass

import pytest

from src.application.usecases.login_usecase import LoginUseCase
from src.application.usecases.logout_usecase import LogoutUseCase
from src.application.usecases.provision_admin_usecase import ProvisionAdminUseCase
from src.application.usecases.register_user_usecase import RegisterUserUseCase
from src.application.usecases.resolve_session_usecase import ResolveSessionUseCase
from src.domain.services.password_policy import PasswordPolicy
from src.infra.adapters.secure_token_generator import SecureTokenGenerator
from tests.doubles.fakes import (
    FakeClock,
    InMemoryAuthSessionRepository,
    InMemoryLoginAttemptLimiter,
    InMemoryUserRepository,
    fast_hasher,
)

TTL_24H = 24 * 60 * 60


@dataclass
class AuthWorld:
    clock: FakeClock
    users: InMemoryUserRepository
    sessions: InMemoryAuthSessionRepository
    limiter: InMemoryLoginAttemptLimiter
    register: RegisterUserUseCase
    login: LoginUseCase
    logout: LogoutUseCase
    resolve: ResolveSessionUseCase
    provision_admin: ProvisionAdminUseCase


@pytest.fixture
def world() -> AuthWorld:
    clock = FakeClock()
    users = InMemoryUserRepository()
    sessions = InMemoryAuthSessionRepository()
    limiter = InMemoryLoginAttemptLimiter(clock=clock, max_attempts=3, window_seconds=600)
    hasher = fast_hasher()
    tokens = SecureTokenGenerator()
    policy = PasswordPolicy(min_length=12, max_length=128)
    logger = logging.getLogger("teste")
    return AuthWorld(
        clock=clock,
        users=users,
        sessions=sessions,
        limiter=limiter,
        register=RegisterUserUseCase(
            users=users, hasher=hasher, tokens=tokens, clock=clock, policy=policy, logger=logger
        ),
        login=LoginUseCase(
            users=users, sessions=sessions, hasher=hasher, tokens=tokens, clock=clock,
            limiter=limiter, session_ttl_seconds=TTL_24H, logger=logger,
        ),
        logout=LogoutUseCase(sessions=sessions, tokens=tokens, clock=clock, logger=logger),
        resolve=ResolveSessionUseCase(users=users, sessions=sessions, tokens=tokens, clock=clock),
        provision_admin=ProvisionAdminUseCase(
            users=users, hasher=hasher, tokens=tokens, clock=clock, policy=policy, logger=logger
        ),
    )
