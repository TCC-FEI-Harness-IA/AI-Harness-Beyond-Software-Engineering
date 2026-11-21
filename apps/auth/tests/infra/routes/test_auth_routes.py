from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from tests.doubles.fakes import FakeClock
from tests.infra.routes.conftest import INTERNAL_TOKEN, ORIGEM

_SENHA = "senha muito boa 1"
_ORIGIN = {"Origin": ORIGEM}


def _cadastrar_e_entrar(client: TestClient, email: str = "ana@exemplo.com") -> dict:
    assert client.post("/auth/register", json={"email": email, "password": _SENHA}, headers=_ORIGIN).status_code == 201
    resposta = client.post("/auth/login", json={"email": email, "password": _SENHA}, headers=_ORIGIN)
    assert resposta.status_code == 200
    return resposta.json()


def _verificar(client: TestClient, token: str) -> object:
    return client.post(
        "/internal/sessions/verify", json={"token": token}, headers={"Authorization": f"Bearer {INTERNAL_TOKEN}"}
    )


def test_cadastro_devolve_usuario_sem_hash(make_client: Callable[..., TestClient]) -> None:
    client = make_client()

    resposta = client.post("/auth/register", json={"email": "Ana@Exemplo.com", "password": _SENHA}, headers=_ORIGIN)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["user"]["email"] == "ana@exemplo.com"
    assert corpo["user"]["role"] == "user"
    assert "password" not in resposta.text and "argon2" not in resposta.text
    assert "set-cookie" not in resposta.headers


def test_cadastro_nao_aceita_perfil_vindo_do_cliente(make_client: Callable[..., TestClient]) -> None:
    client = make_client()

    resposta = client.post(
        "/auth/register", json={"email": "ana@exemplo.com", "password": _SENHA, "role": "admin"}, headers=_ORIGIN
    )

    assert resposta.status_code == 201
    assert resposta.json()["user"]["role"] == "user"


def test_cadastro_duplicado_e_dados_invalidos(make_client: Callable[..., TestClient]) -> None:
    client = make_client()
    client.post("/auth/register", json={"email": "ana@exemplo.com", "password": _SENHA}, headers=_ORIGIN)

    duplicado = client.post("/auth/register", json={"email": "ANA@exemplo.com", "password": _SENHA}, headers=_ORIGIN)
    fraca = client.post("/auth/register", json={"email": "b@exemplo.com", "password": "curta"}, headers=_ORIGIN)
    malformado = client.post("/auth/register", json={"email": 1}, headers=_ORIGIN)

    assert duplicado.status_code == 409
    assert fraca.status_code == 400
    assert malformado.status_code == 422


def test_origem_nao_permitida_e_recusada(make_client: Callable[..., TestClient]) -> None:
    client = make_client()

    resposta = client.post(
        "/auth/register", json={"email": "ana@exemplo.com", "password": _SENHA}, headers={"Origin": "https://mal.com"}
    )
    login = client.post(
        "/auth/login", json={"email": "ana@exemplo.com", "password": _SENHA}, headers={"Origin": "https://mal.com"}
    )

    assert resposta.status_code == 403
    assert login.status_code == 403


def test_login_define_cookie_http_only_lax_de_24h(make_client: Callable[..., TestClient]) -> None:
    client = make_client()

    corpo = _cadastrar_e_entrar(client)

    cookie = client.cookies.get("ralph_session")
    assert cookie
    assert cookie not in str(corpo)
    assert corpo["user"]["email"] == "ana@exemplo.com"
    assert corpo["session"]["expires_at"].startswith("2099-01-02T12:00:00")
    assert corpo["csrf_token"]


def test_atributos_do_cookie_em_producao(make_client: Callable[..., TestClient]) -> None:
    client = make_client(secure=True)
    client.post("/auth/register", json={"email": "ana@exemplo.com", "password": _SENHA}, headers=_ORIGIN)

    resposta = client.post("/auth/login", json={"email": "ana@exemplo.com", "password": _SENHA}, headers=_ORIGIN)

    set_cookie = resposta.headers["set-cookie"]
    assert set_cookie.startswith("__Host-ralph_session=")
    for atributo in ("HttpOnly", "Secure", "SameSite=lax", "Path=/", "Max-Age=86400"):
        assert atributo.lower() in set_cookie.lower()
    assert "domain" not in set_cookie.lower()
    assert resposta.headers["cache-control"] == "no-store"


def test_login_invalido_e_limite_de_tentativas(make_client: Callable[..., TestClient]) -> None:
    client = make_client()
    client.post("/auth/register", json={"email": "ana@exemplo.com", "password": _SENHA}, headers=_ORIGIN)

    for _ in range(3):
        errado = client.post("/auth/login", json={"email": "ana@exemplo.com", "password": "errada 123456"})
        assert errado.status_code == 401
        assert errado.json()["detail"] == "E-mail ou senha inválidos."
    bloqueado = client.post("/auth/login", json={"email": "ana@exemplo.com", "password": _SENHA})

    assert bloqueado.status_code == 429
    assert int(bloqueado.headers["retry-after"]) > 0
    assert "ralph_session" not in client.cookies


