from src.domain.entities.benchmark.benchmark_question_run import BenchmarkQuestionRun
from src.domain.entities.benchmark.benchmark_session_bundle import BenchmarkSessionBundle, BenchmarkSessionBundleItem
from tests.doubles.benchmark_factories import bateria
from tests.doubles.session_factories import sessao_ralph


def test_pacote_lista_as_sessoes_presentes_na_ordem_da_bateria() -> None:
    simples, ralph, outra = sessao_ralph("s1"), sessao_ralph("r1"), sessao_ralph("r2")
    pacote = BenchmarkSessionBundle(
        benchmark_session=bateria("Q1", "Q2"),
        items=[
            BenchmarkSessionBundleItem(
                run=BenchmarkQuestionRun("Q1", "A"), simple_session=simples, ralph_session=ralph
            ),
            BenchmarkSessionBundleItem(run=BenchmarkQuestionRun("Q2", "A"), ralph_session=outra),
        ],
    )

    assert [sessao.id for sessao in pacote.items[0].sessions] == ["s1", "r1"]
    assert [sessao.id for sessao in pacote.sessions] == ["s1", "r1", "r2"]


def test_pacote_sem_questoes_nao_tem_sessoes() -> None:
    assert BenchmarkSessionBundle(benchmark_session=bateria()).sessions == []
