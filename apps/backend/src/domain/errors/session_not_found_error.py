from src.domain.errors.ralph_error import RalphError


class SessionNotFoundError(RalphError):
    """Levantado quando uma sessão consultada não existe.

    Attributes:
        session_id: Identificador da sessão procurada.
    """

    def __init__(self, session_id: str) -> None:
        """Inicializa o erro.

        Args:
            session_id: Identificador da sessão procurada.
        """
        self.session_id = session_id
        super().__init__(f"Sessão '{session_id}' não encontrada.")
