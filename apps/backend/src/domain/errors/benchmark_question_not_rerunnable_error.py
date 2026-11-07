from src.domain.errors.ralph_error import RalphError


class BenchmarkQuestionNotRerunnableError(RalphError):
    """Levantado quando se pede reexecutar uma questão que não tem fluxo errado para refazer.

    Attributes:
        benchmark_session_id: Identificador da bateria.
        question_id: Identificador da questão.
    """

    def __init__(self, benchmark_session_id: str, question_id: str) -> None:
        """Inicializa o erro.

        Args:
            benchmark_session_id: Identificador da bateria.
            question_id: Identificador da questão.
        """
        self.benchmark_session_id = benchmark_session_id
        self.question_id = question_id
        super().__init__(
            f"A questão '{question_id}' da bateria '{benchmark_session_id}' não tem fluxo errado ou com falha "
            "para reexecutar."
        )
