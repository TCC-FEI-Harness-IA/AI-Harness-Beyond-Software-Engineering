import asyncio
import logging
from types import SimpleNamespace
from typing import Any, AsyncGenerator, Callable

import pytest

from src.domain.entities.benchmark.benchmark_flow_request import BenchmarkFlowRequest
from src.domain.entities.session.benchmark_details import BenchmarkDetails
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.services.benchmark_answer_evaluator import BenchmarkAnswerEvaluator
from src.infra.adapters.benchmark_flow_runner_adapter import BenchmarkFlowRunnerAdapter
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from tests.doubles.benchmark_factories import configuracao, questao
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_id_generator import FakeIdGenerator
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.in_memory_session_repository import InMemorySessionRepository

_SIMPLES = BenchmarkInferenceModeEnum.SIMPLE
_RALPH = BenchmarkInferenceModeEnum.RALPH


class _Ambiente:
    """Repositório compartilhado e os startups dublês criados durante o teste."""

    def __init__(self, failing_save_calls: set[int] | None = None) -> None:
        self.repository = InMemorySessionRepository(failing_save_calls=failing_save_calls)
        self.startups: list[Any] = []
        self.payloads: list[Any] = []

    def recorder(self, benchmark_details: BenchmarkDetails) -> SessionRecorderAdapter:
        return SessionRecorderAdapter(
            repository=self.repository,
            clock=FakeClock(),
            id_generator=FakeIdGenerator(session_prefix=f"sess{len(self.startups)}"),
            settings=FakeSettings(),
            logger=logging.getLogger("teste"),
            benchmark_details=benchmark_details,
        )


async def _iniciar(recorder: SessionRecorderAdapter, payload: Any) -> None:
    await recorder.start(
        user_question=payload.message.user_input,
        flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
        model_name=payload.llm_model_config.provider_config.model_name,
        max_tokens=payload.llm_model_config.max_tokens,
        temperature=payload.llm_model_config.temperature,
    )


def _fabrica_simples(ambiente: _Ambiente, resposta: str | Exception, iniciar: bool = True) -> Callable[..., Any]:
    def fabrica(benchmark_details: BenchmarkDetails) -> Any:
        recorder = ambiente.recorder(benchmark_details)

        async def run(payload: Any) -> Any:
            ambiente.payloads.append(payload)
            if iniciar:
                await _iniciar(recorder, payload)
            if isinstance(resposta, Exception):
                if iniciar:
                    await recorder.finish(status=SessionStatusEnum.FAILED, final_answer=None)
                raise resposta
            await recorder.finish(status=SessionStatusEnum.COMPLETED, final_answer=resposta)
            return SimpleNamespace(response=resposta)

        startup = SimpleNamespace(default_message_use_case=SimpleNamespace(session_recorder=recorder), run=run)
        ambiente.startups.append(startup)
        return startup

    return fabrica


def _fabrica_ralph(ambiente: _Ambiente, eventos: list[tuple[str, str, int]], erro: Exception | None = None):
    def fabrica(benchmark_details: BenchmarkDetails) -> Any:
        recorder = ambiente.recorder(benchmark_details)

        async def run(payload: Any) -> AsyncGenerator[Any, None]:
            ambiente.payloads.append(payload)
            await _iniciar(recorder, payload)
            for tipo, conteudo, tokens in eventos:
                yield SimpleNamespace(type=tipo, content=conteudo, total_tokens=tokens)
            if erro is not None:
                raise erro

        startup = SimpleNamespace(session_recorder=recorder, run=run)
        ambiente.startups.append(startup)
        return startup

    return fabrica


def _runner(simple: Callable[..., Any] | None = None, ralph: Callable[..., Any] | None = None):
    return BenchmarkFlowRunnerAdapter(
        evaluator=BenchmarkAnswerEvaluator(),
        clock=FakeClock(monotonic_values=[1000, 3500]),
        logger=logging.getLogger("teste"),
        simple_startup_factory=simple or (lambda **_: None),
        ralph_startup_factory=ralph or (lambda **_: None),
    )


