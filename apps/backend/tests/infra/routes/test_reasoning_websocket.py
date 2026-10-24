import asyncio
import json
from types import SimpleNamespace
from typing import Any, AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect, WebSocketState

from src.domain.enums.session_status_enum import SessionStatusEnum
from src.infra.routes.v1.message import router as message_router_module
from src.infra.routes.v1.message.dtos.context_window_dto import ContextWindowDTO
from src.infra.routes.v1.message.dtos.reasoning_event_dto import ReasoningEventDTO
from src.infra.routes.v1.message.router import reasoning
from src.main import create_app

_CONTRATO_CAMPOS = {
    "type",
    "subtype",
    "phase",
    "task",
    "session_id",
    "content",
    "total_tokens",
    "context_window",
    "inference_time_ms",
}


def _event(session_id: str = "sess_ws1", **overrides: Any) -> ReasoningEventDTO:
    base: dict[str, Any] = {
        "type": "thinking",
        "subtype": "execute",
        "phase": "B1",
        "task": "T1",
        "session_id": session_id,
        "content": "conteudo",
        "total_tokens": 10,
        "context_window": ContextWindowDTO(context_id="ctx-1", context_size=5),
        "inference_time_ms": 100,
    }
    base.update(overrides)
    return ReasoningEventDTO(**base)


class _FakeSessionRecorder:
    """Dublê mínimo, só para provar que a rota finaliza a sessão em falha — e só uma vez."""

    status = SessionStatusEnum.RUNNING

    def __init__(self) -> None:
        self.finished_with: SessionStatusEnum | None = None
        self.finish_calls = 0

    @property
    def session(self) -> Any:
        """Sessão em andamento, de que a rota só consulta o estado."""
        return SimpleNamespace(status=type(self).status)

    async def finish(self, status: SessionStatusEnum, final_answer: str | None) -> None:
        self.finished_with = status
        self.finish_calls += 1


class _FakeStartup:
    """Dublê do startup do fluxo harness, para isolar a rota do use case real."""

    events: list[ReasoningEventDTO] = []
    error: Exception | None = None
    instances: list["_FakeStartup"] = []

    def __init__(self) -> None:
        self.session_recorder = _FakeSessionRecorder()
        _FakeStartup.instances.append(self)

    async def run(self, payload: Any) -> AsyncGenerator[ReasoningEventDTO, None]:
        for event in _FakeStartup.events:
            yield event
        if _FakeStartup.error is not None:
            raise _FakeStartup.error


def _build_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "message": {"user_input": "pergunta do usuario"},
        "llm_model_config": {
            "provider": "open_router",
            "provider_config": {"model_name": "vendor/modelo"},
            "max_tokens": 1200,
            "temperature": 0.3,
        },
    }
    payload.update(overrides)
    return payload


