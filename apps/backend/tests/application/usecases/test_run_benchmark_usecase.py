import asyncio
import logging
from collections.abc import Callable

import pytest

from src.application.dtos.run_benchmark_input_dto import RunBenchmarkInputDTO
from src.application.usecases.run_benchmark_usecase import RunBenchmarkUseCase
from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_flow_request import BenchmarkFlowRequest
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_question_status_enum import BenchmarkQuestionStatusEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.errors.invalid_benchmark_request_error import InvalidBenchmarkRequestError
from tests.doubles.benchmark_factories import questao
from tests.doubles.fake_benchmark_flow_runner import FakeBenchmarkFlowRunner
from tests.doubles.fake_benchmark_question_provider import FakeBenchmarkQuestionProvider
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_id_generator import FakeIdGenerator
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.in_memory_benchmark_session_repository import InMemoryBenchmarkSessionRepository

_SIMPLES = BenchmarkInferenceModeEnum.SIMPLE
_RALPH = BenchmarkInferenceModeEnum.RALPH


def _entrada(question_count: int | None = None, max_parallel: int = 5) -> RunBenchmarkInputDTO:
    return RunBenchmarkInputDTO(
        question_count=question_count,
        max_parallel=max_parallel,
        model_name="vendor/modelo",
        max_tokens=4096,
        temperature=0.0,
        provider=ModelProviderEnum.OPEN_ROUTER,
    )


def _desfecho(request: BenchmarkFlowRequest, correto: bool = True, tokens: int = 10) -> BenchmarkFlowOutcome:
    return BenchmarkFlowOutcome(
        mode=request.mode,
        session_id=f"{request.question.id}_{request.mode.value}",
        selected_alternative="A",
        is_correct=correto,
        error=None,
        duration_seconds=0.1,
        total_tokens=tokens,
    )


