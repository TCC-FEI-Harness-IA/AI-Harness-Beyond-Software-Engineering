"""Isolamento por proprietário nos repositórios JSON e MongoDB (sessões, baterias e modelos)."""
import json
import logging
from pathlib import Path

import pytest
from mongomock_motor import AsyncMongoMockClient

from src.domain.entities.llm.model_info import ModelInfo
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.json_file_benchmark_session_repository import JsonFileBenchmarkSessionRepository
from src.infra.repositories.json_file_session_repository import JsonFileSessionRepository
from src.infra.repositories.layered_model_info_repository import LayeredModelInfoRepository
from src.infra.repositories.mongo_benchmark_session_repository import MongoBenchmarkSessionRepository
from src.infra.repositories.mongo_model_info_repository import MongoModelInfoRepository
from src.infra.repositories.mongo_session_repository import MongoSessionRepository
from tests.doubles.benchmark_factories import bateria
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.session_factories import nova_sessao

_LOGGER = logging.getLogger("teste")


def _json_sessoes(base: Path, owner: str) -> JsonFileSessionRepository:
    return JsonFileSessionRepository(
        mapper=SessionDocumentMapper(),
        settings=FakeSettings(ralph_sessions_storage_path=str(base)),
        logger=_LOGGER,
        owner_id=owner,
    )


def _mongo_sessoes(client: AsyncMongoMockClient, owner: str) -> MongoSessionRepository:
    return MongoSessionRepository(
        collection=client["db"]["sessions"], mapper=SessionDocumentMapper(), logger=_LOGGER, owner_id=owner
    )


def _json_baterias(base: Path, owner: str) -> JsonFileBenchmarkSessionRepository:
    return JsonFileBenchmarkSessionRepository(
        mapper=BenchmarkSessionDocumentMapper(),
        settings=FakeSettings(ralph_benchmark_sessions_storage_path=str(base)),
        logger=_LOGGER,
        owner_id=owner,
    )


def _mongo_baterias(client: AsyncMongoMockClient, owner: str) -> MongoBenchmarkSessionRepository:
    return MongoBenchmarkSessionRepository(
        collection=client["db"]["benchmarks"], mapper=BenchmarkSessionDocumentMapper(), logger=_LOGGER, owner_id=owner
    )


@pytest.fixture(params=["json", "mongo"])
def sessoes(request: pytest.FixtureRequest, tmp_path: Path):
    client = AsyncMongoMockClient()
    if request.param == "json":
        return lambda owner: _json_sessoes(tmp_path / "sessions", owner)
    return lambda owner: _mongo_sessoes(client, owner)


@pytest.fixture(params=["json", "mongo"])
def baterias(request: pytest.FixtureRequest, tmp_path: Path):
    client = AsyncMongoMockClient()
    if request.param == "json":
        return lambda owner: _json_baterias(tmp_path / "benchmarks", owner)
    return lambda owner: _mongo_baterias(client, owner)


async def test_sessoes_com_mesmo_id_em_contas_diferentes_nao_interferem(sessoes) -> None:
    ana, bia = sessoes("usr_ana"), sessoes("usr_bia")
    da_ana = nova_sessao(session_id="sess_1", user_question="pergunta da ana")
    da_bia = nova_sessao(session_id="sess_1", user_question="pergunta da bia")

    await ana.save(session=da_ana)
    await bia.save(session=da_bia)

    assert (await ana.find_by_id(session_id="sess_1")).user_question == "pergunta da ana"
    assert (await bia.find_by_id(session_id="sess_1")).user_question == "pergunta da bia"
    assert await ana.list_ids() == ["sess_1"]


async def test_conta_nao_ve_lista_nem_apaga_sessao_alheia(sessoes) -> None:
    ana, bia = sessoes("usr_ana"), sessoes("usr_bia")
    await ana.save(session=nova_sessao(session_id="sess_ana"))

    assert await bia.find_by_id(session_id="sess_ana") is None
    assert await bia.list_ids() == []
    assert await bia.delete(session_id="sess_ana") is False
    assert await ana.find_by_id(session_id="sess_ana") is not None


async def test_baterias_isoladas_por_conta(baterias) -> None:
    ana, bia = baterias("usr_ana"), baterias("usr_bia")
    da_ana = bateria("Q1")
    await ana.save(benchmark_session=da_ana)

    assert await bia.find_by_id(benchmark_session_id=da_ana.id) is None
    assert await bia.list_all() == []
    assert [item.id for item in await ana.list_all()] == [da_ana.id]

    da_bia = bateria("Q1", "Q2")
    await bia.save(benchmark_session=da_bia)
    assert len((await ana.find_by_id(benchmark_session_id=da_ana.id)).questions) == 1
    assert len((await bia.find_by_id(benchmark_session_id=da_bia.id)).questions) == 2


async def test_alias_so_altera_a_bateria_da_propria_conta(baterias) -> None:
    ana, bia = baterias("usr_ana"), baterias("usr_bia")
    da_ana = bateria("Q1")
    await ana.save(benchmark_session=da_ana)
    da_bia = bateria("Q1")
    await bia.save(benchmark_session=da_bia)

    da_bia.alias = "alias da bia"
    await bia.update_alias(benchmark_session=da_bia)

    assert (await ana.find_by_id(benchmark_session_id=da_ana.id)).alias is None


