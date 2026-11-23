import asyncio
import json
import logging
import os
import re
from pathlib import Path

from src.domain.entities.session.session import Session
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper
from src.domain.interfaces.session_repository_interface import ISessionRepository
from src.domain.interfaces.settings_interface import ISettings

_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_DOCUMENT_SUFFIX = ".json"
_TEMPORARY_SUFFIX = ".tmp"
_DOCUMENT_INDENT = 2
_FILE_ENCODING = "utf-8"


class JsonFileSessionRepository(ISessionRepository):
    """Repositório de sessões apoiado em arquivos JSON locais.

    Grava um arquivo por sessão, de forma atômica: o documento vai primeiro para
    um arquivo temporário e só então substitui o destino, de modo que uma queda
    no meio da escrita nunca corrompe o conteúdo anterior. Todo o I/O é executado
    fora do event loop.
    """

    def __init__(self, mapper: ISessionDocumentMapper, settings: ISettings, logger: logging.Logger) -> None:
        """Inicializa o repositório.

        Args:
            mapper: Conversor entre `Session` e o documento persistido.
            settings: Configurações da aplicação, fonte do diretório de sessões.
            logger: Logger do módulo.
        """
        self.mapper: ISessionDocumentMapper = mapper
        self.settings: ISettings = settings
        self.logger = logger

    async def save(self, session: Session) -> None:
        """Persiste (insere ou substitui) a sessão inteira.

        Args:
            session: Sessão a ser persistida.

        Raises:
            ValueError: Quando o identificador da sessão é inválido.
        """
        self.__validate_session_id(session_id=session.id)
        payload = json.dumps(
            self.mapper.to_document(session=session),
            ensure_ascii=False,
            indent=_DOCUMENT_INDENT,
        )
        await asyncio.to_thread(self.__write_atomically, session.id, payload)
        self.logger.info("Sessão '%s' persistida", session.id)

    async def find_by_id(self, session_id: str) -> Session | None:
        """Busca uma sessão pelo identificador.

        Args:
            session_id: Identificador da sessão procurada.

        Returns:
            Session | None: Sessão encontrada, ou `None` quando não existe.

        Raises:
            ValueError: Quando o identificador é inválido ou o arquivo tem JSON inválido.
        """
        self.__validate_session_id(session_id=session_id)
        raw_document = await asyncio.to_thread(self.__read_raw_document, session_id)
        if raw_document is None:
            return None

        try:
            document = json.loads(raw_document)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Sessão '{session_id}' está gravada com JSON inválido.") from exc

        return self.mapper.from_document(document=document)

    async def list_ids(self) -> list[str]:
        """Lista os identificadores de todas as sessões persistidas.

        Returns:
            list[str]: Identificadores de sessão em ordem alfabética.
        """
        return await asyncio.to_thread(self.__list_ids_from_disk)

    async def delete(self, session_id: str) -> bool:
        """Remove uma sessão persistida.

        Args:
            session_id: Identificador da sessão a remover.

        Returns:
            bool: `True` quando a sessão existia e foi removida.

        Raises:
            ValueError: Quando o identificador é inválido.
        """
        self.__validate_session_id(session_id=session_id)
        return await asyncio.to_thread(self.__delete_from_disk, session_id)

    # ── I/O ──────────────────────────────────────────────────────────────────

    def __write_atomically(self, session_id: str, payload: str) -> None:
        """Grava o documento num arquivo temporário e o promove ao destino final."""
        storage_directory = self.__storage_directory()
        storage_directory.mkdir(parents=True, exist_ok=True)

        document_path = self.__document_path(session_id=session_id)
        temporary_path = document_path.with_name(f"{document_path.name}{_TEMPORARY_SUFFIX}")
        temporary_path.write_text(payload, encoding=_FILE_ENCODING)
        os.replace(temporary_path, document_path)

    def __read_raw_document(self, session_id: str) -> str | None:
        """Lê o conteúdo bruto do arquivo da sessão, ou `None` quando ele não existe."""
        document_path = self.__document_path(session_id=session_id)
        if not document_path.is_file():
            return None
        return document_path.read_text(encoding=_FILE_ENCODING)

    def __list_ids_from_disk(self) -> list[str]:
        """Lista os identificadores gravados, ignorando temporários e outras extensões."""
        storage_directory = self.__storage_directory()
        if not storage_directory.is_dir():
            return []

        return sorted(
            item.stem for item in storage_directory.iterdir() if item.is_file() and item.suffix == _DOCUMENT_SUFFIX
        )

    def __delete_from_disk(self, session_id: str) -> bool:
        """Remove o arquivo da sessão, informando se ele existia."""
        document_path = self.__document_path(session_id=session_id)
        if not document_path.is_file():
            return False

        document_path.unlink()
        return True

    # ── Apoio ────────────────────────────────────────────────────────────────

    def __storage_directory(self) -> Path:
        """Devolve o diretório configurado para os documentos de sessão."""
        return Path(self.settings.ralph_sessions_storage_path)

    def __document_path(self, session_id: str) -> Path:
        """Devolve o caminho do documento de uma sessão já validada."""
        return self.__storage_directory() / f"{session_id}{_DOCUMENT_SUFFIX}"

    def __validate_session_id(self, session_id: str) -> None:
        """Valida o identificador antes de qualquer acesso a disco.

        Raises:
            ValueError: Quando o identificador não é composto apenas por letras,
                dígitos, hífen e underline — o que permitiria *path traversal*.
        """
        if not _SESSION_ID_PATTERN.fullmatch(session_id):
            raise ValueError(f"Identificador de sessão inválido: '{session_id}'.")
