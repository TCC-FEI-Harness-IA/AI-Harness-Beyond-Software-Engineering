import json
import logging
from datetime import timedelta
from pathlib import Path

import pytest
from mongomock_motor import AsyncMongoMockClient

from src.domain.entities.publication.official_publication import OfficialPublication
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.publication_status_enum import PublicationStatusEnum
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.official_publication_document_mapper import OfficialPublicationDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.json_file_official_publication_repository import JsonFileOfficialPublicationRepository
from src.infra.repositories.mongo_official_publication_repository import MongoOfficialPublicationRepository
from src.infra.repositories.official_publication_repository_factory import OfficialPublicationRepositoryFactory
from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum
from tests.doubles.benchmark_factories import CRIADO_EM
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.publication_doubles import bateria_concluida

_LOGGER = logging.getLogger("teste")


def _mapper() -> OfficialPublicationDocumentMapper:
    return OfficialPublicationDocumentMapper(benchmark_mapper=BenchmarkSessionDocumentMapper())


def _publicacao(pub_id: str = "pub_1", battery_id: str = "bench_g") -> tuple[OfficialPublication, list]:
    bateria, sessoes = bateria_concluida(battery_id, BenchmarkDatasetEnum.GPQA)
    return (
        OfficialPublication(
            id=pub_id, dataset=BenchmarkDatasetEnum.GPQA, benchmark_session=bateria, published_at=CRIADO_EM,
            published_by="admin", source_label="bateria pessoal", supersedes="pub_0",
        ),
        sessoes,
    )


@pytest.fixture(params=["json", "mongo"])
def repositorio(request: pytest.FixtureRequest, tmp_path: Path):
    if request.param == "json":
        return JsonFileOfficialPublicationRepository(
            base_path=tmp_path / "official", mapper=_mapper(), session_mapper=SessionDocumentMapper(), logger=_LOGGER
        )
    client = AsyncMongoMockClient()
    return MongoOfficialPublicationRepository(
        publications=client["db"]["official_publications"], sessions=client["db"]["official_sessions"],
        mapper=_mapper(), session_mapper=SessionDocumentMapper(), logger=_LOGGER,
    )


async def test_grava_e_le_a_publicacao_com_as_copias_das_sessoes(repositorio) -> None:
    publicacao, sessoes = _publicacao()

    await repositorio.create(publicacao, sessions=sessoes)

    lida = await repositorio.find("pub_1")
    assert lida == publicacao
    assert lida.benchmark_session.benchmark.split == "diamond"
    assert [item.id for item in await repositorio.list_all()] == ["pub_1"]
    assert await repositorio.find_session("pub_1", sessoes[0].id) == sessoes[0]
    assert sorted(item.id for item in await repositorio.list_sessions("pub_1")) == sorted(s.id for s in sessoes)


async def test_sessao_so_e_encontrada_dentro_da_sua_publicacao(repositorio) -> None:
    primeira, sessoes = _publicacao("pub_1", "bench_a")
    segunda, outras = _publicacao("pub_2", "bench_b")
    await repositorio.create(primeira, sessions=sessoes)
    await repositorio.create(segunda, sessions=outras)

    assert await repositorio.find_session("pub_1", outras[0].id) is None
    assert await repositorio.find_session("pub_x", sessoes[0].id) is None
    assert await repositorio.find("pub_x") is None


async def test_substituicao_mantem_a_publicacao_anterior(repositorio) -> None:
    publicacao, sessoes = _publicacao()
    await repositorio.create(publicacao, sessions=sessoes)

    await repositorio.mark_superseded("pub_1", superseded_by="pub_2", at=CRIADO_EM + timedelta(days=1))

    lida = await repositorio.find("pub_1")
    assert lida.status is PublicationStatusEnum.SUPERSEDED
    assert lida.superseded_by == "pub_2"
    assert lida.published_at == CRIADO_EM
    assert await repositorio.find_session("pub_1", sessoes[0].id) is not None


async def test_listagem_ordena_da_mais_recente(repositorio) -> None:
    antiga, sessoes = _publicacao("pub_antiga", "bench_a")
    nova, outras = _publicacao("pub_nova", "bench_b")
    nova = nova.__class__(**{**nova.__dict__, "published_at": CRIADO_EM + timedelta(hours=1)})
    await repositorio.create(antiga, sessions=sessoes)
    await repositorio.create(nova, sessions=outras)

    assert [item.id for item in await repositorio.list_all()] == ["pub_nova", "pub_antiga"]


@pytest.mark.parametrize("identificador", ["../x", "pub 1", ""])
async def test_identificadores_invalidos_sao_recusados_no_json(tmp_path: Path, identificador: str) -> None:
    repositorio = JsonFileOfficialPublicationRepository(
        base_path=tmp_path, mapper=_mapper(), session_mapper=SessionDocumentMapper(), logger=_LOGGER
    )

    with pytest.raises(ValueError):
        await repositorio.find(identificador)
    with pytest.raises(ValueError):
        await repositorio.find_session("pub_1", identificador)


async def test_json_ignora_pastas_sem_publicacao_e_documentos_sem_dono(tmp_path: Path) -> None:
    repositorio = JsonFileOfficialPublicationRepository(
        base_path=tmp_path, mapper=_mapper(), session_mapper=SessionDocumentMapper(), logger=_LOGGER
    )
    (tmp_path / "publications" / "pub_incompleta").mkdir(parents=True)
    publicacao, sessoes = _publicacao()
    await repositorio.create(publicacao, sessions=sessoes)

    assert [item.id for item in await repositorio.list_all()] == ["pub_1"]
    documento = json.loads((tmp_path / "publications" / "pub_1" / "publication.json").read_text(encoding="utf-8"))
    assert documento["schema_version"] == 1
    assert "owner_id" not in documento["benchmark_session"]


def test_mapper_recusa_documento_sem_campos(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="dataset"):
        _mapper().from_document({"_id": "pub_1"})


def test_fabrica_escolhe_o_armazenamento_configurado(tmp_path: Path) -> None:
    json_repo = OfficialPublicationRepositoryFactory(
        settings=FakeSettings(ralph_official_storage_path=str(tmp_path))
    ).create()
    mongo_repo = OfficialPublicationRepositoryFactory(
        settings=FakeSettings(ralph_session_storage_backend=SessionStorageBackendEnum.MONGODB)
    ).create()

    assert isinstance(json_repo, JsonFileOfficialPublicationRepository)
    assert isinstance(mongo_repo, MongoOfficialPublicationRepository)


async def test_json_substituir_publicacao_inexistente_falha(tmp_path: Path) -> None:
    repositorio = JsonFileOfficialPublicationRepository(
        base_path=tmp_path, mapper=_mapper(), session_mapper=SessionDocumentMapper(), logger=_LOGGER
    )

    with pytest.raises(ValueError, match="não encontrada"):
        await repositorio.mark_superseded("pub_x", superseded_by="pub_y", at=CRIADO_EM)
    assert await repositorio.list_sessions("pub_x") == []
