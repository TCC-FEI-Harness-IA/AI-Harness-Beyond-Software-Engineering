import logging
from dataclasses import replace

import pytest

from src.application.usecases.import_benchmark_session_usecase import ImportBenchmarkSessionUseCase
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.entities.benchmark.benchmark_session_bundle import BenchmarkSessionBundle, BenchmarkSessionBundleItem
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_session_import_conflict_error import BenchmarkSessionImportConflictError
from src.domain.errors.invalid_benchmark_archive_error import InvalidBenchmarkArchiveError
from tests.doubles.benchmark_factories import CRIADO_EM, bateria, desfecho
from tests.doubles.in_memory_benchmark_session_repository import InMemoryBenchmarkSessionRepository
from tests.doubles.in_memory_session_repository import InMemorySessionRepository
from tests.doubles.session_factories import sessao_ralph

_SIMPLES = BenchmarkInferenceModeEnum.SIMPLE
_RALPH = BenchmarkInferenceModeEnum.RALPH
_LOGGER = logging.getLogger("teste.benchmark")


def _bateria(ralph_session_id: str | None = "q1_r", status=BenchmarkSessionStatusEnum.COMPLETED) -> BenchmarkSession:
    sessao = bateria("Q1", "Q2")
    for questao_id, simples, ralph in (
        ("Q1", "q1_s", ralph_session_id),
        ("Q2", "q2_s", "q2_r"),
    ):
        sessao.start_flow(question_id=questao_id, mode=_SIMPLES, at=CRIADO_EM)
        sessao.record_outcome(question_id=questao_id, outcome=desfecho(mode=_SIMPLES, session_id=simples), at=CRIADO_EM)
        sessao.start_flow(question_id=questao_id, mode=_RALPH, at=CRIADO_EM)
        sessao.record_outcome(question_id=questao_id, outcome=desfecho(mode=_RALPH, session_id=ralph), at=CRIADO_EM)
        sessao.finish_question(question_id=questao_id, at=CRIADO_EM)
    if status is not BenchmarkSessionStatusEnum.RUNNING:
        sessao.finish(status=status, at=CRIADO_EM, wall_time_ms=10)
    return sessao


def _pacote(benchmark: BenchmarkSession | None = None, **sobrescritas) -> BenchmarkSessionBundle:
    benchmark = benchmark or _bateria()
    itens = [
        BenchmarkSessionBundleItem(
            run=benchmark.questions[0], simple_session=sessao_ralph("q1_s"), ralph_session=sessao_ralph("q1_r")
        ),
        # Q2: a sessão do Ralph não existia mais quando a bateria foi exportada.
        BenchmarkSessionBundleItem(run=benchmark.questions[1], simple_session=sessao_ralph("q2_s")),
    ]
    return BenchmarkSessionBundle(benchmark_session=benchmark, items=sobrescritas.get("items", itens))


class _SessoesQueNaoApagam(InMemorySessionRepository):
    async def delete(self, session_id: str) -> bool:
        raise OSError("disco fora do ar")


def _caso(
    baterias: InMemoryBenchmarkSessionRepository | None = None,
    sessoes: InMemorySessionRepository | None = None,
) -> ImportBenchmarkSessionUseCase:
    return ImportBenchmarkSessionUseCase(
        benchmark_repository=baterias if baterias is not None else InMemoryBenchmarkSessionRepository(),
        session_repository=sessoes if sessoes is not None else InMemorySessionRepository(),
        logger=_LOGGER,
    )


async def test_grava_as_sessoes_e_depois_a_bateria() -> None:
    baterias, sessoes = InMemoryBenchmarkSessionRepository(), InMemorySessionRepository()
    pacote = _pacote()

    importada = await _caso(baterias, sessoes).execute(pacote)

    assert importada is pacote.benchmark_session
    assert sessoes.save_calls == ["q1_s", "q1_r", "q2_s"]
    assert await baterias.find_by_id("bench_1") == pacote.benchmark_session