def _pedido(mode: BenchmarkInferenceModeEnum) -> BenchmarkFlowRequest:
    return BenchmarkFlowRequest(
        question=questao("Q1", gabarito="A"),
        mode=mode,
        prompt="Pergunta\n\nInstrução",
        llm_config=configuracao(),
        benchmark_session_id="bench_1",
    )


async def test_simples_correto_grava_metadados_e_avaliacao_na_sessao() -> None:
    ambiente = _Ambiente()
    runner = _runner(simple=_fabrica_simples(ambiente, "RESPOSTA_FINAL: A"))

    desfecho = await runner.run(request=_pedido(_SIMPLES), on_tokens=lambda total: None)

    assert desfecho.is_correct is True
    assert desfecho.selected_alternative == "A"
    assert desfecho.duration_seconds == 2.5
    assert desfecho.session_id == "sess0_1"
    detalhes = ambiente.repository.sessions["sess0_1"].benchmark_details
    assert detalhes.is_banchmark is True
    assert detalhes.run_id == "bench_1"
    assert detalhes.corret_answer == "A) um"
    assert detalhes.inference_mode is _SIMPLES
    assert detalhes.providade_answer == "RESPOSTA_FINAL: A"
    assert detalhes.is_correct is True
    assert detalhes.duration_seconds == 2.5
    payload = ambiente.payloads[0]
    assert payload.message.user_input == "Pergunta\n\nInstrução"
    assert payload.llm_model_config.temperature == 0.0
    assert payload.llm_model_config.provider_config.model_name == "vendor/modelo"


async def test_falha_do_simples_vira_erro_avaliado() -> None:
    ambiente = _Ambiente()
    runner = _runner(simple=_fabrica_simples(ambiente, RuntimeError("provedor fora")))

    desfecho = await runner.run(request=_pedido(_SIMPLES), on_tokens=lambda total: None)

    assert desfecho.is_correct is False
    assert desfecho.error == "RuntimeError: provedor fora"
    assert ambiente.repository.sessions["sess0_1"].benchmark_details.providade_answer is None


async def test_fluxo_que_nem_cria_sessao_devolve_desfecho_sem_sessao() -> None:
    ambiente = _Ambiente()
    runner = _runner(simple=_fabrica_simples(ambiente, RuntimeError("payload recusado"), iniciar=False))

    desfecho = await runner.run(request=_pedido(_SIMPLES), on_tokens=lambda total: None)

    assert desfecho.session_id is None
    assert desfecho.total_tokens == 0
    assert desfecho.error == "RuntimeError: payload recusado"


async def test_ralph_usa_o_evento_result_e_informa_o_consumo() -> None:
    ambiente = _Ambiente()
    runner = _runner(
        ralph=_fabrica_ralph(ambiente, [("thinking", "pensando", 10), ("result", "RESPOSTA_FINAL: B", 30)])
    )
    consumos: list[int] = []

    desfecho = await runner.run(request=_pedido(_RALPH), on_tokens=consumos.append)

    assert consumos == [10, 30]
    assert desfecho.selected_alternative == "B"
    assert desfecho.is_correct is False
    assert desfecho.error is None


async def test_evento_error_do_ralph_vira_erro_avaliado() -> None:
    ambiente = _Ambiente()
    runner = _runner(ralph=_fabrica_ralph(ambiente, [("error", "limite de tentativas", 5)]))

    desfecho = await runner.run(request=_pedido(_RALPH), on_tokens=lambda total: None)

    assert desfecho.error == "limite de tentativas"


async def test_excecao_do_ralph_vira_erro_avaliado() -> None:
    ambiente = _Ambiente()
    runner = _runner(ralph=_fabrica_ralph(ambiente, [], erro=RuntimeError("quebrou")))

    desfecho = await runner.run(request=_pedido(_RALPH), on_tokens=lambda total: None)

    assert desfecho.error == "RuntimeError: quebrou"


