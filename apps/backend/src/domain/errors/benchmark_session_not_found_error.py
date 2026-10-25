from src.domain.errors.ralph_error import RalphError


class BenchmarkSessionNotFoundError(RalphError):
    """Levantado quando uma bateria de benchmark consultada não existe.

    Attributes:
        benchmark_session_id: Identificador da bateria procurada.
    """

    def __init__(self, benchmark_session_id: str) -> None:
        """Inicializa o erro.

        Args:
            benchmark_session_id: Identificador da bateria procurada.
        """
        self.benchmark_session_id = benchmark_session_id
        super().__init__(f"Bateria de benchmark '{benchmark_session_id}' não encontrada.")