async def test_recusa_bateria_em_execucao() -> None:
    with pytest.raises(InvalidBenchmarkArchiveError, match="em execução"):
        await _caso().execute(_pacote(_bateria(status=BenchmarkSessionStatusEnum.RUNNING)))


async def test_recusa_questoes_que_nao_correspondem_a_bateria() -> None:
    benchmark = _bateria()
    pacote = _pacote(benchmark, items=[BenchmarkSessionBundleItem(run=benchmark.questions[1])])

    with pytest.raises(InvalidBenchmarkArchiveError, match="questões"):
        await _caso().execute(pacote)


async def test_recusa_sessao_diferente_da_registrada_no_desfecho() -> None:
    benchmark = _bateria()
    pacote = _pacote(
        benchmark,
        items=[
            BenchmarkSessionBundleItem(run=benchmark.questions[0], ralph_session=sessao_ralph("intrusa")),
            BenchmarkSessionBundleItem(run=benchmark.questions[1]),
        ],
    )

    with pytest.raises(InvalidBenchmarkArchiveError, match="intrusa"):
        await _caso().execute(pacote)


async def test_recusa_sessao_de_fluxo_sem_desfecho() -> None:
    benchmark = _bateria()
    benchmark.questions[0] = replace(benchmark.questions[0], ralph=None)
    pacote = _pacote(
        benchmark,
        items=[
            BenchmarkSessionBundleItem(run=benchmark.questions[0], ralph_session=sessao_ralph("q1_r")),
            BenchmarkSessionBundleItem(run=benchmark.questions[1]),
        ],
    )

    with pytest.raises(InvalidBenchmarkArchiveError, match="Ralph Loop"):
        await _caso().execute(pacote)


async def test_recusa_a_mesma_sessao_em_dois_fluxos() -> None:
    benchmark = _bateria(ralph_session_id="q1_s")
    pacote = _pacote(
        benchmark,
        items=[
            BenchmarkSessionBundleItem(
                run=benchmark.questions[0], simple_session=sessao_ralph("q1_s"), ralph_session=sessao_ralph("q1_s")
            ),
            BenchmarkSessionBundleItem(run=benchmark.questions[1]),
        ],
    )

    with pytest.raises(InvalidBenchmarkArchiveError, match="repete"):
        await _caso().execute(pacote)


async def test_recusa_bateria_que_ja_existe_sem_gravar_nada() -> None:
    baterias, sessoes = InMemoryBenchmarkSessionRepository(), InMemorySessionRepository()
    await baterias.save(bateria())

    with pytest.raises(BenchmarkSessionImportConflictError) as erro:
        await _caso(baterias, sessoes).execute(_pacote())

    assert erro.value.conflicting_ids == ["bench_1"]
    assert sessoes.save_calls == []


async def test_recusa_sessao_que_ja_existe_sem_gravar_nada() -> None:
    baterias, sessoes = InMemoryBenchmarkSessionRepository(), InMemorySessionRepository()
    await sessoes.save(sessao_ralph("q1_r"))

    with pytest.raises(BenchmarkSessionImportConflictError) as erro:
        await _caso(baterias, sessoes).execute(_pacote())

    assert erro.value.conflicting_ids == ["q1_r"]
    assert sessoes.save_calls == ["q1_r"]
    assert baterias.sessions == {}


async def test_falha_ao_gravar_a_bateria_desfaz_as_sessoes_gravadas() -> None:
    baterias, sessoes = InMemoryBenchmarkSessionRepository(failing_save_calls={1}), InMemorySessionRepository()

    with pytest.raises(OSError):
        await _caso(baterias, sessoes).execute(_pacote())

    assert sessoes.sessions == {}


async def test_falha_ao_desfazer_nao_esconde_o_erro_original(caplog: pytest.LogCaptureFixture) -> None:
    sessoes = _SessoesQueNaoApagam(failing_save_calls={2})

    with pytest.raises(OSError, match="gravação 2"):
        await _caso(sessoes=sessoes).execute(_pacote())

    assert "q1_s" in caplog.text
