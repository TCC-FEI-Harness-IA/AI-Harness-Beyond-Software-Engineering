from src.domain.errors.ralph_error import RalphError


class NoBenchmarkErrorsToExportError(RalphError):
    """Levantado quando a bateria não tem nenhuma questão errada no Ralph Loop para exportar.

    Attributes:
        benchmark_session_id: Identificador da bateria sem erros a exportar.
    """

    def __init__(self, benchmark_session_id: str) -> None:
        """Inicializa o erro.

        Args:
            benchmark_session_id: Identificador da bateria sem erros a exportar.
        """
        self.benchmark_session_id = benchmark_session_id
        super().__init__(f"A bateria de benchmark '{benchmark_session_id}' não tem erros do Ralph Loop para exportar.")
