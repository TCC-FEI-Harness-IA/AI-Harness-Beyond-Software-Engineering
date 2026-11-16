import json
from pathlib import Path

from mongomock_motor import AsyncMongoMockClient

from src.infra.services.json_directory_publication_backup import JsonDirectoryPublicationBackup
from src.infra.services.mongo_publication_backup import MongoPublicationBackup
from tests.doubles.controllable_clock import ControllableClock


async def test_backup_json_copia_o_diretorio_oficial(tmp_path: Path) -> None:
    oficial = tmp_path / "official"
    (oficial / "publications" / "pub_1").mkdir(parents=True)
    (oficial / "publications" / "pub_1" / "publication.json").write_text('{"id": "pub_1"}')
    backup = JsonDirectoryPublicationBackup(
        source_dir=oficial, backup_root=tmp_path / "backups", clock=ControllableClock()
    )

    destino = Path(await backup.backup("replace-gpqa"))

    assert destino.parent == tmp_path / "backups"
    assert destino.name.endswith("replace-gpqa")
    assert (destino / "publications" / "pub_1" / "publication.json").read_text() == '{"id": "pub_1"}'


async def test_backup_json_de_armazenamento_vazio_registra_o_estado(tmp_path: Path) -> None:
    backup = JsonDirectoryPublicationBackup(
        source_dir=tmp_path / "nao-existe", backup_root=tmp_path / "backups", clock=ControllableClock()
    )

    destino = Path(await backup.backup("publish-initial"))

    assert json.loads((destino / "EMPTY.json").read_text())["source"].endswith("nao-existe")


async def test_backup_mongo_exporta_as_colecoes(tmp_path: Path) -> None:
    client = AsyncMongoMockClient()
    await client["db"]["official_publications"].insert_one({"_id": "pub_1", "dataset": "mmlu"})
    backup = MongoPublicationBackup(
        collections={
            "official_publications": client["db"]["official_publications"],
            "official_sessions": client["db"]["official_sessions"],
        },
        backup_root=tmp_path,
        clock=ControllableClock(),
    )

    destino = Path(await backup.backup("publish-initial"))

    conteudo = json.loads(destino.read_text())
    assert conteudo["official_publications"] == [{"_id": "pub_1", "dataset": "mmlu"}]
    assert conteudo["official_sessions"] == []
