"""Teste de integração ponta a ponta pelo proxy de produção, com OpenRouter falsa.

Sobe `integration/docker-compose.integration.yml` (Nginx com TLS, auth, backend, MongoDB e a
OpenRouter falsa), verifica cookies, CSRF, WebSockets, isolamento, revogação, limites,
persistência após reinício e ausência de segredos nos logs, e derruba tudo ao final.

Uso (com o venv do backend, que já tem httpx e websockets):
    apps/backend/.venv/bin/python integration/run_integration.py
"""
import asyncio
import base64
import json
import re
import secrets
import ssl
import subprocess
import sys
import time
from pathlib import Path

import httpx
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

ROOT = Path(__file__).resolve().parent
COMPOSE = ["docker", "compose", "-f", str(ROOT / "docker-compose.integration.yml")]
BASE = "https://localhost:18443"
WSS = "wss://localhost:18443"
ORIGIN = BASE
FAKE = "http://localhost:19000"
KEY_ANA = "sk-or-v1-integracao-ana"
KEY_BIA = "sk-or-v1-integracao-bia"
PASSWORD = "senha de integracao 123"
MODEL = {"provider": "open_router", "provider_config": {"model_name": "fake/model"}, "max_tokens": 20000,
         "temperature": 0.3}
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))
    print(f"[{'OK' if condition else 'FALHOU'}] {name}{f' — {detail}' if detail and not condition else ''}")


def prepare() -> None:
    (ROOT / "secrets").mkdir(exist_ok=True)
    (ROOT / "secrets" / "auth_internal_token").write_text(secrets.token_urlsafe(48))
    (ROOT / "secrets" / "llm_credential_encryption_key").write_text(
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    )
    (ROOT / "certs").mkdir(exist_ok=True)
    subprocess.run(
        ["openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048", "-days", "1",
         "-keyout", str(ROOT / "certs" / "privkey.pem"), "-out", str(ROOT / "certs" / "fullchain.pem"),
         "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost"],
        check=True, capture_output=True,
    )
    for path in [*(ROOT / "secrets").iterdir(), *(ROOT / "certs").iterdir()]:
        path.chmod(0o644)


def wait_ready(client: httpx.Client) -> None:
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            if client.get("/v1/health").status_code == 200 and client.get("/auth/me").status_code == 401:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise RuntimeError("a pilha não ficou pronta a tempo")


def new_client() -> httpx.Client:
    return httpx.Client(base_url=BASE, verify=str(ROOT / "certs" / "fullchain.pem"), timeout=30,
                        headers={"Origin": ORIGIN})


def cookie_header(client: httpx.Client) -> str:
    return "; ".join(f"{cookie.name}={cookie.value}" for cookie in client.cookies.jar)


def sign_up(client: httpx.Client, email: str) -> dict:
    client.post("/auth/register", json={"email": email, "password": PASSWORD})
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    response.raise_for_status()
    return response.json()


async def reasoning(client: httpx.Client, origin: str = ORIGIN,
                    during_run=None) -> tuple[list[dict], int | None]:
    """Executa o Ralph por WSS com os cookies do cliente; `during_run` roda enquanto a 1ª chamada LLM está em curso."""
    context = ssl.create_default_context(cafile=str(ROOT / "certs" / "fullchain.pem"))
    frames: list[dict] = []
    async with connect(f"{WSS}/v1/message/reasoning", ssl=context, origin=origin, proxy=None,
                       additional_headers={"Cookie": cookie_header(client)}) as ws:
        try:
            await ws.send(json.dumps({"message": {"user_input": "Quanto é 2 + 2?"}, "llm_model_config": MODEL}))
            if during_run is not None:
                await asyncio.sleep(0.7)
                await asyncio.to_thread(during_run)
            async for raw in ws:
                frames.append(json.loads(raw))
        except ConnectionClosed:
            pass
        return frames, ws.close_code


def raw_cookies(**cookies: str) -> dict[str, str]:
    """Header `Cookie` explícito (o cookiejar não reenvia cookies criados à mão para `localhost`)."""
    return {"Cookie": "; ".join(f"{name}={value}" for name, value in cookies.items())}


