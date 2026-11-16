"""Garantias de segurança ponta a ponta, com o grafo real e só a rede da OpenRouter simulada.

- A chave OpenRouter do usuário só aparece no header enviado à OpenRouter: nunca em arquivos,
  documentos do MongoDB, respostas, exportações ou logs.
- Contas diferentes nunca enxergam, alteram, exportam ou reexecutam dados uma da outra.
- Importações não atribuem dono, privilégios nem publicação oficial.
"""
import asyncio
import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from starlette.websockets import WebSocketDisconnect

from src.infra.adapters import mongo_client_adapter
from src.infra.services.llm_service_factory import LLMServiceFactory
from src.infra.services.openrouter_service import OpenRouterService
from src.infra.startups.default_message_startup import DefaultMessageStartup
from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from tests.doubles.security_doubles import (
    CHAVE_VALIDA,
    CHAVE_VALIDA_2,
    authenticated_client,
    authorization_for,
    build_security,
)
from tests.infra.routes.test_benchmark_end_to_end import _roteiro_ralph

_MODELO = "vendor/modelo"


class _OpenRouterFalsa:
    """Responde em ordem e registra a chave de cada chamada."""

    def __init__(self) -> None:
        self.chaves: list[str] = []
        self.roteiro: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.chaves.append(request.headers["Authorization"].removeprefix("Bearer "))
        conteudo = self.roteiro.pop(0) if self.roteiro else "RESPOSTA_FINAL: A"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": conteudo}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
        )


@pytest.fixture
def provedor(monkeypatch: pytest.MonkeyPatch) -> _OpenRouterFalsa:
    falsa = _OpenRouterFalsa()

    def _servicos(factory: LLMServiceFactory, authorization: Any) -> list[OpenRouterService]:
        return [
            OpenRouterService(
                logger=factory.settings.logger(__file__), settings=factory.settings, authorization=authorization,
                transport=httpx.MockTransport(falsa),
            )
        ]

    monkeypatch.setattr(LLMServiceFactory, "create_all", _servicos)
    return falsa


@pytest.fixture(params=["json_file", "mongodb"])
def armazenamento(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", request.param)
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(tmp_path / "sessions"))
    monkeypatch.setenv("RALPH_BENCHMARK_SESSIONS_STORAGE_PATH", str(tmp_path / "benchmark-sessions"))
    monkeypatch.setenv("RALPH_OFFICIAL_STORAGE_PATH", str(tmp_path / "official"))
    monkeypatch.setenv("RALPH_BENCHMARK_PROGRESS_INTERVAL_SECONDS", "0.05")
    monkeypatch.setenv("LLM_MODEL", _MODELO)
    monkeypatch.setenv("GENAI_AVAILABLE_MODELS", _MODELO)
    monkeypatch.setenv("GENAI_AVAILABLE_PROVIDERS", "open_router")
    monkeypatch.setenv("LLM_MAX_TOKENS", "120000")
    monkeypatch.setenv("RALPH_FINAL_ANSWER_TOKEN_RESERVE", "4000")
    cliente = AsyncMongoMockClient()
    monkeypatch.setattr(mongo_client_adapter, "AsyncIOMotorClient", lambda *_, **__: cliente)
    return {"backend": request.param, "dir": tmp_path, "mongo": cliente}


def _corpo_default() -> dict[str, Any]:
    return {
        "message": {"user_input": "Qual é a capital do Brasil?"},
        "llm_model_config": {
            "provider": "open_router", "provider_config": {"model_name": _MODELO}, "max_tokens": 2000,
            "temperature": 0.3,
        },
    }


def _executar_bateria(cliente: TestClient) -> dict[str, Any]:
    with cliente.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json({
            "question_count": 1, "max_parallel": 1,
            "llm_model_config": {**_corpo_default()["llm_model_config"], "max_tokens": 50000},
        })
        ultimo: dict[str, Any] = {}
        try:
            while True:
                ultimo = ws.receive_json()
        except WebSocketDisconnect:
            return ultimo["benchmark_session"]


def _todo_conteudo_persistido(armazenamento: dict) -> str:
    textos = [path.read_text(encoding="utf-8") for path in armazenamento["dir"].rglob("*.json")]
    banco = armazenamento["mongo"]["tcc"]

    async def _documentos() -> list[str]:
        colecoes = await banco.list_collection_names()
        return [json.dumps(doc, default=str) for nome in colecoes for doc in await banco[nome].find({}).to_list(None)]

    return "\n".join(textos + asyncio.run(_documentos()))


