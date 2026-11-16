import logging

import httpx
import pytest

from src.domain.errors.credential_rejected_error import CredentialRejectedError
from src.domain.errors.llm_key_validation_unavailable_error import LLMKeyValidationUnavailableError
from src.infra.security.openrouter_key_validator import OpenRouterKeyValidator

_CHAVE = "sk-or-v1-chave-ficticia-de-teste"


def _validator(handler) -> tuple[OpenRouterKeyValidator, list[httpx.Request]]:
    capturadas: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        capturadas.append(request)
        return handler(request)

    return (
        OpenRouterKeyValidator(
            validation_url="https://openrouter.test/api/v1/key", logger=logging.getLogger("teste"),
            timeout_seconds=2, transport=httpx.MockTransport(_handler),
        ),
        capturadas,
    )


async def test_chave_aceita_pela_openrouter() -> None:
    validator, capturadas = _validator(lambda _: httpx.Response(200, json={"data": {"label": "x"}}))

    await validator.validate(api_key=_CHAVE)

    assert capturadas[0].method == "GET"
    assert capturadas[0].headers["authorization"] == f"Bearer {_CHAVE}"


@pytest.mark.parametrize("status", [401, 403])
async def test_chave_rejeitada_pela_openrouter(status: int, caplog: pytest.LogCaptureFixture) -> None:
    validator, _ = _validator(lambda _: httpx.Response(status, json={"error": {"message": f"bad {_CHAVE}"}}))

    with pytest.raises(CredentialRejectedError) as erro:
        await validator.validate(api_key=_CHAVE)

    assert _CHAVE not in str(erro.value)
    assert _CHAVE not in caplog.text


@pytest.mark.parametrize("resposta", [httpx.Response(500), httpx.Response(429)])
async def test_falha_temporaria_da_openrouter(resposta: httpx.Response) -> None:
    validator, _ = _validator(lambda _: resposta)

    with pytest.raises(LLMKeyValidationUnavailableError):
        await validator.validate(api_key=_CHAVE)


async def test_rede_indisponivel() -> None:
    def _cai(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"falhou {_CHAVE}")

    validator, _ = _validator(_cai)

    with pytest.raises(LLMKeyValidationUnavailableError) as erro:
        await validator.validate(api_key=_CHAVE)
    assert _CHAVE not in str(erro.value)


async def test_formato_absurdo_nem_chega_a_rede() -> None:
    validator, capturadas = _validator(lambda _: httpx.Response(200))

    for invalida in ["", "   ", "x" * 300, "com espaco no meio", "quebra\nde linha"]:
        with pytest.raises(CredentialRejectedError):
            await validator.validate(api_key=invalida)
    assert capturadas == []
