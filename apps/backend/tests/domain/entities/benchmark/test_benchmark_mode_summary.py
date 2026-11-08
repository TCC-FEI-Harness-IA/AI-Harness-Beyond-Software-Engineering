from src.domain.entities.benchmark.benchmark_mode_summary import BenchmarkModeSummary
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from tests.doubles.benchmark_factories import desfecho

_RALPH = BenchmarkInferenceModeEnum.RALPH


def test_agrega_acertos_erros_falhas_tokens_e_duracao() -> None:
    resumo = BenchmarkModeSummary.from_outcomes(
        mode=_RALPH,
        outcomes=[
            desfecho(mode=_RALPH, tokens=10, duracao=1.25),
            desfecho(mode=_RALPH, correto=False, tokens=20, duracao=2.0),
            desfecho(mode=_RALPH, correto=False, erro="falha", tokens=5, duracao=0.5),
        ],
    )

    assert (resumo.executed, resumo.correct, resumo.wrong, resumo.failures) == (3, 1, 2, 1)
    assert resumo.total_tokens == 35
    assert resumo.duration_seconds == 3.75
    assert resumo.accuracy == 1 / 3


def test_sem_desfechos_tem_acuracia_zero() -> None:
    resumo = BenchmarkModeSummary.from_outcomes(mode=_RALPH, outcomes=[])

    assert resumo.executed == 0
    assert resumo.accuracy == 0.0
