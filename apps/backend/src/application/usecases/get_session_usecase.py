import logging

from src.domain.entities.session.session import Session
from src.domain.interfaces.session_repository_interface import ISessionRepository


class GetSessionUseCase:
    """Consulta de uma sessão persistida pelo identificador."""

    def __init__(self, repository: ISessionRepository, logger: logging.Logger) -> None:
        """Inicializa o caso de uso.

        Args:
            repository: Repositório de persistência de sessões.
            logger: Logger do módulo.
        """
        self.repository: ISessionRepository = repository
        self.logger = logger

    async def execute(self, session_id: str) -> Session:
        """Busca a sessão pelo identificador informado.

        Args:
            session_id: Identificador da sessão procurada.

        Returns:
            Session: Sessão encontrada.

        Raises:
            SessionNotFoundError: Quando a sessão não existe.
        """
        raise NotImplementedError
