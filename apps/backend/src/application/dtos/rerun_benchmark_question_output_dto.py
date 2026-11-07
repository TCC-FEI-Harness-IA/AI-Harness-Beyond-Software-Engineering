from dataclasses import dataclass

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession


@dataclass(frozen=True)
class RerunBenchmarkQuestionOutputDTO:
    """Estado da bateria durante a reexecução de uma questão.

    Attributes:
        benchmark_session: Estado atual da bateria.
        finished: `True` no último estado emitido, quando a reexecução terminou.
    """

    benchmark_session: BenchmarkSession
    finished: bool
