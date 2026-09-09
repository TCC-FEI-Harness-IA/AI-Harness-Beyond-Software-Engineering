import logging

from src.domain.entities.session.session import Session
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper
from src.domain.interfaces.session_repository_interface import ISessionRepository
from src.domain.interfaces.settings_interface import ISettings


class JsonFileSessionRepository(ISessionRepository):
    """Repositório de sessões apoiado em arquivos JSON locais."""

    def __init__(self, mapper: ISessionDocumentMapper, settings: ISettings, logger: logging.Logger) -> None:
        """Inicializa o repositório.

        Args:
            mapper: Conversor entre `Session` e o documento persistido.
            settings: Configurações da aplicação, fonte do diretório de sessões.
            logger: Logger do módulo.
        """
        self.mapper: ISessionDocumentMapper = mapper
        self.settings: ISettings = settings
        self.logger = logger

    async def save(self, session: Session) -> None:
        """Persiste (insere ou substitui) a sessão inteira.

        Args:
            session: Sessão a ser persistida.
        """
        raise NotImplementedError

    async def find_by_id(self, session_id: str) -> Session | None:
        """Busca uma sessão pelo identificador.

        Args:
            session_id: Identificador da sessão procurada.

        Returns:
            Session | None: Sessão encontrada, ou `None` quando não existe.
        """
        raise NotImplementedError

    async def list_ids(self) -> list[str]:
        """Lista os identificadores de todas as sessões persistidas.

        Returns:
            list[str]: Identificadores de sessão.
        """
        raise NotImplementedError

    async def delete(self, session_id: str) -> bool:
        """Remove uma sessão persistida.

        Args:
            session_id: Identificador da sessão a remover.

        Returns:
            bool: `True` quando a sessão existia e foi removida.
        """
        raise NotImplementedError
