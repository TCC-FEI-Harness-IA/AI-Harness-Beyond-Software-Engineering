from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.repositories.benchmark_session_repository_factory import BenchmarkSessionRepositoryFactory
from src.infra.repositories.json_file_benchmark_session_repository import JsonFileBenchmarkSessionRepository
from src.infra.repositories.mongo_benchmark_session_repository import MongoBenchmarkSessionRepository
from tests.doubles.fake_settings import FakeSettings


def test_backend_json_cria_o_repositorio_em_arquivo() -> None:
    fabrica = BenchmarkSessionRepositoryFactory(settings=FakeSettings(), mapper=BenchmarkSessionDocumentMapper())

    assert isinstance(fabrica.create(), JsonFileBenchmarkSessionRepository)


def test_backend_mongodb_usa_a_colecao_das_baterias() -> None:
    settings = FakeSettings(
        ralph_session_storage_backend=SessionStorageBackendEnum.MONGODB,
        mongodb_benchmark_sessions_collection="baterias_de_teste",
    )

    repositorio = BenchmarkSessionRepositoryFactory(settings=settings, mapper=BenchmarkSessionDocumentMapper()).create()

    assert isinstance(repositorio, MongoBenchmarkSessionRepository)
    assert repositorio.collection.name == "baterias_de_teste"
