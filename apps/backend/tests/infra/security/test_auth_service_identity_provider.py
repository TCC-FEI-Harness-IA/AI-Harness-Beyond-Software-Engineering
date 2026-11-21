import json
import logging

import httpx
import pytest

from src.domain.errors.identity_service_unavailable_error import IdentityServiceUnavailableError
from src.infra.security.auth_service_identity_provider import AuthServiceIdentityProvider

_INTERNO = "segredo-interno-de-teste-com-mais-de-32-caracteres"
_RESPOSTA = {
    "user_id": "usr_1", "role": "user", "session_id": "ses_1",
    "expires_at": "2026-11-16T12:00:00+00:00", "csrf_token": "csrf-1",
}


def _provider(handler) -> tuple[AuthServiceIdentityProvider, list[httpx.Request]]:
    capturadas: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        capturadas.append(request)
        return handler(request)

    provider = AuthServiceIdentityProvider(
        base_url="http://auth:8001", internal_token=_INTERNO, logger=logging.getLogger("teste"),
        timeout_seconds=2, transport=httpx.MockTransport(_handler),
    )
    return provider, capturadas


async def test_sessao_valida_vira_identidade_autenticada() -> None:
    provider, capturadas = _provider(lambda _: httpx.Response(200, json=_RESPOSTA))

    identidade = await provider.verify(session_token="token-do-cookie")

    assert identidade is not None
    assert identidade.user_id == "usr_1"
    assert identidade.session_id == "ses_1"
    assert identidade.csrf_token == "csrf-1"
    assert identidade.session_expires_at.isoformat() == "2026-11-16T12:00:00+00:00"
    pedido = capturadas[0]
    assert str(pedido.url) == "http://auth:8001/internal/sessions/verify"
    assert pedido.headers["authorization"] == f"Bearer {_INTERNO}"
    assert json.loads(pedido.content) == {"token": "token-do-cookie"}


async def test_sessao_recusada_devolve_none() -> None:
    provider, _ = _provider(lambda _: httpx.Response(401, json={"detail": "x"}))

    assert await provider.verify(session_token="token") is None


async def test_token_vazio_nem_consulta_o_servico() -> None:
    provider, capturadas = _provider(lambda _: httpx.Response(200, json=_RESPOSTA))

    assert await provider.verify(session_token="") is None
    assert capturadas == []


@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(500, json={}),
        httpx.Response(200, json={"user_id": "usr_1"}),
        httpx.Response(200, text="nao-json"),
    ],
)
async def test_falhas_do_servico_nunca_liberam_acesso(resposta: httpx.Response) -> None:
    provider, _ = _provider(lambda _: resposta)

    with pytest.raises(IdentityServiceUnavailableError):
        await provider.verify(session_token="token")


async def test_servico_fora_do_ar_falha_fechado() -> None:
    def _cai(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("recusado")

    provider, _ = _provider(_cai)

    with pytest.raises(IdentityServiceUnavailableError):
        await provider.verify(session_token="token")
