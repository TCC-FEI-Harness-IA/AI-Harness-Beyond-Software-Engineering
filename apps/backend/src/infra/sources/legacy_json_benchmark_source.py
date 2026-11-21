import asyncio
import json
import re
from pathlib import Path

from src.domain.entities.publication.source_battery import SourceBattery
from src.domain.entities.session.session import Session
from src.domain.interfaces.benchmark_session_document_mapper_interface import IBenchmarkSessionDocumentMapper
from src.domain.interfaces.benchmark_source_interface import IBenchmarkSource
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper

_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_ENCODING = "utf-8"


class LegacyJsonBenchmarkSource(IBenchmarkSource):
    """Histórico pessoal anterior às contas: arquivos JSON na raiz dos diretórios configurados.

    Lê só os arquivos da raiz (sem dono); os diretórios `owners/` das contas nunca são considerados.
    É somente leitura: nenhum arquivo é alterado.
    """

    def __init__(
        self,
        benchmarks_dir: Path,
        sessions_dir: Path,
        benchmark_mapper: IBenchmarkSessionDocumentMapper,
        session_mapper: ISessionDocumentMapper,
    ) -> None:
        """Inicializa a origem."""
        self.benchmarks_dir = Path(benchmarks_dir)
        self.sessions_dir = Path(sessions_dir)
        self.benchmark_mapper = benchmark_mapper
        self.session_mapper = session_mapper

    def describe(self) -> str:
        """Origem e caminhos efetivamente lidos."""
        return (
            f"histórico legado em JSON (sem dono): baterias em '{self.benchmarks_dir}', "
            f"sessões em '{self.sessions_dir}'"
        )

    async def list_batteries(self) -> list[SourceBattery]:
        """Baterias da raiz; um arquivo ilegível vira entrada com erro."""
        return await asyncio.to_thread(self.__read_batteries)

    async def find_session(self, session_id: str) -> Session | None:
        """Sessão da raiz do diretório de sessões.

        Raises:
            ValueError: Identificador inválido ou documento ilegível.
        """
        if not _ID_PATTERN.fullmatch(session_id):
            raise ValueError(f"Identificador de sessão inválido: '{session_id}'.")
        path = self.sessions_dir / f"{session_id}.json"
        raw = await asyncio.to_thread(lambda: path.read_text(encoding=_ENCODING) if path.is_file() else None)
        if raw is None:
            return None
        try:
            return self.session_mapper.from_document(document=json.loads(raw))
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError(f"documento inválido ({exc})") from exc

    def __read_batteries(self) -> list[SourceBattery]:
        if not self.benchmarks_dir.is_dir():
            return []
        entries: list[SourceBattery] = []
        for path in sorted(self.benchmarks_dir.glob("*.json")):
            try:
                battery = self.benchmark_mapper.from_document(document=json.loads(path.read_text(encoding=_ENCODING)))
                entries.append(SourceBattery(battery_id=path.stem, battery=battery))
            except (json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
                entries.append(SourceBattery(battery_id=path.stem, error=f"JSON ou documento inválido: {exc}"))
        return entries
