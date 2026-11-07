import io
import json
import zipfile
from pathlib import Path
from typing import Any, Callable

import pytest

from src.application.usecases.export_benchmark_ralph_errors_usecase import ExportBenchmarkRalphErrorsUseCase
from src.application.usecases.get_benchmark_session_usecase import GetBenchmarkSessionUseCase
from src.application.usecases.list_benchmark_sessions_usecase import ListBenchmarkSessionsUseCase
from src.application.usecases.run_benchmark_usecase import RunBenchmarkUseCase
from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_flow_request import BenchmarkFlowRequest
from src.application.usecases.rerun_benchmark_question_usecase import RerunBenchmarkQuestionUseCase
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.errors.no_benchmark_errors_to_export_error import NoBenchmarkErrorsToExportError
from tests.doubles.benchmark_factories import bateria, desfecho
from src.infra.routes.v1.benchmark.dtos.benchmark_run_input_dto import BenchmarkRunInputDTO
from src.infra.startups.benchmark_export_startup import BenchmarkExportStartup
from src.infra.startups.benchmark_query_startup import BenchmarkQueryStartup
from src.infra.startups.benchmark_rerun_startup import BenchmarkRerunStartup
from src.infra.startups.benchmark_run_startup import BenchmarkRunStartup


@pytest.fixture
def armazenamento(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isola os diretórios das baterias e das sessões dentro do teste."""
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "json_file")
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(tmp_path / "sessions"))
    monkeypatch.setenv("RALPH_BENCHMARK_SESSIONS_STORAGE_PATH", str(tmp_path / "benchmark-sessions"))
    monkeypatch.setenv("RALPH_BENCHMARK_PROGRESS_INTERVAL_SECONDS", "0.01")
    monkeypatch.setenv("LLM_MAX_TOKENS", "120000")
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
    assert consulta.describe_dataset()["max_tokens_limit"] == 120000
    assert len(consulta.describe_dataset()["question_ids"]) == 90


async def test_startup_de_consulta_recusa_bateria_inexistente(armazenamento: Path) -> None:
    with pytest.raises(BenchmarkSessionNotFoundError):
        await BenchmarkQueryStartup().get_benchmark_session_document(benchmark_session_id="bench_9")


class _RunnerQueErraNoRalph:
    """Executor dublê: o simples acerta e o Ralph Loop erra, deixando uma sessão persistida."""

    async def run(self, request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        ralph = request.mode.value == "ralph"
        return BenchmarkFlowOutcome(
            mode=request.mode, session_id=f"{request.question.id}_{request.mode.value}", selected_alternative="A",
            is_correct=not ralph, error=None, duration_seconds=0.1, total_tokens=3,
        )


def test_startup_de_exportacao_monta_todo_o_grafo(armazenamento: Path) -> None:
    startup = BenchmarkExportStartup()

    assert all(valor is not None for valor in vars(startup).values())
    assert isinstance(startup.export_use_case, ExportBenchmarkRalphErrorsUseCase)
    assert startup.archive_builder.session_mapper is startup.session_mapper


async def test_startup_de_exportacao_gera_o_zip_com_os_erros_do_ralph(armazenamento: Path) -> None:
    execucao = BenchmarkRunStartup()
    execucao.run_benchmark_use_case.flow_runner = _RunnerQueErraNoRalph()
    frames = [frame async for frame in execucao.run(payload=_abertura(question_count=2))]
    bateria = frames[-1].benchmark_session

    arquivo = await BenchmarkExportStartup().export_ralph_errors(benchmark_session_id=bateria["id"])

    assert arquivo.filename == f"benchmark-session-{bateria['id']}-ralph-loop-errors.zip"
    with zipfile.ZipFile(io.BytesIO(arquivo.content)) as zip_:
        pastas = {nome.split("/")[0] for nome in zip_.namelist()}
        assert pastas == {f"questao-{item['question_id']}" for item in bateria["questions"]}
        execucao_ralph = json.loads(zip_.read(f"{sorted(pastas)[0]}/execucao-ralph-loop.json"))
    assert execucao_ralph["outcome"]["is_correct"] is False
    assert execucao_ralph["session"] is None  # o executor dublê não grava a sessão


async def test_startup_de_exportacao_recusa_bateria_inexistente_e_sem_erros(armazenamento: Path) -> None:
    with pytest.raises(BenchmarkSessionNotFoundError):
        await BenchmarkExportStartup().export_ralph_errors(benchmark_session_id="bench_9")

    execucao = BenchmarkRunStartup()
    execucao.run_benchmark_use_case.flow_runner = _RunnerImediato()
    frames = [frame async for frame in execucao.run(payload=_abertura(question_count=1))]

    with pytest.raises(NoBenchmarkErrorsToExportError):
        await BenchmarkExportStartup().export_ralph_errors(benchmark_session_id=frames[-1].benchmark_session["id"])


async def test_startup_de_reexecucao_monta_o_grafo_e_emite_progress_ate_o_result(armazenamento: Path) -> None:
    startup = BenchmarkRerunStartup()
    assert all(valor is not None for valor in vars(startup).values())
    assert isinstance(startup.rerun_use_case, RerunBenchmarkQuestionUseCase)
    assert startup.rerun_use_case.repository is startup.repository
    questao = "FISICA_ENEM_2022_AZUL_Q093"
    sessao = bateria(questao)
    sessao.start_flow(question_id=questao, mode=BenchmarkInferenceModeEnum.SIMPLE, at=sessao.created_at)
    sessao.record_outcome(
        question_id=questao, outcome=desfecho(mode=BenchmarkInferenceModeEnum.SIMPLE), at=sessao.created_at
    )
    sessao.start_flow(question_id=questao, mode=BenchmarkInferenceModeEnum.RALPH, at=sessao.created_at)
    sessao.record_outcome(
        question_id=questao,
        outcome=desfecho(mode=BenchmarkInferenceModeEnum.RALPH, correto=False),
        at=sessao.created_at,
    )
    sessao.finish_question(question_id=questao, at=sessao.created_at)
    sessao.finish(status=BenchmarkSessionStatusEnum.COMPLETED, at=sessao.created_at, wall_time_ms=1)
    await startup.repository.save(benchmark_session=sessao)
    startup.rerun_use_case.flow_runner = _RunnerImediato()

    frames = [frame async for frame in startup.run(benchmark_session_id="bench_1", question_id=questao)]

    assert {frame.type for frame in frames[:-1]} <= {"progress"}
    assert frames[-1].type == "result"
    documento = frames[-1].benchmark_session
    assert documento["status"] == "completed"
    assert documento["questions"][0]["ralph"]["is_correct"] is True
    assert documento["questions"][0]["ralph"]["session_id"] == f"{questao}_ralph"
    gravada = json.loads((armazenamento / "benchmark-sessions" / "bench_1.json").read_text("utf-8"))
    assert gravada == documento
