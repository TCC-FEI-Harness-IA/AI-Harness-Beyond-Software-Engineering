"""Cada envio LLM revalida a sessão, mesmo antes do próximo ciclo do observador WebSocket."""
import logging
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import WebSocket
from starlette.requests import HTTPConnection

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.errors.execution_not_authorized_error import ExecutionNotAuthorizedError
from src.infra.security.request_security import open_authorization
from src.infra.security.websocket_security import WebSocketExecution
from src.infra.services.openrouter_service import OpenRouterService
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.security_doubles import CHAVE_VALIDA, build_security
from tests.infra.services.provider_spec import RESPOSTA_COMPLETA
from tests.infra.services.test_openrouter_service import _build_request


def _execution():
    security = build_security(revalidation_interval_seconds=3600)
    token, identity = security.identity_provider.login("usr_ana")
    sealed = security.credential_codec.seal(CHAVE_VALIDA, identity)
    cookies = (
        f"{security.settings.session_cookie_name}={token}; "
        f"{security.settings.credential_cookie_name}={sealed.value}"
    )
    connection = HTTPConnection({"type": "http", "headers": [(b"cookie", cookies.encode())]})
    authorization = open_authorization(connection, security, identity)
    sent: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json=RESPOSTA_COMPLETA)

    service = OpenRouterService(
        logging.getLogger("teste.revalidacao"), FakeSettings(), authorization, httpx.MockTransport(respond)
    )
    return security, token, identity, service, sent


@pytest.mark.parametrize("change", ["logout", "unavailable", "other_session", "other_user"])
async def test_sessao_invalida_bloqueia_o_proximo_envio_sem_esperar_o_observador(change: str) -> None:
    security, token, identity, service, sent = _execution()
    await service.generate_response(_build_request())
    if change == "logout":
        security.identity_provider.revoke(token)
    elif change == "unavailable":
        security.identity_provider.unavailable = True
    else:
        security.identity_provider.sessions[token] = replace(
            identity, **({"session_id": "ses_outra"} if change == "other_session" else {"user_id": "usr_bia"})
        )

    with pytest.raises(ExecutionNotAuthorizedError):
        await service.generate_response(_build_request())
    with pytest.raises(ExecutionNotAuthorizedError):
        await service.generate_response(_build_request())

    assert len(sent) == 1
    assert service.authorization.is_active is False


async def test_expiracao_enquanto_o_auth_responde_bloqueia_o_envio() -> None:
    security, _, identity, service, sent = _execution()

    async def slow_verification(session_token: str) -> AuthenticatedUser:
        security.clock.advance(seconds=86400)
        return identity

    security.identity_provider.verify = slow_verification

    with pytest.raises(ExecutionNotAuthorizedError):
        await service.generate_response(_build_request())
    assert sent == []


@pytest.mark.parametrize("handled_by_flow", [True, False])
async def test_recusa_antes_do_envio_encerra_websocket_como_revogado(handled_by_flow: bool) -> None:
    security, token, identity, service, sent = _execution()
    execution = WebSocketExecution(
        websocket=WebSocket({"type": "websocket"}, receive=AsyncMock(), send=AsyncMock()),
        security=security, identity=identity,
        authorization=service.authorization, session_token=token,
        slot=security.execution_limiter.acquire(identity.user_id),
    )

    async def work() -> None:
        security.identity_provider.revoke(token)
        try:
            await service.generate_response(_build_request())
        except ExecutionNotAuthorizedError:
            if not handled_by_flow:
                raise

    try:
        assert await execution.run(work()) is False
        assert sent == []
    finally:
        execution.release()