async def _imediato(request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
    return _desfecho(request)


def _caso_de_uso(
    runner: FakeBenchmarkFlowRunner,
    quantidade: int = 3,
    repositorio: InMemoryBenchmarkSessionRepository | None = None,
    **settings: object,
) -> tuple[RunBenchmarkUseCase, InMemoryBenchmarkSessionRepository]:
    repositorio = repositorio or InMemoryBenchmarkSessionRepository()
    caso = RunBenchmarkUseCase(
        question_provider=FakeBenchmarkQuestionProvider([questao(f"Q{i}") for i in range(quantidade)]),
        flow_runner=runner,
        repository=repositorio,
        clock=FakeClock(monotonic_values=[1000, 1500, 2000, 2500, 3000]),
        id_generator=FakeIdGenerator(),
        settings=FakeSettings(**settings),
        logger=logging.getLogger("teste.benchmark"),
    )
    return caso, repositorio


async def _coletar(caso: RunBenchmarkUseCase, entrada: RunBenchmarkInputDTO) -> list[dict[str, object]]:
    estados = []
    async for sessao in caso.execute(input_dto=entrada):
        estados.append(_foto(sessao))
    return estados


def _foto(sessao: BenchmarkSession) -> dict[str, object]:
    return {
        "status": sessao.status,
        "pending": sessao.pending_count,
        "running": sessao.running_count,
        "finished": sessao.finished_count,
        "tokens": sessao.total_tokens,
    }


async def test_executa_todas_as_questoes_em_fifo_com_simples_antes_do_ralph() -> None:
    runner = FakeBenchmarkFlowRunner(_imediato)
    caso, repositorio = _caso_de_uso(runner, quantidade=3)

    estados = await _coletar(caso, _entrada(max_parallel=1))

    assert [(item.question.id, item.mode) for item in runner.requests] == [
        ("Q0", _SIMPLES), ("Q0", _RALPH), ("Q1", _SIMPLES), ("Q1", _RALPH), ("Q2", _SIMPLES), ("Q2", _RALPH),
    ]
    assert estados[0] == {"status": BenchmarkSessionStatusEnum.RUNNING, "pending": 3, "running": 0, "finished": 0,
                          "tokens": 0}
    assert estados[-1]["status"] is BenchmarkSessionStatusEnum.COMPLETED
    assert estados[-1]["finished"] == 3
    final = repositorio.sessions["bench_1"]
    assert final.status is BenchmarkSessionStatusEnum.COMPLETED
    assert final.total_tokens == 60
    assert final.session_ids == ["Q0_simple", "Q0_ralph", "Q1_simple", "Q1_ralph", "Q2_simple", "Q2_ralph"]
    assert final.finished_at is not None


async def test_prompt_e_o_enunciado_seguido_da_instrucao_e_traz_a_configuracao_da_bateria() -> None:
    runner = FakeBenchmarkFlowRunner(_imediato)
    caso, _ = _caso_de_uso(runner, quantidade=1)

    await _coletar(caso, _entrada())

    pedido = runner.requests[0]
    assert pedido.prompt == f"{questao('Q0').statement}\n\nInstrução comum"
    assert "gabarito" not in pedido.prompt
    assert pedido.benchmark_session_id == "bench_1"
    assert pedido.llm_config.model_name == "vendor/modelo"
    assert pedido.llm_config.temperature == 0.0


async def test_quantidade_menor_executa_as_primeiras_questoes_na_ordem() -> None:
    runner = FakeBenchmarkFlowRunner(_imediato)
    caso, repositorio = _caso_de_uso(runner, quantidade=5)

    await _coletar(caso, _entrada(question_count=2))

    assert [questao.question_id for questao in repositorio.sessions["bench_1"].questions] == ["Q0", "Q1"]
    assert {item.question.id for item in runner.requests} == {"Q0", "Q1"}


async def test_respeita_o_maximo_de_questoes_em_paralelo() -> None:
    liberar = asyncio.Event()

    async def comportamento(request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        if len(runner.active) == 3:
            liberar.set()
        await asyncio.wait_for(liberar.wait(), timeout=2)
        return _desfecho(request)

    runner = FakeBenchmarkFlowRunner(comportamento)
    caso, _ = _caso_de_uso(runner, quantidade=7)

    estados = await _coletar(caso, _entrada(max_parallel=3))

    assert runner.max_active == 3
    assert max(estado["running"] for estado in estados) <= 3
    assert estados[-1]["finished"] == 7


async def test_paralelismo_maior_que_as_questoes_usa_um_worker_por_questao() -> None:
    runner = FakeBenchmarkFlowRunner(_imediato)
    caso, _ = _caso_de_uso(runner, quantidade=2)

    estados = await _coletar(caso, _entrada(max_parallel=5))

    assert estados[-1]["finished"] == 2


async def test_consumo_informado_pelo_fluxo_aparece_no_estado_antes_do_desfecho() -> None:
    continuar = asyncio.Event()

    async def comportamento(request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        if request.mode is _RALPH:
            on_tokens(77)
            await asyncio.wait_for(continuar.wait(), timeout=2)
            return _desfecho(request, tokens=100)
        return _desfecho(request, tokens=10)

    runner = FakeBenchmarkFlowRunner(comportamento)
    caso, _ = _caso_de_uso(runner, quantidade=1)

    estados = []
    async for sessao in caso.execute(input_dto=_entrada()):
        estados.append(_foto(sessao))
        if sessao.total_tokens == 87:
            continuar.set()

    assert {"status": BenchmarkSessionStatusEnum.RUNNING, "pending": 0, "running": 1, "finished": 0,
            "tokens": 87} in estados
    assert estados[-1]["tokens"] == 110


async def test_sem_mudancas_emite_progresso_a_cada_intervalo() -> None:
    async def lento(request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        await asyncio.sleep(0.05)
        return _desfecho(request)

    runner = FakeBenchmarkFlowRunner(lento)
    caso, _ = _caso_de_uso(runner, quantidade=1, ralph_benchmark_progress_interval_seconds=0.005)

    estados = await _coletar(caso, _entrada())

    em_execucao = [estado for estado in estados if estado["running"] == 1]
    assert len(em_execucao) > 4


async def test_persiste_no_inicio_a_cada_desfecho_e_no_encerramento() -> None:
    runner = FakeBenchmarkFlowRunner(_imediato)
    caso, repositorio = _caso_de_uso(runner, quantidade=2)

    await _coletar(caso, _entrada(max_parallel=1))

    assert len(repositorio.saved) == 1 + 4 + 1
    assert repositorio.saved[0].pending_count == 2
    assert repositorio.saved[2].question("Q0").status is BenchmarkQuestionStatusEnum.FINISHED
    assert repositorio.saved[-1].status is BenchmarkSessionStatusEnum.COMPLETED


async def test_tempo_de_execucao_vem_do_relogio_monotonico() -> None:
    runner = FakeBenchmarkFlowRunner(_imediato)
    caso, repositorio = _caso_de_uso(runner, quantidade=1)

    await _coletar(caso, _entrada())

    assert repositorio.sessions["bench_1"].wall_time_ms > 0


async def test_falha_de_persistencia_no_meio_encerra_a_bateria_como_failed() -> None:
    runner = FakeBenchmarkFlowRunner(_imediato)
    caso, repositorio = _caso_de_uso(
        runner, quantidade=3, repositorio=InMemoryBenchmarkSessionRepository(failing_save_calls={2})
    )

    estados = []
    final = None
    async for sessao in caso.execute(input_dto=_entrada(max_parallel=1)):
        estados.append(_foto(sessao))
        final = sessao

    assert final.status is BenchmarkSessionStatusEnum.FAILED
    assert "persistência indisponível" in final.error
    assert repositorio.sessions["bench_1"].status is BenchmarkSessionStatusEnum.FAILED
    assert len(runner.requests) < 6


async def test_falha_ao_persistir_o_encerramento_nao_impede_o_estado_final() -> None:
    runner = FakeBenchmarkFlowRunner(_imediato)
    caso, repositorio = _caso_de_uso(
        runner, quantidade=1, repositorio=InMemoryBenchmarkSessionRepository(failing_save_calls={4})
    )

    estados = await _coletar(caso, _entrada())

    assert estados[-1]["status"] is BenchmarkSessionStatusEnum.COMPLETED
    assert repositorio.sessions["bench_1"].status is BenchmarkSessionStatusEnum.RUNNING


async def test_consumidor_que_para_de_ler_interrompe_a_bateria_e_cancela_os_fluxos() -> None:
    async def bloqueado(request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        await asyncio.Event().wait()
        raise AssertionError("inalcançável")

    runner = FakeBenchmarkFlowRunner(bloqueado)
    caso, repositorio = _caso_de_uso(runner, quantidade=4)
    gerador = caso.execute(input_dto=_entrada(max_parallel=2))

    async for sessao in gerador:
        if sessao.running_count == 2:
            break
    await gerador.aclose()

    final = repositorio.sessions["bench_1"]
    assert final.status is BenchmarkSessionStatusEnum.INTERRUPTED
    assert final.interrupted_count == 2
    assert final.pending_count == 2
    assert len(runner.cancelled) == 2


@pytest.mark.parametrize("max_parallel", [0, 11])
async def test_paralelismo_fora_do_limite_e_recusado_antes_de_criar_a_bateria(max_parallel: int) -> None:
    runner = FakeBenchmarkFlowRunner(_imediato)
    caso, repositorio = _caso_de_uso(runner)

    with pytest.raises(InvalidBenchmarkRequestError, match="max_parallel"):
        await _coletar(caso, _entrada(max_parallel=max_parallel))

    assert repositorio.saved == []


@pytest.mark.parametrize("question_count", [0, 4])
async def test_quantidade_fora_do_dataset_e_recusada_antes_de_criar_a_bateria(question_count: int) -> None:
    runner = FakeBenchmarkFlowRunner(_imediato)
    caso, repositorio = _caso_de_uso(runner, quantidade=3)

    with pytest.raises(InvalidBenchmarkRequestError, match="question_count deve estar entre 1 e 3"):
        await _coletar(caso, _entrada(question_count=question_count))

    assert repositorio.saved == []
    assert runner.requests == []