def scenario() -> None:  # noqa: C901 — roteiro linear de verificações
    ana, bia, visitor = new_client(), new_client(), new_client()
    wait_ready(visitor)
    fake = httpx.Client(base_url=FAKE, timeout=10)

    page = visitor.get("/")
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', page.text)
    check("HTML referencia o bundle de produção", page.status_code == 200 and bool(assets))
    for path in ["/", "/entrar", *assets[:1]]:
        response = visitor.get(path)
        headers = response.headers
        check(f"headers de segurança em {path}", response.status_code == 200 and all((
            headers.get("strict-transport-security", "").startswith("max-age="),
            headers.get("x-content-type-options") == "nosniff",
            headers.get("x-frame-options") == "DENY",
            headers.get("referrer-policy") == "same-origin",
            "default-src 'self'" in headers.get("content-security-policy", ""),
        )))
        check(f"cache estático adequado em {path}",
              "immutable" in headers.get("cache-control", "") if path.startswith("/assets/")
              else headers.get("cache-control") == "no-cache")

    for path in ("/auth/login", "/auth/register"):
        invalid = visitor.post(path, json={"email": "erro@exemplo.com", "password": "senha-ficticia-" * 100})
        check(f"validação sem senha nem cache em {path}",
              invalid.status_code == 422 and "senha-ficticia" not in invalid.text
              and invalid.headers.get("cache-control") == "no-store")

    public = visitor.get("/v1/public/benchmarks")
    check("consulta pública sem login", public.status_code == 200 and public.json() == {"publications": []})
    check("consulta pública cacheável", public.headers.get("cache-control") == "public, max-age=60")
    check("rota interna do auth não é exposta pelo proxy",
          visitor.post("/internal/sessions/verify", json={"token": "x"}).status_code == 404)
    check("visitante não executa chamada LLM",
          visitor.post("/v1/message/default", json={"message": {"user_input": "oi"}, "llm_model_config": MODEL}
                       ).status_code == 401)
    check("visitante não lê histórico privado", visitor.get("/v1/sessions").status_code == 401)
    frames, code = asyncio.run(reasoning(visitor))
    check("WebSocket sem sessão fecha com 4401", code == 4401, f"code={code}")

    login = ana.post("/auth/register", json={"email": "ana@exemplo.com", "password": PASSWORD})
    check("cadastro", login.status_code == 201)
    response = ana.post("/auth/login", json={"email": "ana@exemplo.com", "password": PASSWORD})
    set_cookie = response.headers.get("set-cookie", "")
    check("login define cookie __Host- HttpOnly Secure SameSite=Lax",
          set_cookie.startswith("__Host-ralph_session=") and all(
              item in set_cookie.lower() for item in ("httponly", "secure", "samesite=lax", "path=/")),
          set_cookie[:80])
    csrf = response.json()["csrf_token"]
    session_cookie = ana.cookies.get("__Host-ralph_session")

    bad = ana.put("/v1/credentials/openrouter", json={"api_key": "sk-or-v1-chave-errada"},
                  headers={"X-CSRF-Token": csrf})
    check("chave recusada pela OpenRouter falsa", bad.status_code == 422 and "sk-or-v1-chave-errada" not in bad.text)
    no_csrf = ana.put("/v1/credentials/openrouter", json={"api_key": KEY_ANA})
    check("escrita sem token anti-CSRF é recusada", no_csrf.status_code == 403)
    good = ana.put("/v1/credentials/openrouter", json={"api_key": KEY_ANA}, headers={"X-CSRF-Token": csrf})
    credential_cookie = good.headers.get("set-cookie", "")
    check("credencial aceita, sem a chave na resposta", good.status_code == 200 and KEY_ANA not in good.text)
    check("cookie da credencial __Secure- HttpOnly Secure Strict em /v1",
          credential_cookie.startswith("__Secure-ralph_llm_credential=") and KEY_ANA not in credential_cookie
          and all(item in credential_cookie.lower() for item in ("httponly", "secure", "samesite=strict", "path=/v1")),
          credential_cookie[:80])
    check("respostas privadas não são cacheáveis", good.headers.get("cache-control") == "no-store, private")

    simple = ana.post("/v1/message/default", json={"message": {"user_input": "Quanto é 2 + 2?"},
                                                   "llm_model_config": MODEL}, headers={"X-CSRF-Token": csrf})
    check("inferência simples com a chave da sessão", simple.status_code == 200, simple.text[:200])
    calls = fake.get("/__calls").json()["keys"]
    check("OpenRouter recebeu a chave do usuário", calls == [KEY_ANA], str(calls))
    session_id = simple.json().get("session_id") if simple.status_code == 200 else None

    try:
        asyncio.run(reasoning(ana, origin="https://site-malicioso.exemplo"))
        check("WebSocket de origem não permitida é recusado", False, "conexão aceita")
    except InvalidStatus as exc:
        check("WebSocket de origem não permitida é recusado", exc.response.status_code == 403)

    frames, code = asyncio.run(reasoning(ana))
    check("WebSocket do Ralph com cookies pelo proxy (WSS)", len(frames) > 0 and code in (1000, 1011), f"code={code}")
    check("Ralph chamou a OpenRouter falsa com a chave da Ana",
          set(fake.get("/__calls").json()["keys"]) == {KEY_ANA})

    sign_up(bia, "bia@exemplo.com")
    bia_csrf = bia.get("/auth/me").json()["csrf_token"]
    bia.put("/v1/credentials/openrouter", json={"api_key": KEY_BIA}, headers={"X-CSRF-Token": bia_csrf})
    check("outra conta não lista nem lê a sessão da Ana",
          bia.get("/v1/sessions").json() == {"session_ids": []}
          and bia.get(f"/v1/sessions/{session_id}").status_code == 404)
    mixed = new_client().post(
        "/v1/message/default", json={"message": {"user_input": "x"}, "llm_model_config": MODEL},
        headers={"X-CSRF-Token": bia_csrf, **raw_cookies(**{
            "__Host-ralph_session": bia.cookies.get("__Host-ralph_session"),
            "__Secure-ralph_llm_credential": ana.cookies.get("__Secure-ralph_llm_credential"),
        })},
    )
    check("credencial de outra conta não serve na sessão da Bia", mixed.status_code == 428, str(mixed.status_code))

    def logout_ana() -> None:
        ana.post("/auth/logout", headers={"X-CSRF-Token": csrf})

    calls_before = len(fake.get("/__calls").json()["keys"])
    frames, code = asyncio.run(reasoning(ana, during_run=logout_ana))
    check("logout durante a execução interrompe o WebSocket (4401)", code == 4401, f"code={code}")
    time.sleep(3)
    calls_after = len(fake.get("/__calls").json()["keys"])
    check("nenhuma chamada LLM nova depois da revogação", calls_after - calls_before <= 1,
          f"{calls_after - calls_before} chamadas")
    replay = new_client()
    old = raw_cookies(**{"__Host-ralph_session": session_cookie})
    check("cópia antiga do cookie continua recusada após o logout",
          replay.get("/auth/me", headers=old).status_code == 401
          and replay.get("/v1/sessions", headers=old).status_code == 401)
    valid_before_logout = new_client().get("/auth/me", headers=raw_cookies(**{
        "__Host-ralph_session": bia.cookies.get("__Host-ralph_session")}))
    check("o header de cookie explícito funciona (controle do teste)", valid_before_logout.status_code == 200)

    for _ in range(3):
        visitor.post("/auth/login", json={"email": "bia@exemplo.com", "password": "senha errada 0000"})
    blocked = visitor.post("/auth/login", json={"email": "bia@exemplo.com", "password": PASSWORD})
    check("limite de tentativas de login", blocked.status_code == 429 and "retry-after" in blocked.headers)

    subprocess.run([*COMPOSE, "restart", "auth", "backend"], check=True, capture_output=True)
    wait_ready(visitor)
    check("sessão e credencial persistem após reiniciar os containers",
          bia.get("/auth/me").status_code == 200
          and bia.get("/v1/credentials/openrouter").json().get("status") == "valid")

    logs = subprocess.run([*COMPOSE, "logs", "--no-color"], capture_output=True, text=True).stdout
    secrets_found = [item for item in (KEY_ANA, KEY_BIA, session_cookie, PASSWORD) if item and item in logs]
    check("logs sem chaves, cookies ou senhas", secrets_found == [], f"{len(secrets_found)} segredo(s)")


def main() -> int:
    prepare()
    subprocess.run([*COMPOSE, "up", "-d", "--build"], check=True)
    try:
        scenario()
    finally:
        subprocess.run([*COMPOSE, "down", "-v"], capture_output=True)
    failures = [name for name, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failures)}/{len(RESULTS)} verificações aprovadas")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
