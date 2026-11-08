from inspect import getfile
from typing import Any

from src.application.usecases.get_session_usecase import GetSessionUseCase
from src.domain.interfaces.settings_interface import ISettings
from src.infra.config.settings import Settings
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory


class SessionQueryStartup:
    """Composition root da consulta de sessões persistidas."""

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências da consulta de sessões."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        self.session_document_mapper = SessionDocumentMapper()
        self.session_repository = SessionRepositoryFactory(
            settings=self.settings,
            mapper=self.session_document_mapper,
        ).create()
        self.get_session_use_case = GetSessionUseCase(
            repository=self.session_repository,
            logger=self.settings.logger(module_file=getfile(GetSessionUseCase)),
        )
        self.logger.info("SessionQueryStartup inicializado")

    async def get_session_document(self, session_id: str) -> dict[str, Any]:
        """Consulta uma sessão e devolve o documento que a representa.

        Args:
            session_id: Identificador da sessão procurada.

        Returns:
            dict[str, Any]: Documento da sessão, serializável em JSON.

        Raises:
            SessionNotFoundError: Quando a sessão não existe.
            ValueError: Quando o identificador é inválido.
        """
        self.logger.info("Consultando a sessão '%s'", session_id)

        session = await self.get_session_use_case.execute(session_id=session_id)
        return self.session_document_mapper.to_document(session=session)

    async def list_session_ids(self) -> list[str]:
        """Lista os identificadores de todas as sessões persistidas.

        Returns:
            list[str]: Identificadores de sessão em ordem alfabética.
        """
        self.logger.info("Listando as sessões persistidas")

        return await self.session_repository.list_ids()
