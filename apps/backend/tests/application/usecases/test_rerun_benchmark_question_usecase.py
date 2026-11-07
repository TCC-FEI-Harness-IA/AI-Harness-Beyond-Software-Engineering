import asyncio
import copy
import logging
from collections.abc import Callable
from dataclasses import replace

import pytest

from src.application.dtos.rerun_benchmark_question_output_dto import RerunBenchmarkQuestionOutputDTO
from src.application.usecases.rerun_benchmark_question_usecase import RerunBenchmarkQuestionUseCase
from src.domain.entities.benchmark.benchmark_definition import BenchmarkDefinition
from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_flow_request import BenchmarkFlowRequest
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_question_status_enum import BenchmarkQuestionStatusEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_question_not_rerunnable_error import BenchmarkQuestionNotRerunnableError
from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.errors.invalid_benchmark_request_error import InvalidBenchmarkRequestError
from tests.doubles.benchmark_factories import bateria, desfecho, questao
from tests.doubles.fake_benchmark_flow_runner import FakeBenchmarkFlowRunner
from tests.doubles.fake_benchmark_question_provider import FakeBenchmarkQuestionProvider
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.in_memory_benchmark_session_repository import InMemoryBenchmarkSessionRepository

_SIMPLES = BenchmarkInferenceModeEnum.SIMPLE
_RALPH = BenchmarkInferenceModeEnum.RALPH


def _bateria_encerrada(
    simples_correto: bool = True,
    ralph_correto: bool = False,
    status: BenchmarkSessionStatusEnum = BenchmarkSessionStatusEnum.COMPLETED,
) -> BenchmarkSession:
    sessao = bateria("Q1", "Q2")
    for identificador in ("Q1", "Q2"):
        for modo, correto in ((_SIMPLES, simples_correto), (_RALPH, ralph_correto)):
            sessao.start_flow(question_id=identificador, mode=modo, at=sessao.created_at)
            sessao.record_outcome(
                question_id=identificador,
                outcome=desfecho(mode=modo, correto=correto, session_id=f"{identificador}_{modo.value}_antiga"),
                at=sessao.created_at,
            )
        sessao.finish_question(question_id=identificador, at=sessao.created_at)
    sessao.finish(status=status, at=sessao.created_at, wall_time_ms=10)
    return sessao


def _novo_desfecho(request: BenchmarkFlowRequest, correto: bool = True) -> BenchmarkFlowOutcome:
    return desfecho(mode=request.mode, correto=correto, session_id=f"{request.question.id}_{request.mode.value}_nova")


