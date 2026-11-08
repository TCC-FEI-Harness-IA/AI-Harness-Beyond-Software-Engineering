import logging

from src.domain.entities.session.session import Session
from src.domain.errors.session_not_found_error import SessionNotFoundError
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
        try:
            self.logger.info("Iniciando execução de GetSessionUseCase")

            session = await self.repository.find_by_id(session_id=session_id)
            if session is None:
                raise SessionNotFoundError(session_id=session_id)

            return session
        except SessionNotFoundError:
            self.logger.info("Sessão '%s' não encontrada", session_id)
            raise
        except Exception:
            self.logger.exception("Erro ao executar GetSessionUseCase")
            raise
