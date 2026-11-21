import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.interfaces.benchmark_session_document_mapper_interface import IBenchmarkSessionDocumentMapper
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository
from src.infra.repositories.owner_scope import OWNER_KEY, scoped_key, validate_owner_id

_DOCUMENT_ID_KEY = "_id"
_ID_KEY = "id"


class MongoBenchmarkSessionRepository(IBenchmarkSessionRepository):
    """Repositório de baterias de benchmark apoiado em uma coleção do MongoDB, escopado a um proprietário.

    A chave primária é `<owner_id>/<id>`. O alias é atualizado separadamente para ser preservado
    durante reexecuções de questões.
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        mapper: IBenchmarkSessionDocumentMapper,
        logger: logging.Logger,
        owner_id: str,
    ) -> None:
        """Inicializa o repositório.

        Args:
            collection: Coleção do MongoDB onde as baterias são gravadas.
            mapper: Conversor entre `BenchmarkSession` e o documento persistido.
            logger: Logger do módulo.
            owner_id: Conta dona das baterias desta instância.

        Raises:
            ValueError: Quando o proprietário é inválido.
        """
        self.collection: AsyncIOMotorCollection = collection
        self.mapper: IBenchmarkSessionDocumentMapper = mapper
        self.logger = logger
        self.owner_id = validate_owner_id(owner_id)

    async def save(self, benchmark_session: BenchmarkSession) -> None:
        """Persiste a bateria, preservando um alias já salvo pelo usuário.

        Args:
            benchmark_session: Bateria a ser persistida.
        """
        document = self.mapper.to_document(benchmark_session=benchmark_session)
        alias = document.pop("alias")
        document.pop(_DOCUMENT_ID_KEY)
        document[OWNER_KEY] = self.owner_id
        await self.collection.update_one(
            {_DOCUMENT_ID_KEY: scoped_key(self.owner_id, benchmark_session.id)},
            {"$set": document, "$setOnInsert": {"alias": alias}},
            upsert=True,
        )
        self.logger.info("Bateria '%s' persistida", benchmark_session.id)

    async def update_alias(self, benchmark_session: BenchmarkSession) -> None:
        """Altera apenas o alias, sem sobrescrever resultados de uma reexecução simultânea."""
        result = await self.collection.update_one(
            {_DOCUMENT_ID_KEY: scoped_key(self.owner_id, benchmark_session.id)},
            {"$set": {"alias": benchmark_session.alias, "updated_at": benchmark_session.updated_at.isoformat()}},
        )
        if result.matched_count == 0:
            raise BenchmarkSessionNotFoundError(benchmark_session_id=benchmark_session.id)

    async def find_by_id(self, benchmark_session_id: str) -> BenchmarkSession | None:
        """Busca uma bateria do proprietário pelo identificador.

        Args:
            benchmark_session_id: Identificador da bateria procurada.

        Returns:
            BenchmarkSession | None: Bateria encontrada, ou `None` quando não existe para esta conta.
        """
        document = await self.collection.find_one(
            {_DOCUMENT_ID_KEY: scoped_key(self.owner_id, benchmark_session_id)}
        )
        if document is None:
            return None
        return self.__from_document(document)

    async def list_all(self) -> list[BenchmarkSession]:
        """Lista as baterias do proprietário.

        Returns:
            list[BenchmarkSession]: Baterias, da mais recente para a mais antiga.
        """
        documents = await self.collection.find({OWNER_KEY: self.owner_id}).to_list(length=None)
        sessions = [self.__from_document(document) for document in documents]
        return sorted(sessions, key=lambda item: item.created_at, reverse=True)

    def __from_document(self, document: dict[str, Any]) -> BenchmarkSession:
        """Restaura o identificador original antes de converter."""
        return self.mapper.from_document(document={**document, _DOCUMENT_ID_KEY: document[_ID_KEY]})
