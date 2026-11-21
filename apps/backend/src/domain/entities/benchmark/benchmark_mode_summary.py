from dataclasses import dataclass

from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum


@dataclass(frozen=True)
class BenchmarkModeSummary:
    """Totais de um fluxo dentro da bateria.

    Attributes:
        mode: Fluxo resumido.
        executed: Quantidade de questões em que o fluxo terminou.
        correct: Acertos.
        wrong: Erros, incluindo falhas técnicas e respostas inválidas.
        failures: Subconjunto dos erros causado por falha técnica ou resposta inválida.
        total_tokens: Tokens consumidos pelas sessões do fluxo.
        duration_seconds: Soma das durações do fluxo, em segundos.
    """

    mode: BenchmarkInferenceModeEnum
    executed: int = 0
    correct: int = 0
    wrong: int = 0
    failures: int = 0
    total_tokens: int = 0
    duration_seconds: float = 0.0

    @property
    def accuracy(self) -> float:
        """Fração de acertos entre as questões executadas pelo fluxo.

        Returns:
            float: Valor entre 0 e 1; zero quando nada foi executado.
        """
        return self.correct / self.executed if self.executed else 0.0

    @classmethod
    def from_outcomes(
        cls,
        mode: BenchmarkInferenceModeEnum,
        outcomes: list[BenchmarkFlowOutcome],
    ) -> "BenchmarkModeSummary":
        """Agrega os desfechos de um fluxo.

        Args:
            mode: Fluxo resumido.
            outcomes: Desfechos já registrados do fluxo.

        Returns:
            BenchmarkModeSummary: Totais do fluxo.
        """
        correct = sum(outcome.is_correct for outcome in outcomes)
        return cls(
            mode=mode,
            executed=len(outcomes),
            correct=correct,
            wrong=len(outcomes) - correct,
            failures=sum(outcome.failed for outcome in outcomes),
            total_tokens=sum(outcome.total_tokens for outcome in outcomes),
            duration_seconds=round(sum(outcome.duration_seconds for outcome in outcomes), 3),
        )
