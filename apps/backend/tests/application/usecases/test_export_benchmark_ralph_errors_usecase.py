import logging

import pytest

from src.application.usecases.export_benchmark_ralph_errors_usecase import ExportBenchmarkRalphErrorsUseCase
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.errors.no_benchmark_errors_to_export_error import NoBenchmarkErrorsToExportError
from tests.doubles.benchmark_factories import CRIADO_EM, bateria, desfecho, questao
from tests.doubles.fake_benchmark_question_provider import FakeBenchmarkQuestionProvider
from tests.doubles.in_memory_benchmark_session_repository import InMemoryBenchmarkSessionRepository
from tests.doubles.in_memory_session_repository import InMemorySessionRepository
from tests.doubles.session_factories import sessao_ralph

_SIMPLES = BenchmarkInferenceModeEnum.SIMPLE
_RALPH = BenchmarkInferenceModeEnum.RALPH
_LOGGER = logging.getLogger("teste.benchmark")


def _caso(
    baterias: InMemoryBenchmarkSessionRepository,
    sessoes: InMemorySessionRepository | None = None,
    questoes: list[str] | None = None,
) -> ExportBenchmarkRalphErrorsUseCase:
    return ExportBenchmarkRalphErrorsUseCase(
        benchmark_repository=baterias,
        session_repository=sessoes or InMemorySessionRepository(),
        question_provider=FakeBenchmarkQuestionProvider([questao(item) for item in (questoes or ["Q1", "Q2", "Q3"])]),
        logger=_LOGGER,
    )


def _executar(sessao, questao_id: str, simples, ralph) -> None:
    sessao.start_flow(question_id=questao_id, mode=_SIMPLES, at=CRIADO_EM)
    sessao.record_outcome(question_id=questao_id, outcome=simples, at=CRIADO_EM)
    sessao.start_flow(question_id=questao_id, mode=_RALPH, at=CRIADO_EM)
    sessao.record_outcome(question_id=questao_id, outcome=ralph, at=CRIADO_EM)
    sessao.finish_question(question_id=questao_id, at=CRIADO_EM)


async def _bateria_encerrada(repositorio: InMemoryBenchmarkSessionRepository):
    sessao = bateria("Q1", "Q2", "Q3")
    # Q1: Ralph erra, mesmo com o simples certo. Q2: Ralph acerta, mesmo com o simples errado.
    _executar(
        sessao, "Q1", desfecho(mode=_SIMPLES, session_id="s1_simples"),
        desfecho(mode=_RALPH, correto=False, session_id="sess_1"),
    )
    _executar(
        sessao, "Q2", desfecho(mode=_SIMPLES, correto=False, session_id="s2_simples"),
        desfecho(mode=_RALPH, session_id="s2_ralph"),
    )
    # Q3: falha técnica do Ralph, sem sessão persistida.
    _executar(
        sessao, "Q3", desfecho(mode=_SIMPLES, correto=False, session_id="s3_simples"),
        desfecho(mode=_RALPH, correto=False, erro="provedor fora do ar", session_id=None),
    )
    sessao.finish(status=BenchmarkSessionStatusEnum.COMPLETED, at=CRIADO_EM, wall_time_ms=10)
    await repositorio.save(sessao)
    return sessao


async def test_reune_somente_as_questoes_erradas_no_ralph_na_ordem_da_bateria() -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    await _bateria_encerrada(baterias)
    sessoes = InMemorySessionRepository()
    await sessoes.save(sessao_ralph("sess_1", "Q1"))

    erros = await _caso(baterias, sessoes).execute("bench_1")

    assert [erro.question_id for erro in erros] == ["Q1", "Q3"]
    assert erros[0].expected_alternative == "A"
    assert erros[0].outcome.mode is _RALPH
    assert erros[0].question == questao("Q1")
    assert erros[0].session is not None and erros[0].session.id == "sess_1"


async def test_falha_tecnica_sem_sessao_persistida_tambem_e_exportada() -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    await _bateria_encerrada(baterias)

    erros = await _caso(baterias, InMemorySessionRepository()).execute("bench_1")

    assert [erro.question_id for erro in erros] == ["Q1", "Q3"]
    assert erros[0].session is None  # sessão apagada do armazenamento
    assert erros[1].outcome.error == "provedor fora do ar"
    assert erros[1].session is None


async def test_questao_que_saiu_do_dataset_continua_exportavel_sem_enunciado() -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    await _bateria_encerrada(baterias)

    erros = await _caso(baterias, questoes=["Q2", "Q3"]).execute("bench_1")

    assert [erro.question for erro in erros] == [None, questao("Q3")]


@pytest.mark.parametrize(
    "status", [BenchmarkSessionStatusEnum.FAILED, BenchmarkSessionStatusEnum.INTERRUPTED]
)
async def test_bateria_encerrada_sem_concluir_exporta_os_erros_ja_registrados(
    status: BenchmarkSessionStatusEnum,
) -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    sessao = bateria("Q1", "Q2")
    _executar(sessao, "Q1", desfecho(mode=_SIMPLES), desfecho(mode=_RALPH, correto=False))
    sessao.start_flow(question_id="Q2", mode=_SIMPLES, at=CRIADO_EM)
    sessao.finish(status=status, at=CRIADO_EM, wall_time_ms=10)
    await baterias.save(sessao)

    erros = await _caso(baterias).execute("bench_1")

    assert [erro.question_id for erro in erros] == ["Q1"]


async def test_bateria_inexistente_e_recusada() -> None:
    with pytest.raises(BenchmarkSessionNotFoundError):
        await _caso(InMemoryBenchmarkSessionRepository()).execute("bench_9")


async def test_bateria_em_execucao_e_recusada() -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    sessao = bateria("Q1")
    _executar(sessao, "Q1", desfecho(mode=_SIMPLES), desfecho(mode=_RALPH, correto=False))
    await baterias.save(sessao)

    with pytest.raises(BenchmarkSessionNotFinishedError):
        await _caso(baterias).execute("bench_1")


async def test_bateria_sem_erros_do_ralph_e_recusada() -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    sessao = bateria("Q1", "Q2")
    # Q1: só o simples errou. Q2: o Ralph nem chegou a executar.
    _executar(sessao, "Q1", desfecho(mode=_SIMPLES, correto=False), desfecho(mode=_RALPH))
    sessao.finish(status=BenchmarkSessionStatusEnum.INTERRUPTED, at=CRIADO_EM, wall_time_ms=10)
    await baterias.save(sessao)

    with pytest.raises(NoBenchmarkErrorsToExportError):
        await _caso(baterias).execute("bench_1")