def test_limite_por_cliente_usa_ip_do_proxy_quando_confiavel(make_client: Callable[..., TestClient]) -> None:
    client = make_client(trust_proxy=True)
    for indice in range(3):
        client.post(
            "/auth/login",
            json={"email": f"x{indice}@exemplo.com", "password": "errada 123456"},
            headers={"X-Real-IP": "203.0.113.7"},
        )

    corpo = {"email": "y@exemplo.com", "password": "errada 123456"}
    mesmo_ip = client.post("/auth/login", json=corpo, headers={"X-Real-IP": "203.0.113.7"})
    outro_ip = client.post("/auth/login", json=corpo, headers={"X-Real-IP": "203.0.113.8"})

    assert mesmo_ip.status_code == 429
    assert outro_ip.status_code == 401


def test_me_devolve_sessao_atual_e_csrf(make_client: Callable[..., TestClient]) -> None:
    client = make_client()
    login = _cadastrar_e_entrar(client)

    resposta = client.get("/auth/me")

    assert resposta.status_code == 200
    assert resposta.json() == login
    assert resposta.headers["cache-control"] == "no-store"


def test_me_sem_cookie_ou_expirado_devolve_401(make_client: Callable[..., TestClient], clock: FakeClock) -> None:
    client = make_client()
    assert client.get("/auth/me").status_code == 401

    _cadastrar_e_entrar(client)
    clock.advance(hours=24)

    assert client.get("/auth/me").status_code == 401


def test_logout_exige_csrf_e_revoga_inclusive_copia_antiga(make_client: Callable[..., TestClient]) -> None:
    client = make_client()
    login = _cadastrar_e_entrar(client)
    copia_do_cookie = client.cookies.get("ralph_session")

    sem_csrf = client.post("/auth/logout", headers=_ORIGIN)
    csrf_errado = client.post("/auth/logout", headers={**_ORIGIN, "X-CSRF-Token": "outro"})
    assert sem_csrf.status_code == 403
    assert csrf_errado.status_code == 403
    assert client.get("/auth/me").status_code == 200

    saida = client.post("/auth/logout", headers={**_ORIGIN, "X-CSRF-Token": login["csrf_token"]})

    assert saida.status_code == 204
    apagados = saida.headers.get_list("set-cookie")
    assert any(item.startswith('ralph_session=""') and "Max-Age=0" in item for item in apagados)
    assert any(item.startswith('ralph_llm_credential=""') and "Path=/v1" in item for item in apagados)
    client.cookies.set("ralph_session", copia_do_cookie)
    assert client.get("/auth/me").status_code == 401
    assert _verificar(client, copia_do_cookie).status_code == 401


def test_logout_sem_sessao_valida_apenas_limpa_cookies(make_client: Callable[..., TestClient]) -> None:
    client = make_client()

    resposta = client.post("/auth/logout")

    assert resposta.status_code == 204


def test_verificacao_interna_exige_token_de_servico(make_client: Callable[..., TestClient]) -> None:
    client = make_client()
    _cadastrar_e_entrar(client)
    token = client.cookies.get("ralph_session")

    sem = client.post("/internal/sessions/verify", json={"token": token})
    errado = client.post(
        "/internal/sessions/verify", json={"token": token}, headers={"Authorization": "Bearer errado"}
    )
    certo = _verificar(client, token)

    assert sem.status_code == 401
    assert errado.status_code == 401
    assert certo.status_code == 200
    corpo = certo.json()
    assert corpo["user_id"].startswith("usr_")
    assert corpo["role"] == "user"
    assert corpo["session_id"].startswith("ses_")
    assert corpo["expires_at"].startswith("2099-01-02T12:00:00")
    assert corpo["csrf_token"]
    assert "email" not in corpo
    assert _verificar(client, "token-falso").status_code == 401


def test_sessao_persiste_apos_reinicio_do_servico(
    make_client: Callable[..., TestClient], mongo: AsyncMongoMockClient
) -> None:
    client = make_client()
    _cadastrar_e_entrar(client)
    token = client.cookies.get("ralph_session")

    reiniciado = make_client()

    assert _verificar(reiniciado, token).status_code == 200


def test_health(make_client: Callable[..., TestClient]) -> None:
    assert make_client().get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/auth/login", "/auth/register"])
@pytest.mark.parametrize(
    "password", ["segredo-ficticio-" * 80, {"secret": "senha-ficticia"}], ids=["senha-longa", "tipo-invalido"]
)
def test_validacao_nao_devolve_senha_nem_contexto_sensivel(
    make_client: Callable[..., TestClient], path: str, password: object,
) -> None:
    response = make_client().post(path, json={"email": "ana@exemplo.com", "password": password})

    assert response.status_code == 422
    assert "segredo-ficticio" not in response.text
    assert "senha-ficticia" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert all(set(error) == {"loc", "msg", "type"} for error in response.json()["detail"])


def test_json_invalido_nao_devolve_corpo_e_nao_pode_ser_cacheado(make_client: Callable[..., TestClient]) -> None:
    response = make_client().post(
        "/auth/login", content='{"password": "segredo-ficticio",', headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert "segredo-ficticio" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert all(set(error) == {"loc", "msg", "type"} for error in response.json()["detail"])
