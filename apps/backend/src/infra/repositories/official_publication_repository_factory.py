from inspect import getfile
from pathlib import Path

from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum
from src.domain.interfaces.official_publication_repository_interface import IOfficialPublicationRepository
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.mongo_client_adapter import MongoClientAdapter
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.official_publication_document_mapper import OfficialPublicationDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.json_file_official_publication_repository import JsonFileOfficialPublicationRepository
from src.infra.repositories.mongo_official_publication_repository import MongoOfficialPublicationRepository


class OfficialPublicationRepositoryFactory:
    """Cria o repositório de publicações oficiais no mesmo backend configurado para as sessões."""

    def __init__(self, settings: ISettings) -> None:
        """Inicializa a fábrica."""
        self.settings = settings

    def create(self) -> IOfficialPublicationRepository:
        """Repositório JSON (`RALPH_OFFICIAL_STORAGE_PATH`) ou MongoDB (coleções oficiais)."""
        mapper = OfficialPublicationDocumentMapper(benchmark_mapper=BenchmarkSessionDocumentMapper())
        if self.settings.ralph_session_storage_backend is SessionStorageBackendEnum.MONGODB:
            client = MongoClientAdapter(settings=self.settings)
            return MongoOfficialPublicationRepository(
                publications=client.official_publications_collection,
                sessions=client.official_sessions_collection,
                mapper=mapper,
                session_mapper=SessionDocumentMapper(),
                logger=self.settings.logger(module_file=getfile(MongoOfficialPublicationRepository)),
            )
        return JsonFileOfficialPublicationRepository(
            base_path=Path(self.settings.ralph_official_storage_path),
            mapper=mapper,
            session_mapper=SessionDocumentMapper(),
            logger=self.settings.logger(module_file=getfile(JsonFileOfficialPublicationRepository)),
        )
