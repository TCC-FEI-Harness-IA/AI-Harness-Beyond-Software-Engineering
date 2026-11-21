import logging
from dataclasses import replace

import pytest

from src.application.usecases.export_benchmark_session_usecase import ExportBenchmarkSessionUseCase
from src.domain.entities.benchmark.benchmark_definition import BenchmarkDefinition
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider
from tests.doubles.benchmark_factories import CRIADO_EM, bateria, desfecho, questao
from tests.doubles.fake_benchmark_question_provider import FakeBenchmarkQuestionProvider
from tests.doubles.in_memory_benchmark_session_repository import InMemoryBenchmarkSessionRepository
from tests.doubles.in_memory_session_repository import InMemorySessionRepository
from tests.doubles.session_factories import sessao_ralph

_SIMPLES = BenchmarkInferenceModeEnum.SIMPLE
_RALPH = BenchmarkInferenceModeEnum.RALPH
_LOGGER = logging.getLogger("teste.benchmark")


class _ProvedorComDefinicao(FakeBenchmarkQuestionProvider):
    """Provedor dublê que declara a revisão e o split disponíveis."""

    def __init__(self, definicao: BenchmarkDefinition) -> None:
        super().__init__([questao("Q1"), questao("Q2")])
        self.definicao = definicao

    def definition(self) -> BenchmarkDefinition:
        return self.definicao


def _caso(
    baterias: InMemoryBenchmarkSessionRepository,
    sessoes: InMemorySessionRepository | None = None,
    provedor: IBenchmarkQuestionProvider | None = None,
    pedidos: list[BenchmarkDefinition] | None = None,
) -> ExportBenchmarkSessionUseCase:
    escolhido = provedor or FakeBenchmarkQuestionProvider([questao("Q1"), questao("Q2"), questao("Q3")])

    def provedor_para(definicao: BenchmarkDefinition) -> IBenchmarkQuestionProvider:
        if pedidos is not None:
            pedidos.append(definicao)
        return escolhido

    return ExportBenchmarkSessionUseCase(
        benchmark_repository=baterias,
        session_repository=sessoes or InMemorySessionRepository(),
        question_provider_for=provedor_para,
        logger=_LOGGER,
    )


def _executar(sessao: BenchmarkSession, questao_id: str, simples, ralph) -> None:
    sessao.start_flow(question_id=questao_id, mode=_SIMPLES, at=CRIADO_EM)
    sessao.record_outcome(question_id=questao_id, outcome=simples, at=CRIADO_EM)
    if ralph is not None:
        sessao.start_flow(question_id=questao_id, mode=_RALPH, at=CRIADO_EM)
        sessao.record_outcome(question_id=questao_id, outcome=ralph, at=CRIADO_EM)


async def _bateria_encerrada(repositorio: InMemoryBenchmarkSessionRepository, **definicao) -> BenchmarkSession:
    sessao = bateria("Q1", "Q2", "Q3")
    if definicao:
        sessao.benchmark = BenchmarkDefinition(**definicao)
    _executar(sessao, "Q1", desfecho(mode=_SIMPLES, session_id="q1_s"), desfecho(mode=_RALPH, session_id="q1_r"))
    sessao.finish_question(question_id="Q1", at=CRIADO_EM)
    # Q2: o Ralph falhou antes de criar a sessão.
    _executar(
        sessao, "Q2", desfecho(mode=_SIMPLES, session_id="q2_s"),
        desfecho(mode=_RALPH, correto=False, erro="provedor fora do ar", session_id=None),
    )
    sessao.finish_question(question_id="Q2", at=CRIADO_EM)
    # Q3: interrompida depois do simples, cuja sessão foi apagada.
    _executar(sessao, "Q3", desfecho(mode=_SIMPLES, session_id="q3_s"), None)
    sessao.finish(status=BenchmarkSessionStatusEnum.INTERRUPTED, at=CRIADO_EM, wall_time_ms=10)
    await repositorio.save(sessao)
    return sessao


async def test_reune_a_bateria_com_questao_gabarito_e_as_duas_sessoes_de_cada_questao() -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    gravada = await _bateria_encerrada(baterias)
    sessoes = InMemorySessionRepository()
    for identificador in ("q1_s", "q1_r", "q2_s"):
        await sessoes.save(sessao_ralph(identificador))
    pedidos: list[BenchmarkDefinition] = []

    pacote = await _caso(baterias, sessoes, pedidos=pedidos).execute("bench_1")

    assert pacote.benchmark_session == gravada
    assert pedidos == [gravada.benchmark]
    assert [item.run.question_id for item in pacote.items] == ["Q1", "Q2", "Q3"]
    assert [item.question for item in pacote.items] == [questao("Q1"), questao("Q2"), questao("Q3")]
    assert [
        (
            item.simple_session.id if item.simple_session else None,
            item.ralph_session.id if item.ralph_session else None,
        )
        for item in pacote.items
    ] == [("q1_s", "q1_r"), ("q2_s", None), (None, None)]


async def test_questao_fora_do_dataset_vem_sem_enunciado() -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    await _bateria_encerrada(baterias)

    pacote = await _caso(baterias, provedor=FakeBenchmarkQuestionProvider([questao("Q1")])).execute("bench_1")

    assert [item.question is not None for item in pacote.items] == [True, False, False]


async def test_dataset_indisponivel_exporta_sem_enunciados() -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    await _bateria_encerrada(baterias)

    class _Quebrado(FakeBenchmarkQuestionProvider):
        def list_questions(self):
            raise FileNotFoundError("dataset ausente")

    pacote = await _caso(baterias, provedor=_Quebrado([])).execute("bench_1")

    assert all(item.question is None for item in pacote.items)


@pytest.mark.parametrize(
    "disponivel",
    [
        BenchmarkDefinition(dataset=BenchmarkDatasetEnum.MMLU, revision="outra", split="test"),
        BenchmarkDefinition(dataset=BenchmarkDatasetEnum.MMLU, revision="mmlu-v1", split="dev"),
    ],
)
async def test_revisao_ou_split_diferentes_exportam_sem_enunciados(disponivel: BenchmarkDefinition) -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    await _bateria_encerrada(baterias, dataset=BenchmarkDatasetEnum.MMLU, revision="mmlu-v1", split="test")

    pacote = await _caso(baterias, provedor=_ProvedorComDefinicao(disponivel)).execute("bench_1")

    assert all(item.question is None for item in pacote.items)


async def test_mesma_revisao_de_outro_dataset_traz_os_enunciados() -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    definicao = BenchmarkDefinition(dataset=BenchmarkDatasetEnum.MMLU, revision="mmlu-v1", split="test")
    await _bateria_encerrada(baterias, dataset=definicao.dataset, revision=definicao.revision, split=definicao.split)

    pacote = await _caso(baterias, provedor=_ProvedorComDefinicao(replace(definicao))).execute("bench_1")

    assert [item.question is not None for item in pacote.items] == [True, True, False]


async def test_recusa_bateria_inexistente() -> None:
    with pytest.raises(BenchmarkSessionNotFoundError):
        await _caso(InMemoryBenchmarkSessionRepository()).execute("bench_9")


async def test_recusa_bateria_em_execucao() -> None:
    baterias = InMemoryBenchmarkSessionRepository()
    await baterias.save(bateria("Q1"))

    with pytest.raises(BenchmarkSessionNotFinishedError):
        await _caso(baterias).execute("bench_1")
