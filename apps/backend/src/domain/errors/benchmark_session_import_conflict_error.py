from src.domain.errors.ralph_error import RalphError


class BenchmarkSessionImportConflictError(RalphError):
    """Levantado quando a bateria importada, ou alguma das suas sessões, já existe.

    A importação nunca sobrescreve dados: quem quiser reimportar precisa remover os existentes.

    Attributes:
        benchmark_session_id: Identificador da bateria importada.
        conflicting_ids: Identificadores (bateria ou sessões) que já existem.
    """

    def __init__(self, benchmark_session_id: str, conflicting_ids: list[str]) -> None:
        """Inicializa o erro.

        Args:
            benchmark_session_id: Identificador da bateria importada.
            conflicting_ids: Identificadores que já existem.
        """
        self.benchmark_session_id = benchmark_session_id
        self.conflicting_ids = list(conflicting_ids)
        if conflicting_ids == [benchmark_session_id]:
            message = f"A bateria de benchmark '{benchmark_session_id}' já existe; a importação foi cancelada."
        else:
            listed = ", ".join(f"'{item}'" for item in conflicting_ids)
            message = (
                f"A importação da bateria '{benchmark_session_id}' foi cancelada: já existem os registros {listed}."
            )
        super().__init__(message)