@pytest.mark.parametrize("owner", ["", "../x", "usr ana", "a/b"])
def test_proprietario_invalido_e_recusado(tmp_path: Path, owner: str) -> None:
    with pytest.raises(ValueError):
        _json_sessoes(tmp_path, owner)
    with pytest.raises(ValueError):
        _mongo_sessoes(AsyncMongoMockClient(), owner)
    with pytest.raises(ValueError):
        _json_baterias(tmp_path, owner)
    with pytest.raises(ValueError):
        _mongo_baterias(AsyncMongoMockClient(), owner)


async def test_dados_legados_sem_proprietario_ficam_invisiveis(tmp_path: Path) -> None:
    base = tmp_path / "sessions"
    base.mkdir()
    legado = SessionDocumentMapper().to_document(session=nova_sessao(session_id="sess_legado"))
    (base / "sess_legado.json").write_text(json.dumps(legado), encoding="utf-8")
    client = AsyncMongoMockClient()
    await client["db"]["sessions"].insert_one(legado)

    for repositorio in (_json_sessoes(base, "usr_ana"), _mongo_sessoes(client, "usr_ana")):
        assert await repositorio.find_by_id(session_id="sess_legado") is None
        assert await repositorio.list_ids() == []


async def test_documento_registra_o_proprietario(tmp_path: Path) -> None:
    client = AsyncMongoMockClient()
    await _json_sessoes(tmp_path, "usr_ana").save(session=nova_sessao(session_id="sess_1"))
    await _mongo_sessoes(client, "usr_ana").save(session=nova_sessao(session_id="sess_1"))

    arquivo = json.loads((tmp_path / "owners" / "usr_ana" / "sess_1.json").read_text(encoding="utf-8"))
    documento = await client["db"]["sessions"].find_one({"owner_id": "usr_ana"})

    assert arquivo["owner_id"] == "usr_ana"
    assert documento["_id"] == "usr_ana/sess_1"
    assert documento["id"] == "sess_1"


# ── Catálogo de modelos ──────────────────────────────────────────────────────


def _modelos(client: AsyncMongoMockClient, owner: str) -> MongoModelInfoRepository:
    return MongoModelInfoRepository(collection=client["db"]["user_models"], logger=_LOGGER, owner_id=owner)


async def test_dois_usuarios_cadastram_o_mesmo_modelo_sem_interferencia() -> None:
    client = AsyncMongoMockClient()
    ana, bia = _modelos(client, "usr_ana"), _modelos(client, "usr_bia")
    await ana.ensure_indexes()

    await ana.save(model=ModelInfo(model_name="vendor/m", display_name="da ana"))
    await bia.save(model=ModelInfo(model_name="vendor/m", display_name="da bia"))

    assert (await ana.find_by_name("vendor/m")).display_name == "da ana"
    assert (await bia.find_by_name("vendor/m")).display_name == "da bia"
    assert await bia.delete("vendor/m") is True
    assert await ana.find_by_name("vendor/m") is not None
    assert [item.model_name for item in await ana.list_all()] == ["vendor/m"]


async def test_catalogo_compartilhado_e_somente_leitura_para_o_usuario() -> None:
    client = AsyncMongoMockClient()
    compartilhado = MongoModelInfoRepository(collection=client["db"]["models"], logger=_LOGGER)
    await compartilhado.save(model=ModelInfo(model_name="vendor/shared", display_name="compartilhado"))
    pessoal = _modelos(client, "usr_ana")
    catalogo = LayeredModelInfoRepository(personal=pessoal, shared=compartilhado)

    assert (await catalogo.find_by_name("vendor/shared")).display_name == "compartilhado"
    assert await catalogo.delete("vendor/shared") is False
    assert await catalogo.is_shared("vendor/shared") is True

    await catalogo.save(model=ModelInfo(model_name="vendor/shared", display_name="minha versão"))
    assert (await catalogo.find_by_name("vendor/shared")).display_name == "minha versão"
    assert (await compartilhado.find_by_name("vendor/shared")).display_name == "compartilhado"
    nomes = [(item.model_name, item.display_name) for item in await catalogo.list_all()]
    assert nomes == [("vendor/shared", "minha versão")]
    assert await catalogo.is_shared("vendor/shared") is False


async def test_catalogo_em_camadas_lista_os_dois_niveis() -> None:
    client = AsyncMongoMockClient()
    compartilhado = MongoModelInfoRepository(collection=client["db"]["models"], logger=_LOGGER)
    await compartilhado.save(model=ModelInfo(model_name="a/shared"))
    pessoal = _modelos(client, "usr_ana")
    await pessoal.save(model=ModelInfo(model_name="b/minha"))
    catalogo = LayeredModelInfoRepository(personal=pessoal, shared=compartilhado)

    assert [item.model_name for item in await catalogo.list_all()] == ["a/shared", "b/minha"]
    assert await catalogo.find_by_name("x/nao") is None
    assert await catalogo.delete("b/minha") is True
