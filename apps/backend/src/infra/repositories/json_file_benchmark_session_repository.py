import asyncio
import json
import logging
import os
import re
from pathlib import Path

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.interfaces.benchmark_session_document_mapper_interface import IBenchmarkSessionDocumentMapper
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository
from src.domain.interfaces.settings_interface import ISettings

_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_DOCUMENT_SUFFIX = ".json"
_TEMPORARY_SUFFIX = ".tmp"
_DOCUMENT_INDENT = 2
_FILE_ENCODING = "utf-8"


class JsonFileBenchmarkSessionRepository(IBenchmarkSessionRepository):
    """Repositório de baterias de benchmark apoiado em arquivos JSON locais.

    Segue o mesmo protocolo de `JsonFileSessionRepository`: um arquivo por bateria, gravado de
    forma atômica (temporário seguido de `os.replace`) e com todo o I/O fora do event loop.
    """

    def __init__(self, mapper: IBenchmarkSessionDocumentMapper, settings: ISettings, logger: logging.Logger) -> None:
        """Inicializa o repositório.

        Args:
            mapper: Conversor entre `BenchmarkSession` e o documento persistido.
            settings: Configurações da aplicação, fonte do diretório das baterias.
            logger: Logger do módulo.
        """
        self.mapper: IBenchmarkSessionDocumentMapper = mapper
        self.settings: ISettings = settings
        self.logger = logger

    async def save(self, benchmark_session: BenchmarkSession) -> None:
        """Persiste (insere ou substitui) a bateria inteira.

        Args:
            benchmark_session: Bateria a ser persistida.

        Raises:
            ValueError: Quando o identificador da bateria é inválido.
        """
        self.__validate_id(benchmark_session_id=benchmark_session.id)
        payload = json.dumps(
            self.mapper.to_document(benchmark_session=benchmark_session),
            ensure_ascii=False,
            indent=_DOCUMENT_INDENT,
        )
        await asyncio.to_thread(self.__write_atomically, benchmark_session.id, payload)
        self.logger.info("Bateria '%s' persistida", benchmark_session.id)

    async def find_by_id(self, benchmark_session_id: str) -> BenchmarkSession | None:
        """Busca uma bateria pelo identificador.

        Args:
            benchmark_session_id: Identificador da bateria procurada.

        Returns:
            BenchmarkSession | None: Bateria encontrada, ou `None` quando não existe.

        Raises:
            ValueError: Quando o identificador é inválido ou o arquivo tem JSON inválido.
        """
        self.__validate_id(benchmark_session_id=benchmark_session_id)
        raw_document = await asyncio.to_thread(self.__read_raw_document, self.__document_path(benchmark_session_id))
        if raw_document is None:
            return None
        return self.__parse(raw_document=raw_document, name=benchmark_session_id)

    async def list_all(self) -> list[BenchmarkSession]:
        """Lista todas as baterias persistidas.

        Returns:
            list[BenchmarkSession]: Baterias, da mais recente para a mais antiga.

        Raises:
            ValueError: Quando algum arquivo tem JSON ou documento inválido.
        """
        raw_documents = await asyncio.to_thread(self.__read_all_raw_documents)
        sessions = [self.__parse(raw_document=raw, name=name) for name, raw in raw_documents]
        return sorted(sessions, key=lambda item: item.created_at, reverse=True)

    # ── I/O ──────────────────────────────────────────────────────────────────

    def __write_atomically(self, benchmark_session_id: str, payload: str) -> None:
        """Grava o documento num arquivo temporário e o promove ao destino final."""
        self.__storage_directory().mkdir(parents=True, exist_ok=True)
        document_path = self.__document_path(benchmark_session_id)
        temporary_path = document_path.with_name(f"{document_path.name}{_TEMPORARY_SUFFIX}")
        temporary_path.write_text(payload, encoding=_FILE_ENCODING)
        os.replace(temporary_path, document_path)

    def __read_raw_document(self, document_path: Path) -> str | None:
        """Lê o conteúdo bruto de um arquivo, ou `None` quando ele não existe."""
        if not document_path.is_file():
            return None
        return document_path.read_text(encoding=_FILE_ENCODING)

    def __read_all_raw_documents(self) -> list[tuple[str, str]]:
        """Lê todos os documentos gravados, ignorando temporários e outras extensões."""
        storage_directory = self.__storage_directory()
        if not storage_directory.is_dir():
            return []
        return [
            (item.stem, item.read_text(encoding=_FILE_ENCODING))
            for item in sorted(storage_directory.iterdir())
            if item.is_file() and item.suffix == _DOCUMENT_SUFFIX
        ]

    # ── Apoio ────────────────────────────────────────────────────────────────

    def __parse(self, raw_document: str, name: str) -> BenchmarkSession:
        """Converte o JSON bruto de um arquivo em bateria.

        Raises:
            ValueError: Quando o conteúdo não é JSON válido.
        """
        try:
            document = json.loads(raw_document)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Bateria '{name}' está gravada com JSON inválido.") from exc
        return self.mapper.from_document(document=document)

    def __storage_directory(self) -> Path:
        """Devolve o diretório configurado para as baterias."""
        return Path(self.settings.ralph_benchmark_sessions_storage_path)

    def __document_path(self, benchmark_session_id: str) -> Path:
        """Devolve o caminho do documento de uma bateria já validada."""
        return self.__storage_directory() / f"{benchmark_session_id}{_DOCUMENT_SUFFIX}"

    def __validate_id(self, benchmark_session_id: str) -> None:
        """Valida o identificador antes de qualquer acesso a disco.

        Raises:
            ValueError: Quando o identificador não é composto apenas por letras, dígitos, hífen e
                underline — o que permitiria *path traversal*.
        """
        if not _ID_PATTERN.fullmatch(benchmark_session_id):
            raise ValueError(f"Identificador de bateria inválido: '{benchmark_session_id}'.")
