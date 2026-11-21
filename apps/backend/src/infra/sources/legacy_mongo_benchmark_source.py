from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.entities.publication.source_battery import SourceBattery
from src.domain.entities.session.session import Session
from src.domain.interfaces.benchmark_session_document_mapper_interface import IBenchmarkSessionDocumentMapper
from src.domain.interfaces.benchmark_source_interface import IBenchmarkSource
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper

_WITHOUT_OWNER = {"owner_id": {"$exists": False}}


class LegacyMongoBenchmarkSource(IBenchmarkSource):
    """Histórico pessoal anterior às contas no MongoDB: documentos sem `owner_id` (somente leitura)."""

    def __init__(
        self,
        benchmarks: AsyncIOMotorCollection,
        sessions: AsyncIOMotorCollection,
        benchmark_mapper: IBenchmarkSessionDocumentMapper,
        session_mapper: ISessionDocumentMapper,
    ) -> None:
        """Inicializa a origem."""
        self.benchmarks = benchmarks
        self.sessions = sessions
        self.benchmark_mapper = benchmark_mapper
        self.session_mapper = session_mapper

    def describe(self) -> str:
        """Origem e coleções efetivamente lidas."""
        return (
            f"histórico legado no MongoDB (documentos sem dono): baterias em '{self.benchmarks.name}', "
            f"sessões em '{self.sessions.name}'"
        )

    async def list_batteries(self) -> list[SourceBattery]:
        """Baterias sem dono; um documento inválido vira entrada com erro."""
        entries: list[SourceBattery] = []
        for document in await self.benchmarks.find(_WITHOUT_OWNER).sort("_id", 1).to_list(length=None):
            try:
                battery = self.benchmark_mapper.from_document(document=document)
                entries.append(SourceBattery(battery_id=document["_id"], battery=battery))
            except (ValueError, KeyError, TypeError) as exc:
                entries.append(SourceBattery(battery_id=document["_id"], error=f"documento inválido: {exc}"))
        return entries

    async def find_session(self, session_id: str) -> Session | None:
        """Sessão sem dono.

        Raises:
            ValueError: Documento inválido.
        """
        document = await self.sessions.find_one({"_id": session_id, **_WITHOUT_OWNER})
        if document is None:
            return None
        return self.session_mapper.from_document(document=document)