def test_chave_do_usuario_so_vai_no_header_da_openrouter(
    armazenamento: dict, provedor: _OpenRouterFalsa, caplog: pytest.LogCaptureFixture
) -> None:
    cliente = authenticated_client(user_id="usr_ana")
    provedor.roteiro = ["Brasília", "RESPOSTA_FINAL: A", *_roteiro_ralph("RESPOSTA_FINAL: A")]

    with caplog.at_level(logging.DEBUG):
        resposta = cliente.post("/v1/message/default", json=_corpo_default())
        bateria = _executar_bateria(cliente)
        exportacao = cliente.get(f"/v1/benchmark/sessions/{bateria['id']}/export")
        ids = cliente.get("/v1/sessions").json()["session_ids"]
        historico = [cliente.get(f"/v1/sessions/{sid}").text for sid in ids]

    assert resposta.status_code == 200 and exportacao.status_code == 200
    assert bateria["status"] == "completed"
    assert set(provedor.chaves) == {CHAVE_VALIDA} and len(provedor.chaves) >= 3
    with zipfile.ZipFile(io.BytesIO(exportacao.content)) as arquivo:
        conteudo_zip = "".join(arquivo.read(nome).decode("utf-8", "ignore") for nome in arquivo.namelist())
    persistido = _todo_conteudo_persistido(armazenamento)
    for texto in [resposta.text, json.dumps(bateria), conteudo_zip, *historico, persistido, caplog.text]:
        assert CHAVE_VALIDA not in texto
    assert cliente.get("/v1/credentials/openrouter").text.count("sk-or") == 0


async def test_execucoes_simultaneas_de_usuarios_diferentes_nao_misturam_chaves(
    armazenamento: dict, provedor: _OpenRouterFalsa
) -> None:
    payload = DefaultInputDTO.model_validate(_corpo_default())
    contas = [("usr_ana", CHAVE_VALIDA), ("usr_bia", CHAVE_VALIDA_2)] * 2
    startups = [
        DefaultMessageStartup(owner_id=dono, authorization=authorization_for(chave, owner_id=dono))
        for dono, chave in contas
    ]

    resultados = await asyncio.gather(*[startup.run(payload=payload) for startup in startups])

    assert sorted(provedor.chaves) == sorted([CHAVE_VALIDA, CHAVE_VALIDA_2] * 2)
    assert len({resultado.session_id for resultado in resultados}) == 4


def test_isolamento_entre_contas_em_consulta_alteracao_exportacao_reexecucao_e_importacao(
    armazenamento: dict, provedor: _OpenRouterFalsa
) -> None:
    seguranca = build_security()
    ana = authenticated_client(user_id="usr_ana", security=seguranca)
    bia = authenticated_client(user_id="usr_bia", security=seguranca)
    provedor.roteiro = ["RESPOSTA_FINAL: B", *_roteiro_ralph("RESPOSTA_FINAL: B")]
    bateria = _executar_bateria(ana)
    caminho = f"/v1/benchmark/sessions/{bateria['id']}"
    sessao_da_ana = bateria["session_ids"][0]

    assert bia.get("/v1/benchmark/sessions").json() == {"benchmark_sessions": []}
    assert bia.get(caminho).status_code == 404
    assert bia.get(f"/v1/sessions/{sessao_da_ana}").status_code == 404
    assert bia.put(f"{caminho}/alias", json={"alias": "invasão"}).status_code == 404
    assert bia.get(f"{caminho}/export").status_code == 404
    assert bia.get(f"{caminho}/ralph-loop-errors/export").status_code == 404
    with bia.websocket_connect(f"{caminho}/questions/rerun") as ws:
        ws.send_json({"question_ids": [bateria["questions"][0]["question_id"]]})
        erro = ws.receive_json()
    assert erro["type"] == "error"
    chamadas_antes = len(provedor.chaves)

    pacote = ana.get(f"{caminho}/export").content
    adulterado = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(pacote)) as original, zipfile.ZipFile(adulterado, "w") as novo:
        for nome in original.namelist():
            dados = original.read(nome)
            if nome.endswith(".json"):
                documento = json.loads(dados)
                if isinstance(documento, dict):
                    documento |= {"owner_id": "usr_ana", "role": "admin", "official": True, "status_oficial": "active"}
                dados = json.dumps(documento).encode()
            novo.writestr(nome, dados)

    importada = bia.post(
        "/v1/benchmark/sessions/import", content=adulterado.getvalue(), headers={"Content-Type": "application/zip"}
    )

    assert importada.status_code == 201, importada.text
    assert [item["id"] for item in bia.get("/v1/benchmark/sessions").json()["benchmark_sessions"]] == [bateria["id"]]
    assert ana.get(caminho).json()["alias"] is None
    assert ana.post("/v1/benchmark/sessions/import", content=pacote,
                    headers={"Content-Type": "application/zip"}).status_code == 409
    publico = TestClient(ana.app).get("/v1/public/benchmarks").json()
    assert publico == {"publications": []}
    assert len(provedor.chaves) == chamadas_antes
