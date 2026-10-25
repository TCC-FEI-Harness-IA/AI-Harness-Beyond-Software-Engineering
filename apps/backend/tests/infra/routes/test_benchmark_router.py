import asyncio
import json
from typing import Any, AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect, WebSocketState

from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.errors.invalid_benchmark_request_error import InvalidBenchmarkRequestError
from src.domain.errors.no_benchmark_errors_to_export_error import NoBenchmarkErrorsToExportError
from src.infra.routes.v1.benchmark import router as benchmark_router_module
from src.infra.routes.v1.benchmark.dtos.benchmark_frame_dto import BenchmarkFrameDTO
from src.infra.routes.v1.benchmark.router import run_benchmark
from src.infra.services.benchmark_ralph_errors_archive_builder import BenchmarkArchive
from src.main import create_app


def _frame(tipo: str = "progress", status: str = "running") -> BenchmarkFrameDTO:
    return BenchmarkFrameDTO(type=tipo, benchmark_session={"id": "bench_1", "status": status})


class _FakeRunStartup:
    """Dublê do startup de execução, para isolar a rota do caso de uso."""

    frames: list[BenchmarkFrameDTO] = []
    error: BaseException | None = None
    construction_error: Exception | None = None
    payloads: list[Any] = []
    closed = 0

    def __init__(self) -> None:
        if _FakeRunStartup.construction_error is not None:
            raise _FakeRunStartup.construction_error

    async def run(self, payload: Any) -> AsyncGenerator[BenchmarkFrameDTO, None]:
        _FakeRunStartup.payloads.append(payload)
        try:
            for frame in _FakeRunStartup.frames:
                yield frame
            if _FakeRunStartup.error is not None:
                raise _FakeRunStartup.error
        finally:
            _FakeRunStartup.closed += 1


class _FakeQueryStartup:
    """Dublê do startup de consultas, com respostas e falhas programáveis."""

    error: Exception | None = None

    def __init__(self) -> None:
        if _FakeQueryStartup.error is not None:
            raise _FakeQueryStartup.error

    def describe_dataset(self) -> dict[str, Any]:
        return {"question_ids": ["Q1"], "max_parallel_limit": 10}

    async def list_benchmark_session_documents(self) -> list[dict[str, Any]]:
        return [{"id": "bench_1"}]

    async def get_benchmark_session_document(self, benchmark_session_id: str) -> dict[str, Any]:
        return {"id": benchmark_session_id}


class _QueryStartupQueLevanta(_FakeQueryStartup):
    """Consulta de bateria que levanta o erro programado."""

    lookup_error: Exception = RuntimeError()

    async def get_benchmark_session_document(self, benchmark_session_id: str) -> dict[str, Any]:
        raise _QueryStartupQueLevanta.lookup_error


class _FakeExportStartup:
    """Dublê do startup de exportação, com arquivo e falha programáveis."""

    error: Exception | None = None
    requested: list[str] = []

    async def export_ralph_errors(self, benchmark_session_id: str) -> BenchmarkArchive:
        _FakeExportStartup.requested.append(benchmark_session_id)
        if _FakeExportStartup.error is not None:
            raise _FakeExportStartup.error
        return BenchmarkArchive(
            filename=f"benchmark-session-{benchmark_session_id}-ralph-loop-errors.zip", content=b"PK-zip"
        )


def _abertura(**sobrescritas: Any) -> dict[str, Any]:
    corpo: dict[str, Any] = {
        "question_count": 3,
        "max_parallel": 2,
        "llm_model_config": {
            "provider": "open_router",
            "provider_config": {"model_name": "vendor/modelo"},
            "max_tokens": 1200,
            "temperature": 0.3,
        },
    }
    corpo.update(sobrescritas)
    return corpo


