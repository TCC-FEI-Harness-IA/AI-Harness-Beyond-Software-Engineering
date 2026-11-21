"""Dublês e utilitários de autenticação para a suíte do backend.

Só existem nos testes: em produção, `create_app()` sempre monta o provedor de identidade real
(serviço de autenticação) e o validador real da OpenRouter.
"""
import secrets
from dataclasses import replace
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.errors.credential_rejected_error import CredentialRejectedError
from src.domain.errors.identity_service_unavailable_error import IdentityServiceUnavailableError
from src.domain.errors.llm_key_validation_unavailable_error import LLMKeyValidationUnavailableError
from src.domain.interfaces.identity_provider_interface import IIdentityProvider
from src.domain.interfaces.llm_key_validator_interface import ILLMKeyValidator
from src.domain.services.execution_authorization import ExecutionAuthorization
from src.infra.config.security_settings import SecuritySettings
from src.infra.security.security_services import SecurityServices
from tests.doubles.controllable_clock import ControllableClock

ORIGEM = "http://localhost:5173"
CHAVE_VALIDA = "sk-or-v1-chave-ficticia-valida-0001"
CHAVE_VALIDA_2 = "sk-or-v1-chave-ficticia-valida-0002"


class FakeIdentityProvider(IIdentityProvider):
    """Sessões de autenticação em memória, com revogação e indisponibilidade programáveis."""

    def __init__(self, clock: ControllableClock) -> None:
        self.clock = clock
        self.sessions: dict[str, AuthenticatedUser] = {}
        self.unavailable = False
        self.calls = 0

    def login(self, user_id: str, role: str = "user", hours: float = 24) -> tuple[str, AuthenticatedUser]:
        token = secrets.token_urlsafe(16)
        identity = AuthenticatedUser(
            user_id=user_id,
            role=role,
            session_id=f"ses_{secrets.token_hex(4)}",
            session_expires_at=self.clock.now() + timedelta(hours=hours),
            csrf_token=secrets.token_urlsafe(8),
        )
        self.sessions[token] = identity
        return token, identity

    def revoke(self, token: str) -> None:
        self.sessions.pop(token, None)

    async def verify(self, session_token: str) -> AuthenticatedUser | None:
        self.calls += 1
        if self.unavailable:
            raise IdentityServiceUnavailableError()
        identity = self.sessions.get(session_token)
        if identity is None or self.clock.now() >= identity.session_expires_at:
            return None
        return identity


class FakeKeyValidator(ILLMKeyValidator):
    """Validador da OpenRouter sem rede: só as chaves cadastradas são aceitas."""

    def __init__(self, accepted: set[str] | None = None) -> None:
        self.accepted = accepted if accepted is not None else {CHAVE_VALIDA, CHAVE_VALIDA_2}
        self.unavailable = False
        self.validated: list[str] = []

    async def validate(self, api_key: str) -> None:
        self.validated.append(api_key)
        if self.unavailable:
            raise LLMKeyValidationUnavailableError()
        if api_key not in self.accepted:
            raise CredentialRejectedError()


def test_security_settings(**overrides: object) -> SecuritySettings:
    base = SecuritySettings(
        environment="development",
        auth_service_url="http://auth.test",
        internal_token="segredo-interno-de-teste-com-mais-de-32-caracteres",
        credential_encryption_key=secrets.token_bytes(32),
        cookie_secure=False,
        public_origins=(ORIGEM,),
        key_validation_url="https://openrouter.test/api/v1/key",
        revalidation_interval_seconds=0.02,
        max_concurrent_runs_per_user=2,
        max_run_starts_per_window=100,
        run_starts_window_seconds=3600,
    )
    return replace(base, **overrides)


test_security_settings.__test__ = False  # type: ignore[attr-defined]


def build_security(
    clock: ControllableClock | None = None,
    identity_provider: FakeIdentityProvider | None = None,
    key_validator: FakeKeyValidator | None = None,
    **settings_overrides: object,
) -> SecurityServices:
    """Serviços de segurança com identidade e validação de chave falsas, e criptografia real."""
    clock = clock or ControllableClock()
    return SecurityServices.build(
        settings=test_security_settings(**settings_overrides),
        clock=clock,
        identity_provider=identity_provider or FakeIdentityProvider(clock),
        key_validator=key_validator or FakeKeyValidator(),
    )


def sign_in(client: TestClient, security: SecurityServices, user_id: str = "usr_ana", role: str = "user") -> dict:
    """Abre uma sessão falsa e grava o cookie de sessão no cliente; devolve os headers de escrita."""
    provider = security.identity_provider
    assert isinstance(provider, FakeIdentityProvider)
    token, identity = provider.login(user_id=user_id, role=role)
    client.cookies.set(security.settings.session_cookie_name, token)
    return {"X-CSRF-Token": identity.csrf_token, "Origin": ORIGEM}


def store_credential(client: TestClient, headers: dict, api_key: str = CHAVE_VALIDA) -> None:
    """Configura a chave OpenRouter da sessão atual pelo endpoint real."""
    response = client.put("/v1/credentials/openrouter", json={"api_key": api_key}, headers=headers)
    assert response.status_code == 200, response.text


def expires(at: datetime) -> str:
    return at.isoformat()


def authorization_for(
    api_key: str = CHAVE_VALIDA, owner_id: str = "usr_teste", clock: ControllableClock | None = None, hours: float = 24
) -> ExecutionAuthorization:
    """Autorização de execução com credencial em memória, para testes de serviços e startups."""
    from src.domain.entities.llm.llm_credential import LLMCredential

    clock = clock or ControllableClock()
    identity = AuthenticatedUser(
        user_id=owner_id,
        role="user",
        session_id=f"ses_{owner_id}",
        session_expires_at=clock.now() + timedelta(hours=hours),
        csrf_token="csrf",
    )
    credential = LLMCredential(
        api_key=api_key, owner_id=owner_id, session_id=identity.session_id, expires_at=identity.session_expires_at
    )
    return ExecutionAuthorization(identity=identity, credential=credential, clock=clock)


def authenticated_client(
    user_id: str = "usr_teste",
    with_credential: bool = True,
    security: SecurityServices | None = None,
    **client_kwargs: object,
) -> TestClient:
    """Cliente com sessão autenticada (e credencial OpenRouter, por padrão) na aplicação real.

    A sessão é criada no provedor de identidade falso; a credencial passa pelo endpoint real
    (`PUT /v1/credentials/openrouter`), que a cifra no cookie. Os headers de escrita (CSRF e
    origem) ficam como padrão do cliente, inclusive para o handshake dos WebSockets.
    """
    from src.main import create_app

    security = security or build_security()
    client = TestClient(create_app(security=security), **client_kwargs)  # type: ignore[arg-type]
    headers = sign_in(client, security, user_id=user_id)
    client.headers.update(headers)
    if with_credential:
        store_credential(client, headers)
    client.security = security  # type: ignore[attr-defined]
    return client
