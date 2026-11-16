from typing import Any

from src.application.usecases.get_official_publication_usecase import GetOfficialPublicationUseCase
from src.domain.entities.publication.official_publication import OfficialPublication
from src.domain.interfaces.settings_interface import ISettings
from src.infra.config.settings import Settings
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.official_publication_repository_factory import OfficialPublicationRepositoryFactory
from src.infra.services.public_session_redactor import PublicSessionRedactor


class PublicBenchmarkStartup:
    """Composition root das consultas públicas dos resultados oficiais (sem autenticação e sem LLM)."""

    def __init__(self) -> None:
        """Monta repositório oficial, caso de uso e conversores."""
        self.settings: ISettings = Settings()
        self.use_case = GetOfficialPublicationUseCase(
            repository=OfficialPublicationRepositoryFactory(settings=self.settings).create()
        )
        self.benchmark_mapper = BenchmarkSessionDocumentMapper()
        self.session_mapper = SessionDocumentMapper()
        self.redactor = PublicSessionRedactor()

    async def list_publications(self) -> list[dict[str, Any]]:
        """Publicações vigentes, no formato público."""
        return [self.__view(item) for item in await self.use_case.list_active()]

    async def get_publication(self, publication_id: str) -> dict[str, Any]:
        """Uma publicação, no formato público."""
        return self.__view(await self.use_case.get(publication_id))

    async def get_session(self, publication_id: str, session_id: str) -> dict[str, Any]:
        """Sessão filha da publicação, com textos omitidos quando o dataset exige."""
        publication, session = await self.use_case.get_session(publication_id, session_id)
        document = self.session_mapper.to_document(session=session)
        return self.redactor.redact(document) if self.__redacted(publication) else document

    def __redacted(self, publication: OfficialPublication) -> bool:
        return publication.dataset.value in self.settings.ralph_public_redacted_datasets

    def __view(self, publication: OfficialPublication) -> dict[str, Any]:
        """Formato público: sem quem publicou nem a origem pessoal."""
        return {
            "id": publication.id,
            "dataset": publication.dataset.value,
            "status": publication.status.value,
            "published_at": publication.published_at.isoformat(),
            "supersedes": publication.supersedes,
            "superseded_by": publication.superseded_by,
            "superseded_at": publication.superseded_at.isoformat() if publication.superseded_at else None,
            "source_benchmark_session_id": publication.source_benchmark_session_id,
            "text_redacted": self.__redacted(publication),
            "benchmark_session": self.benchmark_mapper.to_document(benchmark_session=publication.benchmark_session),
        }
