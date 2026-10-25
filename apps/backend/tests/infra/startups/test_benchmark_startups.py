import json
from pathlib import Path
from typing import Any, Callable

import pytest

from src.application.usecases.get_benchmark_session_usecase import GetBenchmarkSessionUseCase
from src.application.usecases.list_benchmark_sessions_usecase import ListBenchmarkSessionsUseCase
from src.application.usecases.run_benchmark_usecase import RunBenchmarkUseCase
from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_flow_request import BenchmarkFlowRequest
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.infra.routes.v1.benchmark.dtos.benchmark_run_input_dto import BenchmarkRunInputDTO
from src.infra.startups.benchmark_query_startup import BenchmarkQueryStartup
from src.infra.startups.benchmark_run_startup import BenchmarkRunStartup


@pytest.fixture
def armazenamento(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isola os diretórios das baterias e das sessões dentro do teste."""
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "json_file")
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(tmp_path / "sessions"))
    monkeypatch.setenv("RALPH_BENCHMARK_SESSIONS_STORAGE_PATH", str(tmp_path / "benchmark-sessions"))
    monkeypatch.setenv("RALPH_BENCHMARK_PROGRESS_INTERVAL_SECONDS", "0.01")
    return tmp_path


class _RunnerImediato:
    """Executor dublê: responde todo fluxo na hora, com acerto."""

    async def run(self, request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        return BenchmarkFlowOutcome(
            mode=request.mode, session_id=f"{request.question.id}_{request.mode.value}", selected_alternative="A",
            is_correct=True, error=None, duration_seconds=0.1, total_tokens=3,
        )


def _abertura(**sobrescritas: Any) -> BenchmarkRunInputDTO:
    corpo: dict[str, Any] = {
        "question_count": 2,
        "max_parallel": 2,
        "llm_model_config": {
            "provider": "open_router",
            "provider_config": {"model_name": "vendor/modelo"},
            "max_tokens": 100,
            "temperature": 0.2,
        },
    }
    corpo.update(sobrescritas)
    return BenchmarkRunInputDTO.model_validate(corpo)


def test_startup_de_execucao_monta_todo_o_grafo(armazenamento: Path) -> None:
    startup = BenchmarkRunStartup()

    assert all(valor is not None for valor in vars(startup).values())
    assert isinstance(startup.run_benchmark_use_case, RunBenchmarkUseCase)
    assert startup.run_benchmark_use_case.flow_runner is startup.flow_runner
    assert startup.run_benchmark_use_case.repository is startup.repository


async def test_startup_de_execucao_traduz_a_abertura_e_emite_progress_ate_o_result(armazenamento: Path) -> None:
    startup = BenchmarkRunStartup()
    startup.run_benchmark_use_case.flow_runner = _RunnerImediato()

    frames = [frame async for frame in startup.run(payload=_abertura())]

    assert {frame.type for frame in frames[:-1]} == {"progress"}
    assert frames[-1].type == "result"
    bateria = frames[-1].benchmark_session
    assert bateria["status"] == "completed"
    assert bateria["model_name"] == "vendor/modelo"
    assert bateria["temperature"] == 0.2
    assert bateria["question_count"] == 2
    gravada = json.loads((armazenamento / "benchmark-sessions" / f"{bateria['id']}.json").read_text("utf-8"))
    assert gravada == bateria


async def test_startup_de_consulta_lista_detalha_e_descreve(armazenamento: Path) -> None:
    execucao = BenchmarkRunStartup()
    execucao.run_benchmark_use_case.flow_runner = _RunnerImediato()
    frames = [frame async for frame in execucao.run(payload=_abertura(question_count=1))]
    bateria = frames[-1].benchmark_session

    consulta = BenchmarkQueryStartup()

    assert isinstance(consulta.get_benchmark_session_use_case, GetBenchmarkSessionUseCase)
    assert isinstance(consulta.list_benchmark_sessions_use_case, ListBenchmarkSessionsUseCase)
    assert await consulta.get_benchmark_session_document(benchmark_session_id=bateria["id"]) == bateria
    assert await consulta.list_benchmark_session_documents() == [bateria]
    assert consulta.describe_dataset()["max_parallel_limit"] == 10
    assert len(consulta.describe_dataset()["question_ids"]) == 15


async def test_startup_de_consulta_recusa_bateria_inexistente(armazenamento: Path) -> None:
    with pytest.raises(BenchmarkSessionNotFoundError):
        await BenchmarkQueryStartup().get_benchmark_session_document(benchmark_session_id="bench_9")
