import asyncio
import json
import shutil
from pathlib import Path

from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.publication_backup_interface import IPublicationBackup


class JsonDirectoryPublicationBackup(IPublicationBackup):
    """Backup do armazenamento oficial em JSON: cópia integral do diretório antes da alteração."""

    def __init__(self, source_dir: Path, backup_root: Path, clock: IClock) -> None:
        """Inicializa o backup.

        Args:
            source_dir: Diretório das publicações oficiais.
            backup_root: Onde os backups são criados (um subdiretório por operação).
            clock: Fonte de tempo, para nomear o backup.
        """
        self.source_dir = Path(source_dir)
        self.backup_root = Path(backup_root)
        self.clock = clock

    async def backup(self, label: str) -> str:
        """Copia o diretório (ou registra que ele estava vazio) e devolve o destino."""
        destination = self.backup_root / f"{self.clock.now().strftime('%Y%m%dT%H%M%S%fZ')}-{label}"
        await asyncio.to_thread(self.__copy, destination)
        return str(destination)

    def __copy(self, destination: Path) -> None:
        if self.source_dir.is_dir():
            shutil.copytree(self.source_dir, destination)
            return
        destination.mkdir(parents=True)
        (destination / "EMPTY.json").write_text(json.dumps({"source": str(self.source_dir)}), encoding="utf-8")
