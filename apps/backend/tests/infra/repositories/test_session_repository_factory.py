from pathlib import Path

from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.json_file_session_repository import JsonFileSessionRepository
from src.infra.repositories.mongo_session_repository import MongoSessionRepository
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory
from tests.doubles.fake_settings import FakeSettings


def _build_factory(**settings_overrides: object) -> SessionRepositoryFactory:
    return SessionRepositoryFactory(settings=FakeSettings(**settings_overrides), mapper=SessionDocumentMapper())


def test_backend_json_file_e_o_default() -> None:
    repositorio = _build_factory().create()

    assert isinstance(repositorio, JsonFileSessionRepository)


def test_repositorio_json_file_aponta_para_o_diretorio_configurado(tmp_path: Path) -> None:
    repositorio = _build_factory(
        ralph_session_storage_backend=SessionStorageBackendEnum.JSON_FILE,
        ralph_sessions_storage_path=str(tmp_path),
    ).create()

    assert isinstance(repositorio, JsonFileSessionRepository)
    assert repositorio.settings.ralph_sessions_storage_path == str(tmp_path)


def test_backend_mongodb_cria_o_repositorio_de_mongo() -> None:
    repositorio = _build_factory(ralph_session_storage_backend=SessionStorageBackendEnum.MONGODB).create()

    assert isinstance(repositorio, MongoSessionRepository)


def test_repositorio_mongo_aponta_para_o_banco_e_a_colecao_configurados() -> None:
    repositorio = _build_factory(
        ralph_session_storage_backend=SessionStorageBackendEnum.MONGODB,
        mongodb_database="banco_de_teste",
        mongodb_sessions_collection="colecao_de_teste",
    ).create()

    assert isinstance(repositorio, MongoSessionRepository)
    assert repositorio.collection.name == "colecao_de_teste"
    assert repositorio.collection.database.name == "banco_de_teste"
