import logging

from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.interfaces.benchmark_session_document_mapper_interface import IBenchmarkSessionDocumentMapper
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository

_DOCUMENT_ID_KEY = "_id"


class MongoBenchmarkSessionRepository(IBenchmarkSessionRepository):
    """Repositório de baterias de benchmark apoiado em uma coleção do MongoDB.

    O documento gravado é exatamente o produzido por `IBenchmarkSessionDocumentMapper`, cuja chave
    `_id` já é o identificador da bateria.
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        mapper: IBenchmarkSessionDocumentMapper,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o repositório.

        Args:
            collection: Coleção do MongoDB onde as baterias são gravadas.
            mapper: Conversor entre `BenchmarkSession` e o documento persistido.
            logger: Logger do módulo.
        """
        self.collection: AsyncIOMotorCollection = collection
        self.mapper: IBenchmarkSessionDocumentMapper = mapper
        self.logger = logger

    async def save(self, benchmark_session: BenchmarkSession) -> None:
        """Persiste (insere ou substitui) a bateria inteira.

        Args:
            benchmark_session: Bateria a ser persistida.
        """
        document = self.mapper.to_document(benchmark_session=benchmark_session)
        await self.collection.replace_one({_DOCUMENT_ID_KEY: benchmark_session.id}, document, upsert=True)
        self.logger.info("Bateria '%s' persistida", benchmark_session.id)

    async def find_by_id(self, benchmark_session_id: str) -> BenchmarkSession | None:
        """Busca uma bateria pelo identificador.

        Args:
            benchmark_session_id: Identificador da bateria procurada.

        Returns:
            BenchmarkSession | None: Bateria encontrada, ou `None` quando não existe.
        """
        document = await self.collection.find_one({_DOCUMENT_ID_KEY: benchmark_session_id})
        if document is None:
            return None
        return self.mapper.from_document(document=document)

    async def list_all(self) -> list[BenchmarkSession]:
        """Lista todas as baterias persistidas.

        Returns:
            list[BenchmarkSession]: Baterias, da mais recente para a mais antiga.
        """
        documents = await self.collection.find({}).to_list(length=None)
        sessions = [self.mapper.from_document(document=document) for document in documents]
        return sorted(sessions, key=lambda item: item.created_at, reverse=True)
