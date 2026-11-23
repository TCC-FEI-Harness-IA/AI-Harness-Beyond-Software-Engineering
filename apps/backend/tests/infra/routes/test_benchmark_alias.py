import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.infra.routes.v1.benchmark import router as router_module
from src.infra.startups.benchmark_alias_startup import BenchmarkAliasStartup
from src.main import create_app
from tests.doubles.benchmark_factories import bateria


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "json_file")
    monkeypatch.setenv("RALPH_BENCHMARK_SESSIONS_STORAGE_PATH", str(tmp_path))
    repository = BenchmarkAliasStartup().update_use_case.repository
    session = bateria(status=BenchmarkSessionStatusEnum.COMPLETED)
    asyncio.run(repository.save(session))
    running = bateria()
    running.id = "bench_running"
    asyncio.run(repository.save(running))
    return TestClient(create_app())


def test_alias_persiste_no_detalhe_e_na_listagem_e_pode_ser_removido(client: TestClient) -> None:
    path = "/v1/benchmark/sessions/bench_1"
    before = client.get(path).json()
    for alias, expected in [("  Comparação de modelos  ", "Comparação de modelos"),
                            ("Outra rodada", "Outra rodada"), (None, None), ("   ", None)]:
        response = client.put(f"{path}/alias", json={"alias": alias})
        assert response.status_code == 200
        assert response.json()["alias"] == expected
        assert client.get(path).json()["alias"] == expected
        sessions = client.get("/v1/benchmark/sessions").json()["benchmark_sessions"]
        assert next(item for item in sessions if item["id"] == "bench_1")["alias"] == expected
        assert response.json()["questions"] == before["questions"]
        assert response.json()["created_at"] == before["created_at"]


@pytest.mark.parametrize(("session_id", "status"), [
    ("bench_9", 404), ("bench_running", 409), ("invalid!", 400),
])
def test_alias_rejeita_bateria_inexistente_em_execucao_ou_id_invalido(
    client: TestClient, session_id: str, status: int,
) -> None:
    response = client.put(f"/v1/benchmark/sessions/{session_id}/alias", json={"alias": "Teste"})
    assert response.status_code == status


@pytest.mark.parametrize("payload", [{}, {"alias": 42}, {"alias": "x" * 121}, {"alias": "ok", "status": "running"}])
def test_alias_valida_o_corpo_sem_alterar_a_bateria(client: TestClient, payload: dict) -> None:
    response = client.put("/v1/benchmark/sessions/bench_1/alias", json=payload)
    assert response.status_code == 422
    assert client.get("/v1/benchmark/sessions/bench_1").json()["alias"] is None


def test_alias_falha_de_persistencia_retorna_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable():
        raise RuntimeError("Mongo indisponível")

    monkeypatch.setattr(router_module, "BenchmarkAliasStartup", unavailable)
    response = client.put("/v1/benchmark/sessions/bench_1/alias", json={"alias": "Teste"})
    assert response.status_code == 500
    assert response.json()["detail"] == "Mongo indisponível"
