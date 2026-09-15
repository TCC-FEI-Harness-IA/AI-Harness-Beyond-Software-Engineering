import logging

from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.entities.session.session import Session
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper
from src.domain.interfaces.session_repository_interface import ISessionRepository

_DOCUMENT_ID_KEY = "_id"


class MongoSessionRepository(ISessionRepository):
    """Repositório de sessões apoiado em uma coleção do MongoDB.

    O documento gravado é exatamente o produzido por `ISessionDocumentMapper`, cuja
    chave `_id` já é o identificador da sessão — não há tradução extra de esquema.
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        mapper: ISessionDocumentMapper,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o repositório.

        Args:
            collection: Coleção do MongoDB onde os documentos de sessão são gravados.
            mapper: Conversor entre `Session` e o documento persistido.
            logger: Logger do módulo.
        """
        self.collection: AsyncIOMotorCollection = collection
        self.mapper: ISessionDocumentMapper = mapper
        self.logger = logger

    async def save(self, session: Session) -> None:
        """Persiste (insere ou substitui) a sessão inteira.

        Args:
            session: Sessão a ser persistida.
        """
        document = self.mapper.to_document(session=session)
        await self.collection.replace_one({_DOCUMENT_ID_KEY: session.id}, document, upsert=True)
        self.logger.info("Sessão '%s' persistida", session.id)

    async def find_by_id(self, session_id: str) -> Session | None:
        """Busca uma sessão pelo identificador.

        Args:
            session_id: Identificador da sessão procurada.

        Returns:
            Session | None: Sessão encontrada, ou `None` quando não existe.
        """
        document = await self.collection.find_one({_DOCUMENT_ID_KEY: session_id})
        if document is None:
            return None
        return self.mapper.from_document(document=document)

    async def list_ids(self) -> list[str]:
        """Lista os identificadores de todas as sessões persistidas.

        Returns:
            list[str]: Identificadores de sessão em ordem alfabética.
        """
        ids = await self.collection.distinct(_DOCUMENT_ID_KEY)
        return sorted(ids)

    async def delete(self, session_id: str) -> bool:
        """Remove uma sessão persistida.

        Args:
            session_id: Identificador da sessão a remover.

        Returns:
            bool: `True` quando a sessão existia e foi removida.
        """
        result = await self.collection.delete_one({_DOCUMENT_ID_KEY: session_id})
        return result.deleted_count > 0
