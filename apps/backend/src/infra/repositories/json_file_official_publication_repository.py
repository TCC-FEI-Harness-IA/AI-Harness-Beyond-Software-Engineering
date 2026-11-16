import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.domain.entities.publication.official_publication import OfficialPublication
from src.domain.entities.session.session import Session
from src.domain.interfaces.official_publication_repository_interface import IOfficialPublicationRepository
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper
from src.infra.mappers.official_publication_document_mapper import OfficialPublicationDocumentMapper

_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_MANIFEST = "publication.json"
_ENCODING = "utf-8"


class JsonFileOfficialPublicationRepository(IOfficialPublicationRepository):
    """Publicações oficiais em arquivos JSON, fora dos diretórios pessoais.

    Layout: `<base>/publications/<pub_id>/publication.json` e `.../sessions/<session_id>.json`. As
    sessões são gravadas antes do manifesto, então uma publicação só aparece quando está completa.
    Toda escrita é atômica (temporário seguido de `os.replace`).
    """

    def __init__(
        self,
        base_path: Path,
        mapper: OfficialPublicationDocumentMapper,
        session_mapper: ISessionDocumentMapper,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o repositório."""
        self.base_path = Path(base_path)
        self.mapper = mapper
        self.session_mapper = session_mapper
        self.logger = logger

    async def create(self, publication: OfficialPublication, sessions: list[Session]) -> None:
        """Grava as sessões e, por último, o manifesto."""
        directory = self.__publication_dir(publication.id)
        for session in sessions:
            self.__validate(session.id)
            await asyncio.to_thread(
                self.__write, directory / "sessions" / f"{session.id}.json",
                self.session_mapper.to_document(session=session),
            )
        await asyncio.to_thread(self.__write, directory / _MANIFEST, self.mapper.to_document(publication))
        self.logger.info("Publicação oficial '%s' gravada com %d sessões", publication.id, len(sessions))

    async def find(self, publication_id: str) -> OfficialPublication | None:
        """Busca uma publicação."""
        document = await asyncio.to_thread(self.__read, self.__publication_dir(publication_id) / _MANIFEST)
        return None if document is None else self.mapper.from_document(document)

    async def list_all(self) -> list[OfficialPublication]:
        """Publicações completas, da mais recente para a mais antiga."""
        documents = await asyncio.to_thread(self.__read_manifests)
        publications = [self.mapper.from_document(document) for document in documents]
        return sorted(publications, key=lambda item: item.published_at, reverse=True)

    async def find_session(self, publication_id: str, session_id: str) -> Session | None:
        """Cópia de uma sessão filha da publicação."""
        self.__validate(session_id)
        path = self.__publication_dir(publication_id) / "sessions" / f"{session_id}.json"
        document = await asyncio.to_thread(self.__read, path)
        return None if document is None else self.session_mapper.from_document(document=document)

    async def list_sessions(self, publication_id: str) -> list[Session]:
        """Todas as cópias de sessões da publicação."""
        directory = self.__publication_dir(publication_id) / "sessions"
        documents = await asyncio.to_thread(
            lambda: [self.__read(path) for path in sorted(directory.glob("*.json"))] if directory.is_dir() else []
        )
        return [self.session_mapper.from_document(document=document) for document in documents if document]

    async def mark_superseded(self, publication_id: str, superseded_by: str, at: datetime) -> None:
        """Reescreve só o manifesto, com o estado `superseded`."""
        publication = await self.find(publication_id)
        if publication is None:
            raise ValueError(f"Publicação '{publication_id}' não encontrada.")
        await asyncio.to_thread(
            self.__write,
            self.__publication_dir(publication_id) / _MANIFEST,
            self.mapper.to_document(publication.superseded(by=superseded_by, at=at)),
        )

    def __publication_dir(self, publication_id: str) -> Path:
        self.__validate(publication_id)
        return self.base_path / "publications" / publication_id

    @staticmethod
    def __validate(identifier: str) -> None:
        if not _ID_PATTERN.fullmatch(identifier):
            raise ValueError(f"Identificador inválido: '{identifier}'.")

    @staticmethod
    def __write(path: Path, document: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f"{path.name}.tmp")
        temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding=_ENCODING)
        os.replace(temporary, path)

    @staticmethod
    def __read(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding=_ENCODING))

    def __read_manifests(self) -> list[dict[str, Any]]:
        root = self.base_path / "publications"
        if not root.is_dir():
            return []
        return [
            json.loads((item / _MANIFEST).read_text(encoding=_ENCODING))
            for item in sorted(root.iterdir())
            if (item / _MANIFEST).is_file()
        ]