async def test_ralph_sem_resposta_final_vira_erro_avaliado() -> None:
    ambiente = _Ambiente()
    runner = _runner(ralph=_fabrica_ralph(ambiente, [("thinking", "pensando", 5)]))

    desfecho = await runner.run(request=_pedido(_RALPH), on_tokens=lambda total: None)

    assert "sem emitir uma resposta final" in desfecho.error


async def test_falha_ao_persistir_a_avaliacao_nunca_vira_acerto() -> None:
    ambiente = _Ambiente(failing_save_calls={3})
    runner = _runner(simple=_fabrica_simples(ambiente, "A"))

    desfecho = await runner.run(request=_pedido(_SIMPLES), on_tokens=lambda total: None)

    assert desfecho.is_correct is False
    assert "Falha ao persistir avaliação" in desfecho.error


async def test_cancelamento_encerra_como_failed_a_sessao_em_execucao() -> None:
    ambiente = _Ambiente()
    iniciou = asyncio.Event()

    def fabrica(benchmark_details: BenchmarkDetails) -> Any:
        recorder = ambiente.recorder(benchmark_details)

        async def run(payload: Any) -> AsyncGenerator[Any, None]:
            await _iniciar(recorder, payload)
            iniciou.set()
            await asyncio.Event().wait()
            yield SimpleNamespace(type="result", content="A", total_tokens=0)

        return SimpleNamespace(session_recorder=recorder, run=run)

    tarefa = asyncio.create_task(_runner(ralph=fabrica).run(request=_pedido(_RALPH), on_tokens=lambda total: None))
    await iniciou.wait()
    tarefa.cancel()

    with pytest.raises(asyncio.CancelledError):
        await tarefa
    assert ambiente.repository.sessions["sess0_1"].status is SessionStatusEnum.FAILED


async def test_cancelamento_antes_de_criar_a_sessao_so_propaga() -> None:
    ambiente = _Ambiente()
    chamou = asyncio.Event()

    def fabrica(benchmark_details: BenchmarkDetails) -> Any:
        recorder = ambiente.recorder(benchmark_details)

        async def run(payload: Any) -> Any:
            chamou.set()
            await asyncio.Event().wait()

        return SimpleNamespace(default_message_use_case=SimpleNamespace(session_recorder=recorder), run=run)

    tarefa = asyncio.create_task(_runner(simple=fabrica).run(request=_pedido(_SIMPLES), on_tokens=lambda total: None))
    await chamou.wait()
    tarefa.cancel()

    with pytest.raises(asyncio.CancelledError):
        await tarefa
    assert ambiente.repository.sessions == {}


async def test_cancelamento_com_sessao_ja_encerrada_nao_a_encerra_de_novo() -> None:
    ambiente = _Ambiente()
    encerrou = asyncio.Event()

    def fabrica(benchmark_details: BenchmarkDetails) -> Any:
        recorder = ambiente.recorder(benchmark_details)

        async def run(payload: Any) -> AsyncGenerator[Any, None]:
            await _iniciar(recorder, payload)
            await recorder.finish(status=SessionStatusEnum.COMPLETED, final_answer="A")
            encerrou.set()
            await asyncio.Event().wait()
            yield SimpleNamespace(type="result", content="A", total_tokens=0)

        return SimpleNamespace(session_recorder=recorder, run=run)

    tarefa = asyncio.create_task(_runner(ralph=fabrica).run(request=_pedido(_RALPH), on_tokens=lambda total: None))
    await encerrou.wait()
    tarefa.cancel()

    with pytest.raises(asyncio.CancelledError):
        await tarefa
    assert ambiente.repository.sessions["sess0_1"].status is SessionStatusEnum.COMPLETED


def test_por_padrao_usa_os_composition_roots_da_api() -> None:
    from src.infra.startups.default_message_startup import DefaultMessageStartup
    from src.infra.startups.ralph_thinking_startup import RalphThinkingStartup

    runner = BenchmarkFlowRunnerAdapter(
        evaluator=BenchmarkAnswerEvaluator(), clock=FakeClock(), logger=logging.getLogger("teste")
    )

    assert runner.simple_startup_factory is DefaultMessageStartup
    assert runner.ralph_startup_factory is RalphThinkingStartup
