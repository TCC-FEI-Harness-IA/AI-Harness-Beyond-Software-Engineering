from dataclasses import dataclass

from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum


@dataclass(frozen=True)
class BenchmarkFlowOutcome:
    """Desfecho de um fluxo (simples ou Ralph) para uma questão do benchmark.

    Attributes:
        mode: Fluxo executado.
        session_id: Sessão persistida pelo fluxo, ou `None` quando ela nem chegou a ser criada.
        selected_alternative: Letra identificada na resposta, ou `None`.
        is_correct: Acerto; falhas técnicas e respostas inválidas contam como erro.
        error: Diagnóstico de falha técnica ou de resposta inválida, quando houve.
        duration_seconds: Duração do fluxo, em segundos.
        total_tokens: Tokens consumidos pela sessão do fluxo.
    """

    mode: BenchmarkInferenceModeEnum
    session_id: str | None
    selected_alternative: str | None
    is_correct: bool
    error: str | None
    duration_seconds: float
    total_tokens: int

    @property
    def failed(self) -> bool:
        """Informa se o fluxo terminou com falha técnica ou resposta inválida.

        Returns:
            bool: `True` quando há diagnóstico de erro.
        """
        return self.error is not None
