import logging
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.entities.publication.official_publication import OfficialPublication
from src.domain.entities.session.session import Session
from src.domain.interfaces.official_publication_repository_interface import IOfficialPublicationRepository
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper
from src.infra.mappers.official_publication_document_mapper import OfficialPublicationDocumentMapper


class MongoOfficialPublicationRepository(IOfficialPublicationRepository):
    """Publicações oficiais no MongoDB, em coleções próprias.

    `official_publications` guarda o manifesto com a bateria; `official_sessions` guarda as cópias
    das sessões com chave `<pub_id>/<session_id>`, de modo que uma sessão só é encontrada dentro da
    publicação a que pertence.
    """

    def __init__(
        self,
        publications: AsyncIOMotorCollection,
        sessions: AsyncIOMotorCollection,
        mapper: OfficialPublicationDocumentMapper,
        session_mapper: ISessionDocumentMapper,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o repositório."""
        self.publications = publications
        self.sessions = sessions
        self.mapper = mapper
        self.session_mapper = session_mapper
        self.logger = logger

    async def create(self, publication: OfficialPublication, sessions: list[Session]) -> None:
        """Grava as sessões e, por último, o manifesto."""
        for session in sessions:
            key = f"{publication.id}/{session.id}"
            await self.sessions.replace_one(
                {"_id": key},
                {
                    "_id": key,
                    "publication_id": publication.id,
                    "session": self.session_mapper.to_document(session=session),
                },
                upsert=True,
            )
        await self.publications.replace_one({"_id": publication.id}, self.mapper.to_document(publication), upsert=True)
        self.logger.info("Publicação oficial '%s' gravada com %d sessões", publication.id, len(sessions))

    async def find(self, publication_id: str) -> OfficialPublication | None:
        """Busca uma publicação."""
        document = await self.publications.find_one({"_id": publication_id})
        return None if document is None else self.mapper.from_document(document)

    async def list_all(self) -> list[OfficialPublication]:
        """Publicações, da mais recente para a mais antiga."""
        documents = await self.publications.find({}).to_list(length=None)
        publications = [self.mapper.from_document(document) for document in documents]
        return sorted(publications, key=lambda item: item.published_at, reverse=True)

    async def find_session(self, publication_id: str, session_id: str) -> Session | None:
        """Cópia de uma sessão filha da publicação."""
        document = await self.sessions.find_one({"_id": f"{publication_id}/{session_id}"})
        return None if document is None else self.session_mapper.from_document(document=document["session"])

    async def list_sessions(self, publication_id: str) -> list[Session]:
        """Todas as cópias de sessões da publicação."""
        documents = await self.sessions.find({"publication_id": publication_id}).to_list(length=None)
        return [self.session_mapper.from_document(document=item["session"]) for item in documents]

    async def mark_superseded(self, publication_id: str, superseded_by: str, at: datetime) -> None:
        """Marca a publicação como substituída."""
        await self.publications.update_one(
            {"_id": publication_id},
            {"$set": {"status": "superseded", "superseded_by": superseded_by, "superseded_at": at.isoformat()}},
        )