def _coletar(ws: WebSocketTestSession) -> tuple[list[dict], int | None]:
    frames = []
    try:
        while True:
            frames.append(ws.receive_json())
    except WebSocketDisconnect as exc:
        return frames, exc.code


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Cliente com os startups de benchmark substituídos por dublês."""
    _FakeRunStartup.frames = []
    _FakeRunStartup.error = None
    _FakeRunStartup.construction_error = None
    _FakeRunStartup.payloads = []
    _FakeRunStartup.closed = 0
    _FakeQueryStartup.error = None
    monkeypatch.setattr(benchmark_router_module, "BenchmarkRunStartup", _FakeRunStartup)
    monkeypatch.setattr(benchmark_router_module, "BenchmarkQueryStartup", _FakeQueryStartup)
    return TestClient(create_app())


# ── Consultas ────────────────────────────────────────────────────────────────


def test_consultas_delegam_ao_startup(client: TestClient) -> None:
    assert client.get("/v1/benchmark/questions").json() == {"question_ids": ["Q1"], "max_parallel_limit": 10}
    assert client.get("/v1/benchmark/sessions").json() == {"benchmark_sessions": [{"id": "bench_1"}]}
    assert client.get("/v1/benchmark/sessions/bench_7").json() == {"id": "bench_7"}


@pytest.mark.parametrize("caminho", ["/v1/benchmark/questions", "/v1/benchmark/sessions", "/v1/benchmark/sessions/x"])
def test_falha_inesperada_nas_consultas_vira_500(client: TestClient, caminho: str) -> None:
    _FakeQueryStartup.error = RuntimeError("disco fora do ar")

    resposta = client.get(caminho)

    assert resposta.status_code == 500
    assert resposta.json()["detail"] == "disco fora do ar"


@pytest.mark.parametrize(
    ("erro", "status"),
    [(BenchmarkSessionNotFoundError("bench_9"), 404), (ValueError("identificador inválido"), 400)],
)
def test_erros_conhecidos_da_consulta_viram_404_e_400(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, erro: Exception, status: int
) -> None:
    _QueryStartupQueLevanta.lookup_error = erro
    monkeypatch.setattr(benchmark_router_module, "BenchmarkQueryStartup", _QueryStartupQueLevanta)

    resposta = client.get("/v1/benchmark/sessions/bench_9")

    assert resposta.status_code == status
    assert resposta.json()["detail"] == str(erro)


# ── Exportação ───────────────────────────────────────────────────────────────


@pytest.fixture
def exportacao(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _FakeExportStartup.error = None
    _FakeExportStartup.requested = []
    monkeypatch.setattr(benchmark_router_module, "BenchmarkExportStartup", _FakeExportStartup)
    return client


def test_exportacao_devolve_o_zip_como_anexo(exportacao: TestClient) -> None:
    resposta = exportacao.get("/v1/benchmark/sessions/bench_7/ralph-loop-errors/export")

    assert resposta.status_code == 200
    assert resposta.content == b"PK-zip"
    assert resposta.headers["content-type"] == "application/zip"
    assert resposta.headers["content-disposition"] == (
        'attachment; filename="benchmark-session-bench_7-ralph-loop-errors.zip"'
    )
    assert _FakeExportStartup.requested == ["bench_7"]


@pytest.mark.parametrize(
    ("erro", "status"),
    [
        (BenchmarkSessionNotFoundError("bench_9"), 404),
        (BenchmarkSessionNotFinishedError("bench_9"), 409),
        (NoBenchmarkErrorsToExportError("bench_9"), 409),
        (ValueError("identificador inválido"), 400),
        (RuntimeError("disco fora do ar"), 500),
    ],
)
def test_falhas_da_exportacao_viram_o_status_http_correspondente(
    exportacao: TestClient, erro: Exception, status: int
) -> None:
    _FakeExportStartup.error = erro

    resposta = exportacao.get("/v1/benchmark/sessions/bench_9/ralph-loop-errors/export")

    assert resposta.status_code == status
    assert resposta.json()["detail"] == str(erro)


# ── WebSocket ────────────────────────────────────────────────────────────────


def test_bateria_concluida_envia_os_frames_e_fecha_com_1000(client: TestClient) -> None:
    _FakeRunStartup.frames = [_frame(), _frame(), _frame("result", "completed")]

    with client.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json(_abertura())
        frames, codigo = _coletar(ws)

    assert [frame["type"] for frame in frames] == ["progress", "progress", "result"]
    assert codigo == 1000
    payload = _FakeRunStartup.payloads[0]
    assert (payload.question_count, payload.max_parallel) == (3, 2)


def test_abertura_sem_quantidade_e_paralelismo_usa_os_defaults(client: TestClient) -> None:
    _FakeRunStartup.frames = [_frame("result", "completed")]
    abertura = _abertura()
    del abertura["question_count"], abertura["max_parallel"]

    with client.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json(abertura)
        _coletar(ws)

    payload = _FakeRunStartup.payloads[0]
    assert (payload.question_count, payload.max_parallel) == (None, 5)


@pytest.mark.parametrize("status", ["failed", "interrupted"])
def test_bateria_que_nao_conclui_fecha_com_1011(client: TestClient, status: str) -> None:
    _FakeRunStartup.frames = [_frame(), _frame("result", status)]

    with client.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json(_abertura())
        frames, codigo = _coletar(ws)

    assert frames[-1]["benchmark_session"]["status"] == status
    assert codigo == 1011


@pytest.mark.parametrize("sobrescrita", [{"question_count": 0}, {"max_parallel": 0}, {"llm_model_config": None}])
def test_abertura_fora_do_contrato_gera_erro_e_fecha_com_1003(client: TestClient, sobrescrita: dict) -> None:
    with client.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json(_abertura(**sobrescrita))
        frames, codigo = _coletar(ws)

    assert frames[0]["type"] == "error"
    assert codigo == 1003
    assert _FakeRunStartup.payloads == []


def test_pedido_recusado_pelo_caso_de_uso_gera_erro_e_fecha_com_1003(client: TestClient) -> None:
    _FakeRunStartup.error = InvalidBenchmarkRequestError("question_count deve estar entre 1 e 15. Valor: 20.")

    with client.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json(_abertura())
        frames, codigo = _coletar(ws)

    assert frames == [{"type": "error", "content": "question_count deve estar entre 1 e 15. Valor: 20."}]
    assert codigo == 1003


def test_frame_acima_do_tamanho_maximo_fecha_com_1009(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RALPH_WEBSOCKET_MAX_MESSAGE_BYTES", "10")

    with client.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json(_abertura())
        frames, codigo = _coletar(ws)

    assert frames == []
    assert codigo == 1009


def test_falha_inesperada_gera_frame_de_erro_fecha_com_1011_e_encerra_o_gerador(client: TestClient) -> None:
    _FakeRunStartup.frames = [_frame()]
    _FakeRunStartup.error = RuntimeError("quebrou")

    with client.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json(_abertura())
        frames, codigo = _coletar(ws)

    assert frames[-1] == {"type": "error", "content": "quebrou"}
    assert codigo == 1011
    assert _FakeRunStartup.closed == 1


def test_falha_ao_montar_o_startup_gera_frame_de_erro(client: TestClient) -> None:
    _FakeRunStartup.construction_error = ValueError("configuração inválida")

    with client.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json(_abertura())
        frames, codigo = _coletar(ws)

    assert frames == [{"type": "error", "content": "configuração inválida"}]
    assert codigo == 1011


def test_cliente_desconectado_encerra_o_gerador_sem_derrubar_o_servidor(client: TestClient) -> None:
    _FakeRunStartup.frames = [_frame()]
    _FakeRunStartup.error = WebSocketDisconnect(code=1001)

    with client.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json(_abertura())
        ws.receive_json()

    assert _FakeRunStartup.closed == 1


class _SocketDesconectado:
    """Dublê de baixo nível: socket que a camada ASGI já marcou como desconectado."""

    def __init__(self, raw_text: str) -> None:
        self.raw_text = raw_text
        self.client_state = WebSocketState.DISCONNECTED
        self.sent: list[dict[str, Any]] = []

    async def accept(self) -> None:
        pass

    async def receive_text(self) -> str:
        return self.raw_text

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)

    async def close(self, code: int) -> None:
        raise AssertionError("não deveria fechar um socket desconectado")


def test_falha_inesperada_nao_envia_frame_quando_o_socket_ja_esta_desconectado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeRunStartup.frames = []
    _FakeRunStartup.error = RuntimeError("quebrou")
    _FakeRunStartup.construction_error = None
    monkeypatch.setattr(benchmark_router_module, "BenchmarkRunStartup", _FakeRunStartup)
    websocket = _SocketDesconectado(raw_text=json.dumps(_abertura()))

    asyncio.run(run_benchmark(websocket))

    assert websocket.sent == []
