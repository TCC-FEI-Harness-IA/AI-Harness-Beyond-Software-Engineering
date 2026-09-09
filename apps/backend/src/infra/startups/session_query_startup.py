from inspect import getfile

from src.application.usecases.get_session_usecase import GetSessionUseCase
from src.domain.interfaces.settings_interface import ISettings
from src.infra.config.settings import Settings
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.json_file_session_repository import JsonFileSessionRepository


class SessionQueryStartup:
    """Composition root da consulta de sessões persistidas."""

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências da consulta de sessões."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        self.session_document_mapper = SessionDocumentMapper()
        self.session_repository = JsonFileSessionRepository(
            mapper=self.session_document_mapper,
            settings=self.settings,
            logger=self.settings.logger(module_file=getfile(JsonFileSessionRepository)),
        )
        self.get_session_use_case = GetSessionUseCase(
            repository=self.session_repository,
            logger=self.settings.logger(module_file=getfile(GetSessionUseCase)),
        )
        self.logger.info("SessionQueryStartup inicializado")
