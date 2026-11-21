"""Autorização das rotas de benchmark: consultas privadas, importação, WebSockets e ciclo de vida."""
import asyncio
from typing import Any, AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.infra.routes.v1.benchmark import router as benchmark_router_module
from src.infra.routes.v1.benchmark.dtos.benchmark_frame_dto import BenchmarkFrameDTO
from src.main import create_app
from tests.doubles.security_doubles import ORIGEM, FakeIdentityProvider, authenticated_client, build_security


class _StartupQuePendura:
    """Startup de execução/reexecução que emite um frame e fica ocupado até ser cancelado."""

    instancias: list["_StartupQuePendura"] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.fechado = False
        _StartupQuePendura.instancias.append(self)

    async def _frames(self) -> AsyncGenerator[BenchmarkFrameDTO, None]:
        try:
            yield BenchmarkFrameDTO(type="progress", benchmark_session={"id": "bench_1", "status": "running"})
            await asyncio.sleep(30)
        finally:
            self.fechado = True

    def run(self, **_: Any) -> AsyncGenerator[BenchmarkFrameDTO, None]:
        return self._frames()

    def run_many(self, **_: Any) -> AsyncGenerator[BenchmarkFrameDTO, None]:
        return self._frames()


@pytest.fixture(autouse=True)
def startups(monkeypatch: pytest.MonkeyPatch) -> None:
    _StartupQuePendura.instancias = []
    monkeypatch.setattr(benchmark_router_module, "BenchmarkRunStartup", _StartupQuePendura)
    monkeypatch.setattr(benchmark_router_module, "BenchmarkRerunStartup", _StartupQuePendura)


def _coletar(ws: Any) -> tuple[list[dict], int]:
    frames = []
    try:
        while True:
            frames.append(ws.receive_json())
    except WebSocketDisconnect as exc:
        return frames, exc.code


@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [
        ("get", "/v1/benchmark/sessions"),
        ("get", "/v1/benchmark/sessions/bench_1"),
        ("get", "/v1/benchmark/sessions/bench_1/export"),
        ("get", "/v1/benchmark/sessions/bench_1/ralph-loop-errors/export"),
        ("post", "/v1/benchmark/sessions/import"),
        ("put", "/v1/benchmark/sessions/bench_1/alias"),
    ],
)
def test_visitante_nao_acessa_baterias_pessoais(metodo: str, caminho: str) -> None:
    visitante = TestClient(create_app(security=build_security()))

    extras = {"json": {}} if metodo == "put" else {}
    resposta = getattr(visitante, metodo)(caminho, headers={"Origin": ORIGEM}, **extras)

    assert resposta.status_code == 401


def test_importacao_exige_csrf() -> None:
    cliente = authenticated_client(with_credential=False)
    del cliente.headers["X-CSRF-Token"]

    resposta = cliente.post("/v1/benchmark/sessions/import", content=b"PK", headers={"Content-Type": "application/zip"})

    assert resposta.status_code == 403


@pytest.mark.parametrize(
    "caminho",
    [
        "/v1/benchmark/run",
        "/v1/benchmark/sessions/bench_1/questions/Q1/rerun",
        "/v1/benchmark/sessions/bench_1/questions/rerun",
    ],
)
def test_websockets_de_benchmark_recusam_visitante(caminho: str) -> None:
    visitante = TestClient(create_app(security=build_security()))

    with visitante.websocket_connect(caminho, headers={"Origin": ORIGEM}) as ws:
        _, codigo = _coletar(ws)

    assert codigo == 4401
    assert _StartupQuePendura.instancias == []


@pytest.mark.parametrize(
    ("caminho", "abertura"),
    [
        ("/v1/benchmark/run", {
            "question_count": 1, "max_parallel": 1,
            "llm_model_config": {"provider": "open_router", "provider_config": {"model_name": "v/m"},
                                 "max_tokens": 1000, "temperature": 0.3},
        }),
        ("/v1/benchmark/sessions/bench_1/questions/Q1/rerun", None),
        ("/v1/benchmark/sessions/bench_1/questions/rerun", {"question_ids": ["Q1"]}),
    ],
)
def test_logout_durante_a_bateria_interrompe_e_bloqueia_novas_chamadas(caminho: str, abertura: Any) -> None:
    cliente = authenticated_client(user_id="usr_ana")
    provider = cliente.security.identity_provider  # type: ignore[attr-defined]
    assert isinstance(provider, FakeIdentityProvider)

    with cliente.websocket_connect(caminho) as ws:
        if abertura is not None:
            ws.send_json(abertura)
        assert ws.receive_json()["type"] == "progress"
        provider.revoke(cliente.cookies.get("ralph_session"))
        frames, codigo = _coletar(ws)

    assert codigo == 4401
    assert frames[-1]["type"] == "error"
    startup = _StartupQuePendura.instancias[0]
    assert startup.fechado is True
    assert startup.kwargs["owner_id"] == "usr_ana"
    assert startup.kwargs["authorization"].is_active is False