async def _acerta(request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
    on_tokens(42)
    await asyncio.sleep(0.01)
    return _novo_desfecho(request)


async def _erra(request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
    return _novo_desfecho(request, correto=False)


def _caso_de_uso(
    comportamento,
    sessao: BenchmarkSession | None = None,
    repositorio: InMemoryBenchmarkSessionRepository | None = None,
    provider: FakeBenchmarkQuestionProvider | None = None,
) -> tuple[RerunBenchmarkQuestionUseCase, FakeBenchmarkFlowRunner, InMemoryBenchmarkSessionRepository, list]:
    repositorio = repositorio or InMemoryBenchmarkSessionRepository()
    if sessao is not None:
        repositorio.sessions[sessao.id] = sessao
    runner = FakeBenchmarkFlowRunner(comportamento)
    definicoes: list[BenchmarkDefinition] = []
    provider = provider or FakeBenchmarkQuestionProvider([questao("Q1"), questao("Q2")])

    def provider_para(definicao: BenchmarkDefinition) -> FakeBenchmarkQuestionProvider:
        definicoes.append(definicao)
        return provider

    caso = RerunBenchmarkQuestionUseCase(
        question_provider_for=provider_para,
        flow_runner=runner,
        repository=repositorio,
        clock=FakeClock(),
        settings=FakeSettings(),
        logger=logging.getLogger("teste.reexecucao"),
    )
    return caso, runner, repositorio, definicoes


async def _coletar(
    caso: RerunBenchmarkQuestionUseCase, question_id: str = "Q1"
) -> list[RerunBenchmarkQuestionOutputDTO]:
    """Coleta fotos dos estados emitidos, porque a bateria emitida é o mesmo objeto, alterado a cada mudança."""
    return [
        replace(item, benchmark_session=copy.deepcopy(item.benchmark_session))
        async for item in caso.execute(benchmark_session_id="bench_1", question_id=question_id)
    ]


async def test_reexecuta_so_o_fluxo_errado_e_substitui_o_desfecho_na_bateria_persistida() -> None:
    caso, runner, repositorio, definicoes = _caso_de_uso(_acerta, _bateria_encerrada())

    estados = await _coletar(caso)

    assert [(item.question.id, item.mode) for item in runner.requests] == [("Q1", _RALPH)]
    assert runner.requests[0].benchmark_session_id == "bench_1"
    assert runner.requests[0].prompt == "Pergunta\n\nA) um\nB) dois\nC) três\nD) quatro\nE) cinco\n\nInstrução comum"
    assert definicoes
    assert [item.finished for item in estados] == [False] * (len(estados) - 1) + [True]
    assert estados[0].benchmark_session.question("Q1").current_mode is None
    assert any(item.benchmark_session.question("Q1").current_mode is _RALPH for item in estados)
    assert any(item.benchmark_session.question("Q1").current_tokens == 42 for item in estados)

    gravada = repositorio.sessions["bench_1"]
    questao_gravada = gravada.question("Q1")
    assert questao_gravada.ralph.session_id == "Q1_ralph_nova"
    assert questao_gravada.ralph.is_correct
    assert questao_gravada.simple.session_id == "Q1_simple_antiga"
    assert questao_gravada.status is BenchmarkQuestionStatusEnum.FINISHED
    assert questao_gravada.current_mode is None
    assert gravada.question("Q2").ralph.session_id == "Q2_ralph_antiga"
    assert gravada.status is BenchmarkSessionStatusEnum.COMPLETED
    assert gravada.summary(_RALPH).correct == 1


async def test_reexecuta_os_dois_fluxos_em_ordem_e_persiste_a_cada_desfecho() -> None:
    caso, runner, repositorio, _ = _caso_de_uso(_acerta, _bateria_encerrada(simples_correto=False))

    await _coletar(caso)

    assert [item.mode for item in runner.requests] == [_SIMPLES, _RALPH]
    assert repositorio.save_attempts == 2
    primeira, segunda = repositorio.saved
    assert primeira.question("Q1").simple.session_id == "Q1_simple_nova"
    assert primeira.question("Q1").ralph.session_id == "Q1_ralph_antiga"
    assert segunda.question("Q1").ralph.session_id == "Q1_ralph_nova"


async def test_reexecucao_que_continua_errada_registra_o_novo_erro() -> None:
    caso, _, repositorio, _ = _caso_de_uso(_erra, _bateria_encerrada())

    await _coletar(caso)

    assert not repositorio.sessions["bench_1"].question("Q1").ralph.is_correct
    assert repositorio.sessions["bench_1"].question("Q1").ralph.session_id == "Q1_ralph_nova"


@pytest.mark.parametrize("status", [BenchmarkSessionStatusEnum.FAILED, BenchmarkSessionStatusEnum.INTERRUPTED])
async def test_bateria_que_nao_concluiu_mas_tem_a_questao_encerrada_pode_ser_reexecutada(
    status: BenchmarkSessionStatusEnum,
) -> None:
    caso, runner, repositorio, _ = _caso_de_uso(_acerta, _bateria_encerrada(status=status))

    await _coletar(caso)

    assert len(runner.requests) == 1
    assert repositorio.sessions["bench_1"].status is status


async def test_progresso_sem_mudancas_continua_sendo_emitido_pelo_intervalo() -> None:
    liberar = asyncio.Event()

    async def lento(request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        await liberar.wait()
        return _novo_desfecho(request)

    caso, _, _, _ = _caso_de_uso(lento, _bateria_encerrada())
    estados = []
    async for item in caso.execute(benchmark_session_id="bench_1", question_id="Q1"):
        estados.append(item.finished)
        if len(estados) == 3:
            liberar.set()

    assert len(estados) >= 4
    assert estados[-1]


async def test_bateria_inexistente_e_recusada() -> None:
    caso, _, _, _ = _caso_de_uso(_acerta)

    with pytest.raises(BenchmarkSessionNotFoundError):
        await _coletar(caso)


async def test_bateria_em_execucao_e_recusada() -> None:
    caso, runner, _, _ = _caso_de_uso(_acerta, bateria("Q1"))

    with pytest.raises(BenchmarkSessionNotFinishedError):
        await _coletar(caso)
    assert runner.requests == []


async def test_questao_de_outra_bateria_e_recusada() -> None:
    caso, _, _, _ = _caso_de_uso(_acerta, _bateria_encerrada())

    with pytest.raises(InvalidBenchmarkRequestError, match="não pertence à bateria"):
        await _coletar(caso, question_id="Q9")


async def test_questao_removida_do_dataset_e_recusada() -> None:
    provider = FakeBenchmarkQuestionProvider([questao("Q2")])
    caso, _, _, _ = _caso_de_uso(_acerta, _bateria_encerrada(), provider=provider)

    with pytest.raises(InvalidBenchmarkRequestError, match="não existe mais no dataset"):
        await _coletar(caso)


async def test_revisao_diferente_do_dataset_e_recusada() -> None:
    sessao = _bateria_encerrada()
    sessao.benchmark = replace(sessao.benchmark, revision="vestibular-v0")
    caso, runner, _, _ = _caso_de_uso(_acerta, sessao)

    with pytest.raises(InvalidBenchmarkRequestError, match="vestibular-v0"):
        await _coletar(caso)
    assert runner.requests == []


async def test_questao_sem_fluxo_errado_e_recusada() -> None:
    caso, runner, _, _ = _caso_de_uso(_acerta, _bateria_encerrada(ralph_correto=True))

    with pytest.raises(BenchmarkQuestionNotRerunnableError, match="Q1"):
        await _coletar(caso)
    assert runner.requests == []


async def test_nao_roda_duas_reexecucoes_da_mesma_bateria_ao_mesmo_tempo() -> None:
    liberar = asyncio.Event()

    async def lento(request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        await liberar.wait()
        return _novo_desfecho(request)

    caso, _, repositorio, _ = _caso_de_uso(lento, _bateria_encerrada())
    primeira = caso.execute(benchmark_session_id="bench_1", question_id="Q1")
    await anext(primeira)

    with pytest.raises(BenchmarkSessionNotFinishedError):
        await _coletar(caso, question_id="Q2")

    liberar.set()
    restante = [item async for item in primeira]
    assert restante[-1].finished
    await _coletar(caso, question_id="Q2")
    assert repositorio.sessions["bench_1"].question("Q2").ralph.session_id == "Q2_ralph_nova"


async def test_cancelamento_cancela_o_fluxo_e_mantem_o_desfecho_anterior() -> None:
    iniciou = asyncio.Event()

    async def travado(request: BenchmarkFlowRequest, on_tokens: Callable[[int], None]) -> BenchmarkFlowOutcome:
        iniciou.set()
        await asyncio.Event().wait()
        raise AssertionError("não deveria terminar")

    caso, runner, repositorio, _ = _caso_de_uso(travado, _bateria_encerrada())
    geracao = caso.execute(benchmark_session_id="bench_1", question_id="Q1")
    await anext(geracao)
    await iniciou.wait()

    await geracao.aclose()

    assert len(runner.cancelled) == 1
    assert repositorio.save_attempts == 0
    assert repositorio.sessions["bench_1"].question("Q1").ralph.session_id == "Q1_ralph_antiga"
    await _coletar(_caso_de_uso(_acerta, repositorio.sessions["bench_1"])[0])


async def test_falha_ao_persistir_propaga_e_descarta_a_reexecucao_em_andamento() -> None:
    repositorio = InMemoryBenchmarkSessionRepository(failing_save_calls={1})
    caso, _, _, _ = _caso_de_uso(_acerta, _bateria_encerrada(), repositorio=repositorio)
    sessoes = []

    with pytest.raises(OSError, match="persistência indisponível"):
        async for item in caso.execute(benchmark_session_id="bench_1", question_id="Q1"):
            sessoes.append(item.benchmark_session)

    assert repositorio.sessions["bench_1"].question("Q1").ralph.session_id == "Q1_ralph_antiga"
    assert sessoes[-1].question("Q1").current_mode is None
    await _coletar(caso)


async def test_recusa_reexecutar_com_provider_de_outro_subconjunto() -> None:
    sessao = _bateria_encerrada()
    sessao.benchmark = replace(sessao.benchmark, split="main")
    caso, runner, _, _ = _caso_de_uso(_acerta, sessao)
    with pytest.raises(InvalidBenchmarkRequestError, match="Subconjunto"):
        await _coletar(caso)
    assert not runner.requests
