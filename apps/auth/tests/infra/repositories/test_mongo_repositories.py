import logging
from datetime import UTC, datetime, timedelta

import pytest
from mongomock_motor import AsyncMongoMockClient

from src.domain.entities.auth_session import AuthSession
from src.domain.entities.user import User
from src.domain.enums.user_role_enum import UserRoleEnum
from src.domain.errors.email_already_registered_error import EmailAlreadyRegisteredError
from src.domain.errors.too_many_attempts_error import TooManyAttemptsError
from src.infra.repositories.mongo_auth_session_repository import MongoAuthSessionRepository
from src.infra.repositories.mongo_login_attempt_limiter import MongoLoginAttemptLimiter
from src.infra.repositories.mongo_user_repository import MongoUserRepository
from tests.doubles.fakes import FakeClock

# Datas no futuro: o mongomock aplica índices TTL contra o relógio real.
_AGORA = datetime(2099, 1, 1, 12, 0, tzinfo=UTC)
_LOGGER = logging.getLogger("teste")


def _user(user_id: str = "usr_1", email: str = "ana@exemplo.com") -> User:
    return User(id=user_id, email=email, password_hash="$argon2id$hash", role=UserRoleEnum.USER, created_at=_AGORA)


def _session(token_hash: str = "h1") -> AuthSession:
    return AuthSession(
        id="ses_1", token_hash=token_hash, user_id="usr_1", created_at=_AGORA,
        expires_at=_AGORA + timedelta(hours=24), csrf_token="csrf",
    )


async def test_usuario_e_gravado_sem_senha_e_lido_de_volta(mongo_client: AsyncMongoMockClient) -> None:
    repo = MongoUserRepository(collection=mongo_client["auth"]["users"], logger=_LOGGER)
    await repo.ensure_indexes()

    await repo.insert(_user())

    documento = await mongo_client["auth"]["users"].find_one({"_id": "usr_1"})
    assert documento["email"] == "ana@exemplo.com"
    assert documento["password_hash"] == "$argon2id$hash"
    assert "password" not in documento
    assert await repo.find_by_email("ana@exemplo.com") == _user()
    assert await repo.find_by_id("usr_1") == _user()
    assert await repo.find_by_id("usr_x") is None
    assert await repo.find_by_email("x@exemplo.com") is None


async def test_indice_unico_impede_email_duplicado(mongo_client: AsyncMongoMockClient) -> None:
    repo = MongoUserRepository(collection=mongo_client["auth"]["users"], logger=_LOGGER)
    await repo.ensure_indexes()
    await repo.insert(_user())

    with pytest.raises(EmailAlreadyRegisteredError):
        await repo.insert(_user(user_id="usr_2"))


async def test_atualiza_hash_e_perfil(mongo_client: AsyncMongoMockClient) -> None:
    repo = MongoUserRepository(collection=mongo_client["auth"]["users"], logger=_LOGGER)
    await repo.insert(_user())

    await repo.update(_user().promoted_to_admin().with_password_hash("$argon2id$novo"))

    lido = await repo.find_by_id("usr_1")
    assert lido is not None
    assert lido.role is UserRoleEnum.ADMIN
    assert lido.password_hash == "$argon2id$novo"


async def test_sessao_persiste_entre_clientes_e_pode_ser_revogada(mongo_client: AsyncMongoMockClient) -> None:
    repo = MongoAuthSessionRepository(collection=mongo_client["auth"]["sessions"], logger=_LOGGER)
    await repo.ensure_indexes()
    await repo.insert(_session())

    reiniciado = MongoAuthSessionRepository(collection=mongo_client["auth"]["sessions"], logger=_LOGGER)
    lida = await reiniciado.find_by_token_hash("h1")
    assert lida == _session()
    assert lida.expires_at.tzinfo is not None

    assert await reiniciado.revoke("h1", revoked_at=_AGORA) is True
    assert await reiniciado.revoke("h1", revoked_at=_AGORA) is False
    assert (await repo.find_by_token_hash("h1")).revoked_at == _AGORA
    assert await repo.find_by_token_hash("h-desconhecido") is None


async def test_datas_sem_fuso_vindas_do_driver_sao_tratadas_como_utc() -> None:
    cliente_sem_fuso = AsyncMongoMockClient()
    repo = MongoAuthSessionRepository(collection=cliente_sem_fuso["auth"]["sessions"], logger=_LOGGER)
    await repo.insert(_session())

    lida = await repo.find_by_token_hash("h1")

    assert lida is not None and lida.expires_at == _AGORA + timedelta(hours=24)


async def test_limitador_conta_falhas_por_chave_e_janela(mongo_client: AsyncMongoMockClient) -> None:
    clock = FakeClock(_AGORA)
    limiter = MongoLoginAttemptLimiter(
        collection=mongo_client["auth"]["attempts"], clock=clock, max_attempts=2, window_seconds=60
    )
    await limiter.ensure_indexes()

    await limiter.ensure_allowed(["email:a"])
    await limiter.register_failure(["email:a", "ip:1"])
    await limiter.register_failure(["email:a"])

    with pytest.raises(TooManyAttemptsError) as erro:
        await limiter.ensure_allowed(["ip:1", "email:a"])
    assert erro.value.retry_after_seconds == 60
    await limiter.ensure_allowed(["ip:1"])

    clock.advance(seconds=60)
    await limiter.ensure_allowed(["email:a"])
    await limiter.register_failure(["email:a"])
    await limiter.ensure_allowed(["email:a"])


async def test_limitador_reinicia_contador(mongo_client: AsyncMongoMockClient) -> None:
    clock = FakeClock(_AGORA)
    limiter = MongoLoginAttemptLimiter(
        collection=mongo_client["auth"]["attempts"], clock=clock, max_attempts=1, window_seconds=60
    )
    await limiter.register_failure(["email:a"])

    await limiter.reset("email:a")

    await limiter.ensure_allowed(["email:a"])
