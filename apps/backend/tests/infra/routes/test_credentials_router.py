import json

import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.infra.security.security_services import SecurityServices
from tests.doubles.controllable_clock import ControllableClock
from tests.doubles.security_doubles import (
    CHAVE_VALIDA,
    CHAVE_VALIDA_2,
    ORIGEM,
    FakeIdentityProvider,
    FakeKeyValidator,
    build_security,
    sign_in,
)

_ROTA = "/v1/credentials/openrouter"


@pytest.fixture
def clock() -> ControllableClock:
    return ControllableClock()


@pytest.fixture
def validator() -> FakeKeyValidator:
    return FakeKeyValidator()


@pytest.fixture
def security(clock: ControllableClock, validator: FakeKeyValidator) -> SecurityServices:
    return build_security(clock=clock, key_validator=validator)


@pytest.fixture
def client(security: SecurityServices) -> TestClient:
    return TestClient(create_app(security=security))


def test_visitante_nao_consulta_nem_configura_credencial(client: TestClient) -> None:
    assert client.get(_ROTA).status_code == 401
    assert client.put(_ROTA, json={"api_key": CHAVE_VALIDA}, headers={"Origin": ORIGEM}).status_code == 401
    assert client.delete(_ROTA).status_code == 401


def test_estado_inicial_sem_credencial(client: TestClient, security: SecurityServices) -> None:
    sign_in(client, security)

    resposta = client.get(_ROTA)

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "missing", "available": False, "expires_at": None}
    assert resposta.headers["cache-control"] == "no-store, private"
    assert "Cookie" in resposta.headers["vary"]


def test_configura_credencial_valida_em_cookie_cifrado(
    client: TestClient, security: SecurityServices, validator: FakeKeyValidator
) -> None:
    headers = sign_in(client, security)

    resposta = client.put(_ROTA, json={"api_key": CHAVE_VALIDA}, headers=headers)

    assert resposta.status_code == 200
    assert CHAVE_VALIDA not in resposta.text
    assert resposta.json()["status"] == "valid"
    assert resposta.json()["available"] is True
    set_cookie = resposta.headers["set-cookie"]
    assert set_cookie.startswith("ralph_llm_credential=")
    assert CHAVE_VALIDA not in set_cookie
    for atributo in ("HttpOnly", "Path=/v1", "SameSite=strict"):
        assert atributo.lower() in set_cookie.lower()
    assert validator.validated == [CHAVE_VALIDA]
    assert client.get(_ROTA).json()["status"] == "valid"


def test_cookie_seguro_em_producao(clock: ControllableClock) -> None:
    security = build_security(clock=clock, cookie_secure=True, public_origins=("https://ralph.test",))
    client = TestClient(create_app(security=security), base_url="https://testserver")
    headers = sign_in(client, security)
    headers["Origin"] = "https://ralph.test"

    resposta = client.put(_ROTA, json={"api_key": CHAVE_VALIDA}, headers=headers)

    assert resposta.headers["set-cookie"].startswith("__Secure-ralph_llm_credential=")
    assert "secure" in resposta.headers["set-cookie"].lower()


def test_escrita_exige_csrf_e_origem(client: TestClient, security: SecurityServices) -> None:
    headers = sign_in(client, security)

    sem_csrf = client.put(_ROTA, json={"api_key": CHAVE_VALIDA}, headers={"Origin": ORIGEM})
    csrf_errado = client.put(_ROTA, json={"api_key": CHAVE_VALIDA}, headers={**headers, "X-CSRF-Token": "x"})
    outra_origem = client.put(_ROTA, json={"api_key": CHAVE_VALIDA}, headers={**headers, "Origin": "https://mal"})

    assert sem_csrf.status_code == 403
    assert csrf_errado.status_code == 403
    assert outra_origem.status_code == 403
    assert "set-cookie" not in sem_csrf.headers


