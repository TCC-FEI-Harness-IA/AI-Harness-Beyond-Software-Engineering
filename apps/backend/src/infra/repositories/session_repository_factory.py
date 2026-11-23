from inspect import getfile

from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper
from src.domain.interfaces.session_repository_interface import ISessionRepository
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.mongo_client_adapter import MongoClientAdapter
from src.infra.repositories.json_file_session_repository import JsonFileSessionRepository
from src.infra.repositories.mongo_session_repository import MongoSessionRepository


class SessionRepositoryFactory:
    """Instancia o `ISessionRepository` correspondente ao backend configurado.

    O mesmo documento (produzido por `ISessionDocumentMapper`) é gravado em qualquer
    backend, então trocar `RALPH_SESSION_STORAGE_BACKEND` nunca exige migração de dados
    além da própria cópia dos arquivos para o MongoDB (ou vice-versa).
    """

    def __init__(self, settings: ISettings, mapper: ISessionDocumentMapper) -> None:
        """Inicializa a fábrica.

        Args:
            settings: Configurações da aplicação, fonte do backend escolhido.
            mapper: Conversor entre `Session` e o documento persistido.
        """
        self.settings: ISettings = settings
        self.mapper: ISessionDocumentMapper = mapper

    def create(self) -> ISessionRepository:
        """Cria o repositório de sessões do backend configurado.

        Returns:
            ISessionRepository: `JsonFileSessionRepository` ou `MongoSessionRepository`,
            conforme `ISettings.ralph_session_storage_backend`.
        """
        if self.settings.ralph_session_storage_backend is SessionStorageBackendEnum.MONGODB:
            mongo_client = MongoClientAdapter(settings=self.settings)
            return MongoSessionRepository(
                collection=mongo_client.sessions_collection,
                mapper=self.mapper,
                logger=self.settings.logger(module_file=getfile(MongoSessionRepository)),
            )

        return JsonFileSessionRepository(
            mapper=self.mapper,
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(JsonFileSessionRepository)),
        )
