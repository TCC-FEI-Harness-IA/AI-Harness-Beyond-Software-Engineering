from inspect import getfile

from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum
from src.domain.interfaces.benchmark_session_document_mapper_interface import IBenchmarkSessionDocumentMapper
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.mongo_client_adapter import MongoClientAdapter
from src.infra.repositories.json_file_benchmark_session_repository import JsonFileBenchmarkSessionRepository
from src.infra.repositories.mongo_benchmark_session_repository import MongoBenchmarkSessionRepository


class BenchmarkSessionRepositoryFactory:
    """Instancia o `IBenchmarkSessionRepository` do mesmo backend configurado para as sessões.

    As baterias ficam junto das sessões que agrupam: em `RALPH_BENCHMARK_SESSIONS_STORAGE_PATH`
    quando o backend é `json_file`, ou em `MONGODB_BENCHMARK_SESSIONS_COLLECTION` no MongoDB.
    """

    def __init__(self, settings: ISettings, mapper: IBenchmarkSessionDocumentMapper) -> None:
        """Inicializa a fábrica.

        Args:
            settings: Configurações da aplicação, fonte do backend escolhido.
            mapper: Conversor entre `BenchmarkSession` e o documento persistido.
        """
        self.settings: ISettings = settings
        self.mapper: IBenchmarkSessionDocumentMapper = mapper

    def create(self) -> IBenchmarkSessionRepository:
        """Cria o repositório de baterias do backend configurado.

        Returns:
            IBenchmarkSessionRepository: Repositório JSON ou MongoDB, conforme
            `ISettings.ralph_session_storage_backend`.
        """
        if self.settings.ralph_session_storage_backend is SessionStorageBackendEnum.MONGODB:
            mongo_client = MongoClientAdapter(settings=self.settings)
            return MongoBenchmarkSessionRepository(
                collection=mongo_client.benchmark_sessions_collection,
                mapper=self.mapper,
                logger=self.settings.logger(module_file=getfile(MongoBenchmarkSessionRepository)),
            )

        return JsonFileBenchmarkSessionRepository(
            mapper=self.mapper,
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(JsonFileBenchmarkSessionRepository)),
        )