def test_chave_recusada_pela_openrouter(client: TestClient, security: SecurityServices) -> None:
    headers = sign_in(client, security)

    resposta = client.put(_ROTA, json={"api_key": "sk-or-v1-recusada-000"}, headers=headers)

    assert resposta.status_code == 422
    assert "sk-or-v1-recusada-000" not in resposta.text
    assert "set-cookie" not in resposta.headers


def test_validacao_indisponivel(client: TestClient, security: SecurityServices, validator: FakeKeyValidator) -> None:
    headers = sign_in(client, security)
    validator.unavailable = True

    resposta = client.put(_ROTA, json={"api_key": CHAVE_VALIDA}, headers=headers)

    assert resposta.status_code == 503


@pytest.mark.parametrize("corpo", [{}, {"api_key": 1}, {"api_key": "x" * 600}, [], "texto"])
def test_corpo_invalido_nao_ecoa_a_chave(client: TestClient, security: SecurityServices, corpo: object) -> None:
    headers = sign_in(client, security)

    resposta = client.put(_ROTA, content=json.dumps(corpo), headers={**headers, "Content-Type": "application/json"})

    assert resposta.status_code == 422
    assert "x" * 50 not in resposta.text


def test_substitui_e_remove_a_credencial(client: TestClient, security: SecurityServices) -> None:
    headers = sign_in(client, security)
    client.put(_ROTA, json={"api_key": CHAVE_VALIDA}, headers=headers)
    primeiro = client.cookies.get("ralph_llm_credential")

    client.put(_ROTA, json={"api_key": CHAVE_VALIDA_2}, headers=headers)
    assert client.cookies.get("ralph_llm_credential") != primeiro

    sem_csrf = client.delete(_ROTA, headers={"Origin": ORIGEM})
    removida = client.delete(_ROTA, headers=headers)

    assert sem_csrf.status_code == 403
    assert removida.status_code == 204
    assert 'ralph_llm_credential=""' in removida.headers["set-cookie"]
    assert client.get(_ROTA).json()["status"] == "missing"


def test_cookie_de_outra_conta_e_tratado_como_invalido(client: TestClient, security: SecurityServices) -> None:
    headers = sign_in(client, security, user_id="usr_ana")
    client.put(_ROTA, json={"api_key": CHAVE_VALIDA}, headers=headers)
    cookie_da_ana = client.cookies.get("ralph_llm_credential")

    sign_in(client, security, user_id="usr_bia")
    client.cookies.set("ralph_llm_credential", cookie_da_ana, path="/v1")
    resposta = client.get(_ROTA)

    assert resposta.json()["status"] == "invalid"
    assert 'ralph_llm_credential=""' in resposta.headers["set-cookie"]


def test_credencial_expira_com_a_sessao(
    client: TestClient, security: SecurityServices, clock: ControllableClock
) -> None:
    headers = sign_in(client, security)
    client.put(_ROTA, json={"api_key": CHAVE_VALIDA}, headers=headers)
    provider = security.identity_provider
    assert isinstance(provider, FakeIdentityProvider)

    clock.advance(hours=24)

    assert client.get(_ROTA).status_code == 401


def test_autenticacao_indisponivel_falha_fechado(client: TestClient, security: SecurityServices) -> None:
    sign_in(client, security)
    provider = security.identity_provider
    assert isinstance(provider, FakeIdentityProvider)
    provider.unavailable = True

    assert client.get(_ROTA).status_code == 503


def test_header_de_identidade_do_cliente_e_ignorado(client: TestClient) -> None:
    resposta = client.get(_ROTA, headers={"X-User-Id": "usr_ana", "X-Forwarded-User": "usr_ana"})

    assert resposta.status_code == 401


def test_corpo_que_nao_e_json(client: TestClient, security: SecurityServices) -> None:
    headers = sign_in(client, security)

    resposta = client.put(_ROTA, content=b"{nao-json", headers={**headers, "Content-Type": "application/json"})

    assert resposta.status_code == 422
