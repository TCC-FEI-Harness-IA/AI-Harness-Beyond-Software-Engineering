import uuid
from inspect import getfile
from pathlib import Path

from src.application.usecases.publish_official_results_usecase import PublishOfficialResultsUseCase
from src.application.usecases.select_official_batteries_usecase import SelectOfficialBatteriesUseCase
from src.domain.entities.publication.official_publication import OfficialPublication
from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum
from src.domain.interfaces.benchmark_source_interface import IBenchmarkSource
from src.domain.interfaces.publication_backup_interface import IPublicationBackup
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.adapters.mongo_client_adapter import MongoClientAdapter
from src.infra.config.settings import Settings
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.benchmark_session_repository_factory import BenchmarkSessionRepositoryFactory
from src.infra.repositories.official_publication_repository_factory import OfficialPublicationRepositoryFactory
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory
from src.infra.services.json_directory_publication_backup import JsonDirectoryPublicationBackup
from src.infra.services.mongo_publication_backup import MongoPublicationBackup
from src.infra.sources.legacy_json_benchmark_source import LegacyJsonBenchmarkSource
from src.infra.sources.legacy_mongo_benchmark_source import LegacyMongoBenchmarkSource
from src.infra.sources.owned_benchmark_source import OwnedBenchmarkSource

LEGACY_SOURCE = "legacy"
OWNER_PREFIX = "owner:"
_DEFAULT_BACKUP_DIR = "./data/backups/official"


class OfficialPublicationAdminStartup:
    """Composition root das operações administrativas sobre os resultados oficiais.

    A origem pessoal é sempre explícita: `legacy` (histórico sem dono, anterior às contas, no backend
    configurado) ou `owner:<user_id>` (as baterias de uma conta). Nunca "todas as contas".
    """

    def __init__(self, source_spec: str | None = None, backup_dir: str | None = None) -> None:
        """Monta origem, repositório oficial, backup e casos de uso.

        Args:
            source_spec: `legacy` ou `owner:<user_id>`; obrigatório para seleção e publicação.
            backup_dir: Diretório dos backups.

        Raises:
            ValueError: Quando a origem não é reconhecida.
        """
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)
        self.clock = ClockAdapter()
        self.benchmark_mapper = BenchmarkSessionDocumentMapper()
        self.session_mapper = SessionDocumentMapper()
        self.repository = OfficialPublicationRepositoryFactory(settings=self.settings).create()
        self.source = self.__source(source_spec) if source_spec is not None else None
        self.select_use_case = (
            SelectOfficialBatteriesUseCase(
                source=self.source, logger=self.settings.logger(module_file=getfile(SelectOfficialBatteriesUseCase))
            )
            if self.source is not None
            else None
        )
        self.publish_use_case = PublishOfficialResultsUseCase(
            repository=self.repository,
            backup=self.__backup(Path(backup_dir or _DEFAULT_BACKUP_DIR)),
            clock=self.clock,
            id_generator=lambda: f"pub_{uuid.uuid4().hex}",
            logger=self.settings.logger(module_file=getfile(PublishOfficialResultsUseCase)),
        )

    @property
    def is_mongodb(self) -> bool:
        """Informa se o armazenamento configurado é o MongoDB."""
        return self.settings.ralph_session_storage_backend is SessionStorageBackendEnum.MONGODB

    async def discover(self) -> list[str]:
        """Descreve o armazenamento efetivamente configurado e o que há nele."""
        lines = [f"Armazenamento configurado: {self.settings.ralph_session_storage_backend.value}"]
        if self.is_mongodb:
            client = MongoClientAdapter(settings=self.settings)
            without_owner = {"owner_id": {"$exists": False}}
            batteries = await client.benchmark_sessions_collection.count_documents(without_owner)
            sessions = await client.sessions_collection.count_documents(without_owner)
            lines.append(
                f"MongoDB '{self.settings.mongodb_database}': {batteries} baterias e "
                f"{sessions} sessões legadas (sem dono)"
            )
        else:
            benchmarks_dir = Path(self.settings.ralph_benchmark_sessions_storage_path)
            sessions_dir = Path(self.settings.ralph_sessions_storage_path)
            batteries = len(list(benchmarks_dir.glob("*.json"))) if benchmarks_dir.is_dir() else 0
            sessions = len(list(sessions_dir.glob("*.json"))) if sessions_dir.is_dir() else 0
            owners = benchmarks_dir / "owners"
            accounts = len([item for item in owners.iterdir() if item.is_dir()]) if owners.is_dir() else 0
            lines.append(f"Baterias legadas (sem dono) em '{benchmarks_dir}': {batteries} baterias")
            lines.append(f"Sessões legadas (sem dono) em '{sessions_dir}': {sessions} sessões")
            lines.append(f"Contas com baterias próprias: {accounts}")
            lines.append(f"Publicações oficiais em '{self.settings.ralph_official_storage_path}'")
        lines.append(f"Publicações oficiais existentes: {len(await self.repository.list_all())}")
        return lines

    async def list_publications(self) -> list[OfficialPublication]:
        """Todas as publicações, inclusive as substituídas."""
        return await self.repository.list_all()

    def __source(self, spec: str) -> IBenchmarkSource:
        if spec == LEGACY_SOURCE:
            if self.is_mongodb:
                client = MongoClientAdapter(settings=self.settings)
                return LegacyMongoBenchmarkSource(
                    benchmarks=client.benchmark_sessions_collection, sessions=client.sessions_collection,
                    benchmark_mapper=self.benchmark_mapper, session_mapper=self.session_mapper,
                )
            return LegacyJsonBenchmarkSource(
                benchmarks_dir=Path(self.settings.ralph_benchmark_sessions_storage_path),
                sessions_dir=Path(self.settings.ralph_sessions_storage_path),
                benchmark_mapper=self.benchmark_mapper, session_mapper=self.session_mapper,
            )
        if spec.startswith(OWNER_PREFIX) and len(spec) > len(OWNER_PREFIX):
            owner_id = spec[len(OWNER_PREFIX):]
            return OwnedBenchmarkSource(
                benchmark_repository=BenchmarkSessionRepositoryFactory(self.settings, self.benchmark_mapper).create(
                    owner_id
                ),
                session_repository=SessionRepositoryFactory(self.settings, self.session_mapper).create(owner_id),
                description=f"baterias da conta '{owner_id}' ({self.settings.ralph_session_storage_backend.value})",
                logger=self.logger,
            )
        raise ValueError(f"Origem pessoal desconhecida: '{spec}'. Use 'legacy' ou 'owner:<user_id>'.")

    def __backup(self, backup_dir: Path) -> IPublicationBackup:
        if self.is_mongodb:
            client = MongoClientAdapter(settings=self.settings)
            return MongoPublicationBackup(
                collections={
                    self.settings.mongodb_official_publications_collection: client.official_publications_collection,
                    self.settings.mongodb_official_sessions_collection: client.official_sessions_collection,
                },
                backup_root=backup_dir,
                clock=self.clock,
            )
        return JsonDirectoryPublicationBackup(
            source_dir=Path(self.settings.ralph_official_storage_path), backup_root=backup_dir, clock=self.clock
        )
