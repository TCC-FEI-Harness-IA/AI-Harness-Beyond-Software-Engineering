import logging

from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.entities.session.session import Session
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper
from src.domain.interfaces.session_repository_interface import ISessionRepository
from src.infra.repositories.owner_scope import OWNER_KEY, scoped_key, validate_owner_id

_DOCUMENT_ID_KEY = "_id"
_ID_KEY = "id"


class MongoSessionRepository(ISessionRepository):
    """Repositório de sessões apoiado em uma coleção do MongoDB, escopado a um proprietário.

    O documento é o produzido por `ISessionDocumentMapper`, acrescido de `owner_id`; a chave
    primária é `<owner_id>/<id>`, então contas diferentes nunca colidem e documentos legados (sem
    dono, com `_id` igual ao identificador) não aparecem em nenhuma consulta.
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        mapper: ISessionDocumentMapper,
        logger: logging.Logger,
        owner_id: str,
    ) -> None:
        """Inicializa o repositório.

        Args:
            collection: Coleção do MongoDB onde os documentos de sessão são gravados.
            mapper: Conversor entre `Session` e o documento persistido.
            logger: Logger do módulo.
            owner_id: Conta dona das sessões desta instância.

        Raises:
            ValueError: Quando o proprietário é inválido.
        """
        self.collection: AsyncIOMotorCollection = collection
        self.mapper: ISessionDocumentMapper = mapper
        self.logger = logger
        self.owner_id = validate_owner_id(owner_id)

    async def save(self, session: Session) -> None:
        """Persiste (insere ou substitui) a sessão inteira do proprietário.

        Args:
            session: Sessão a ser persistida.
        """
        key = scoped_key(self.owner_id, session.id)
        document = {**self.mapper.to_document(session=session), _DOCUMENT_ID_KEY: key, OWNER_KEY: self.owner_id}
        await self.collection.replace_one({_DOCUMENT_ID_KEY: key}, document, upsert=True)
        self.logger.info("Sessão '%s' persistida", session.id)

    async def find_by_id(self, session_id: str) -> Session | None:
        """Busca uma sessão do proprietário pelo identificador.

        Args:
            session_id: Identificador da sessão procurada.

        Returns:
            Session | None: Sessão encontrada, ou `None` quando não existe para esta conta.
        """
        document = await self.collection.find_one({_DOCUMENT_ID_KEY: scoped_key(self.owner_id, session_id)})
        if document is None:
            return None
        return self.mapper.from_document(document={**document, _DOCUMENT_ID_KEY: document[_ID_KEY]})

    async def list_ids(self) -> list[str]:
        """Lista os identificadores das sessões do proprietário.

        Returns:
            list[str]: Identificadores de sessão em ordem alfabética.
        """
        ids = await self.collection.distinct(_ID_KEY, {OWNER_KEY: self.owner_id})
        return sorted(ids)

    async def delete(self, session_id: str) -> bool:
        """Remove uma sessão do proprietário.

        Args:
            session_id: Identificador da sessão a remover.

        Returns:
            bool: `True` quando a sessão existia e foi removida.
        """
        result = await self.collection.delete_one({_DOCUMENT_ID_KEY: scoped_key(self.owner_id, session_id)})
        return result.deleted_count > 0
