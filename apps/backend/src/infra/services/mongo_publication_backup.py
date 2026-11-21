import asyncio
import json
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.publication_backup_interface import IPublicationBackup


class MongoPublicationBackup(IPublicationBackup):
    """Backup das coleções oficiais do MongoDB num arquivo JSON, antes da alteração."""

    def __init__(self, collections: dict[str, AsyncIOMotorCollection], backup_root: Path, clock: IClock) -> None:
        """Inicializa o backup.

        Args:
            collections: Coleções a exportar, pelo nome.
            backup_root: Diretório dos arquivos de backup.
            clock: Fonte de tempo, para nomear o arquivo.
        """
        self.collections = collections
        self.backup_root = Path(backup_root)
        self.clock = clock

    async def backup(self, label: str) -> str:
        """Exporta todos os documentos e devolve o caminho do arquivo."""
        content = {
            name: await collection.find({}).to_list(length=None) for name, collection in self.collections.items()
        }
        destination = self.backup_root / f"{self.clock.now().strftime('%Y%m%dT%H%M%S%fZ')}-{label}.json"
        await asyncio.to_thread(self.__write, destination, content)
        return str(destination)

    @staticmethod
    def __write(destination: Path, content: dict) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(content, ensure_ascii=False, default=str), encoding="utf-8")
