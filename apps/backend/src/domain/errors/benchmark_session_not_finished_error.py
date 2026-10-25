from src.domain.errors.ralph_error import RalphError


class BenchmarkSessionNotFinishedError(RalphError):
    """Levantado quando se pede o resultado de uma bateria de benchmark que ainda está em execução.

    Attributes:
        benchmark_session_id: Identificador da bateria em execução.
    """

    def __init__(self, benchmark_session_id: str) -> None:
        """Inicializa o erro.

        Args:
            benchmark_session_id: Identificador da bateria em execução.
        """
        self.benchmark_session_id = benchmark_session_id
        super().__init__(f"A bateria de benchmark '{benchmark_session_id}' ainda está em execução.")