def _collect_frames(ws: WebSocketTestSession) -> tuple[list[dict], int | None]:
    """Lê frames até o servidor fechar, devolvendo os frames e o código de fechamento."""
    frames = []
    try:
        while True:
            frames.append(ws.receive_json())
    except WebSocketDisconnect as exc:
        return frames, exc.code


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Cliente HTTP com o startup do fluxo harness substituído por dublê."""
    _FakeStartup.events = []
    _FakeStartup.error = None
    _FakeStartup.instances = []
    _FakeSessionRecorder.status = SessionStatusEnum.RUNNING
    monkeypatch.setattr(message_router_module, "RalphThinkingStartup", _FakeStartup)
    return TestClient(create_app())


def test_fluxo_completo_recebe_a_sequencia_de_eventos_e_termina_em_result(client: TestClient) -> None:
    _FakeStartup.events = [
        _event(subtype="setup", task="setup"),
        _event(subtype="tasks", task="setup"),
        _event(type="result", subtype="compile", task="synthesis", content="resposta final"),
    ]

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_text('{"message": {"user_input": "pergunta"}, "llm_model_config": '
                     '{"provider": "open_router", "provider_config": {"model_name": "vendor/modelo"}, '
                     '"max_tokens": 1200, "temperature": 0.3}}')
        frames, close_code = _collect_frames(ws)

    assert [frame["type"] for frame in frames] == ["thinking", "thinking", "result"]
    assert frames[-1]["content"] == "resposta final"
    assert close_code == 1000


def test_todo_evento_tem_exatamente_os_nove_campos_do_contrato(client: TestClient) -> None:
    _FakeStartup.events = [_event()]

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(_build_payload())
        frames, _ = _collect_frames(ws)

    assert set(frames[0].keys()) == _CONTRATO_CAMPOS
    assert set(frames[0]["context_window"].keys()) == {"context_id", "context_size"}


def test_total_tokens_nao_decresce_ao_longo_dos_frames(client: TestClient) -> None:
    _FakeStartup.events = [
        _event(total_tokens=10),
        _event(total_tokens=50),
        _event(total_tokens=120),
    ]

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(_build_payload())
        frames, _ = _collect_frames(ws)

    totals = [frame["total_tokens"] for frame in frames]
    assert totals == sorted(totals)


def test_context_id_muda_a_cada_nova_tarefa(client: TestClient) -> None:
    _FakeStartup.events = [
        _event(context_window=ContextWindowDTO(context_id="ctx-1", context_size=5), task="T1"),
        _event(context_window=ContextWindowDTO(context_id="ctx-2", context_size=3), task="T2"),
    ]

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(_build_payload())
        frames, _ = _collect_frames(ws)

    context_ids = [frame["context_window"]["context_id"] for frame in frames]
    assert context_ids == ["ctx-1", "ctx-2"]


def test_payload_com_json_malformado_gera_erro_e_fecha_com_1003(client: TestClient) -> None:
    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_text("isto nao e json")
        frames, close_code = _collect_frames(ws)

    assert frames[0]["type"] == "error"
    assert close_code == 1003


def test_payload_sem_message_gera_erro_e_fecha_com_1003(client: TestClient) -> None:
    payload = _build_payload()
    del payload["message"]

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(payload)
        frames, close_code = _collect_frames(ws)

    assert frames[0]["type"] == "error"
    assert close_code == 1003


def test_frame_acima_do_tamanho_maximo_fecha_com_1009(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RALPH_WEBSOCKET_MAX_MESSAGE_BYTES", "10")

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(_build_payload())
        frames, close_code = _collect_frames(ws)

    assert frames == []
    assert close_code == 1009


def test_cliente_desconecta_no_meio_nao_derruba_o_servidor_e_finaliza_sessao_como_failed(
    client: TestClient,
) -> None:
    """O gerador simula o disconnect (nenhum frame extra é aguardado do servidor: quando o
    cliente já se foi, não há ninguém para receber um fechamento)."""
    _FakeStartup.events = [_event()]
    _FakeStartup.error = WebSocketDisconnect(code=1001)

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(_build_payload())
        primeiro_evento = ws.receive_json()

    assert primeiro_evento["type"] == "thinking"
    assert _FakeStartup.instances[0].session_recorder.finished_with == SessionStatusEnum.FAILED


def test_cliente_que_desconecta_depois_da_sessao_encerrada_nao_a_encerra_de_novo(client: TestClient) -> None:
    """A sessão concluída (ou já falha) não pode ser finalizada outra vez pela rota."""
    _FakeSessionRecorder.status = SessionStatusEnum.COMPLETED
    _FakeStartup.events = [_event(type="result", subtype="compile", task="synthesis")]
    _FakeStartup.error = WebSocketDisconnect(code=1001)

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(_build_payload())
        ws.receive_json()

    assert _FakeStartup.instances[0].session_recorder.finish_calls == 0


def test_interrupcao_que_ja_emitiu_o_evento_de_erro_do_dominio_nao_envia_um_segundo_frame_de_erro(
    client: TestClient,
) -> None:
    """O desfecho terminal é um só: o evento de erro do domínio, seguido do fechamento 1011."""
    _FakeStartup.events = [_event(), _event(type="error", subtype="compile", task="synthesis", content="**Erro:** x")]
    _FakeStartup.error = RuntimeError("limite atingido")

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(_build_payload())
        frames, close_code = _collect_frames(ws)

    assert [frame["type"] for frame in frames] == ["thinking", "error"]
    assert set(frames[-1].keys()) == _CONTRATO_CAMPOS
    assert close_code == 1011


def test_falha_sem_evento_de_erro_do_dominio_ainda_recebe_o_frame_generico(client: TestClient) -> None:
    _FakeStartup.events = [_event()]
    _FakeStartup.error = RuntimeError("provedor fora do ar")

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(_build_payload())
        frames, close_code = _collect_frames(ws)

    assert [frame["type"] for frame in frames] == ["thinking", "error"]
    assert frames[-1] == {"type": "error", "content": "provedor fora do ar"}
    assert close_code == 1011


def test_use_case_levanta_gera_evento_de_erro_e_fecha_com_1011(client: TestClient) -> None:
    _FakeStartup.events = []
    _FakeStartup.error = RuntimeError("provedor fora do ar")

    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(_build_payload())
        frames, close_code = _collect_frames(ws)

    assert frames[-1]["type"] == "error"
    assert close_code == 1011


def test_duas_conexoes_simultaneas_tem_sessoes_e_estados_independentes(client: TestClient) -> None:
    _FakeStartup.events = [_event(session_id="sess_a")]
    with client.websocket_connect("/v1/message/reasoning") as ws_a:
        ws_a.send_json(_build_payload())
        frames_a, _ = _collect_frames(ws_a)

    _FakeStartup.events = [_event(session_id="sess_b")]
    with client.websocket_connect("/v1/message/reasoning") as ws_b:
        ws_b.send_json(_build_payload())
        frames_b, _ = _collect_frames(ws_b)

    assert frames_a[0]["session_id"] == "sess_a"
    assert frames_b[0]["session_id"] == "sess_b"
    assert len(_FakeStartup.instances) == 2
    assert _FakeStartup.instances[0] is not _FakeStartup.instances[1]


class _FakeDisconnectedWebSocket:
    """Dublê de baixo nível, usado só para provar que a rota não tenta enviar
    num socket que a camada ASGI já marcou como desconectado."""

    def __init__(self, raw_text: str) -> None:
        self.raw_text = raw_text
        self.client_state = WebSocketState.DISCONNECTED
        self.sent: list[dict[str, Any]] = []
        self.closed_with: int | None = None

    async def accept(self) -> None:
        pass

    async def receive_text(self) -> str:
        return self.raw_text

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)

    async def close(self, code: int) -> None:
        self.closed_with = code


def test_erro_generico_nao_envia_frame_quando_o_socket_ja_esta_desconectado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeStartup.events = []
    _FakeStartup.error = RuntimeError("provedor fora do ar")
    monkeypatch.setattr(message_router_module, "RalphThinkingStartup", _FakeStartup)
    websocket = _FakeDisconnectedWebSocket(raw_text=json.dumps(_build_payload()))

    asyncio.run(reasoning(websocket))

    assert websocket.sent == []
    assert websocket.closed_with == 1011
