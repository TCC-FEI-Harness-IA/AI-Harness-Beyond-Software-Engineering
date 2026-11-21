from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from src.main import create_app
from datetime import UTC, datetime

from tests.doubles.fakes import FakeClock, fast_hasher

INTERNAL_TOKEN = "segredo-interno-de-teste-com-mais-de-32-caracteres"
ORIGEM = "https://ralph.exemplo.com"


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Configura o ambiente do serviço; `secure=True` liga cookies `Secure` e o prefixo `__Host-`."""

    def _configure(secure: bool = False, production: bool = False, trust_proxy: bool = False) -> None:
        monkeypatch.setenv("APP_ENV", "production" if production else "development")
        monkeypatch.setenv("AUTH_INTERNAL_TOKEN", INTERNAL_TOKEN)
        monkeypatch.setenv("AUTH_COOKIE_SECURE", "true" if secure else "false")
        monkeypatch.setenv("PUBLIC_ORIGINS", ORIGEM)
        monkeypatch.setenv("AUTH_LOGIN_MAX_ATTEMPTS", "3")
        monkeypatch.setenv("AUTH_TRUST_PROXY_HEADERS", "true" if trust_proxy else "false")

    return _configure


# No futuro: o mongomock aplica os índices TTL (sessões, tentativas) contra o relógio real.
INICIO_ROTAS = datetime(2099, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(INICIO_ROTAS)


@pytest.fixture
def mongo() -> AsyncMongoMockClient:
    return AsyncMongoMockClient(tz_aware=True)


@pytest.fixture
def make_client(
    auth_env: Callable[..., None], clock: FakeClock, mongo: AsyncMongoMockClient
) -> Iterator[Callable[..., TestClient]]:
    """Cria o app sobre o MongoDB em memória e o relógio controlável, executando o `lifespan` (índices)."""
    abertos: list[TestClient] = []

    def _make(secure: bool = False, trust_proxy: bool = False) -> TestClient:
        auth_env(secure=secure, trust_proxy=trust_proxy)
        app = create_app(mongo_client=mongo, clock=clock, hasher=fast_hasher())
        base_url = "https://testserver" if secure else "http://testserver"
        client = TestClient(app, base_url=base_url)
        client.__enter__()
        abertos.append(client)
        return client

    yield _make
    for client in abertos:
        client.__exit__(None, None, None)
