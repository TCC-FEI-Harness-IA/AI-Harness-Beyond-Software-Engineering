import pytest

from src.domain.entities.llm.model_info import ModelInfo
from src.domain.errors.model_already_registered_error import ModelAlreadyRegisteredError
from src.infra.repositories.mongo_model_info_repository import MongoModelInfoRepository
from src.infra.routes.v1.model.dtos.model_info_dto import ModelInfoFieldsDTO, ModelInfoInputDTO
from src.infra.startups.model_catalog_startup import ModelCatalogStartup
from tests.doubles.in_memory_model_info_repository import InMemoryModelInfoRepository


def _startup_em_memoria(
    monkeypatch: pytest.MonkeyPatch, repositorio: InMemoryModelInfoRepository
) -> ModelCatalogStartup:
    startup = ModelCatalogStartup()
    for usecase in (
        startup.list_models_use_case,
        startup.register_model_use_case,
        startup.update_model_use_case,
        startup.delete_model_use_case,
    ):
        monkeypatch.setattr(usecase, "repository", repositorio)
    return startup


def test_constroi_todo_o_grafo_sem_deixar_atributo_nulo() -> None:
    startup = ModelCatalogStartup()

    assert vars(startup)
    assert all(valor is not None for valor in vars(startup).values())


def test_todos_os_casos_de_uso_compartilham_o_repositorio_mongo() -> None:
    startup = ModelCatalogStartup()

    assert isinstance(startup.model_repository, MongoModelInfoRepository)
    assert startup.list_models_use_case.repository is startup.model_repository
    assert startup.register_model_use_case.repository is startup.model_repository
    assert startup.update_model_use_case.repository is startup.model_repository
    assert startup.delete_model_use_case.repository is startup.model_repository


async def test_lista_os_modelos_como_documentos(monkeypatch: pytest.MonkeyPatch) -> None:
    startup = _startup_em_memoria(
        monkeypatch, InMemoryModelInfoRepository(models=[ModelInfo(model_name="vendor/modelo", context_length=8192)])
    )

    assert await startup.list_models() == [
        {
            "model_name": "vendor/modelo",
            "display_name": None,
            "input_price_per_million_tokens": None,
            "output_price_per_million_tokens": None,
            "context_length": 8192,
            "throughput_tokens_per_second": None,
        }
    ]


async def test_cadastro_normaliza_nome_e_apelido_em_branco(monkeypatch: pytest.MonkeyPatch) -> None:
    repositorio = InMemoryModelInfoRepository()
    startup = _startup_em_memoria(monkeypatch, repositorio)

    documento = await startup.register_model(
        payload=ModelInfoInputDTO(model_name="  vendor/novo ", display_name="  ", context_length=4096)
    )

    assert documento["model_name"] == "vendor/novo"
    assert documento["display_name"] is None
    assert repositorio.models["vendor/novo"].context_length == 4096


async def test_cadastro_repetido_levanta_o_erro_de_dominio(monkeypatch: pytest.MonkeyPatch) -> None:
    startup = _startup_em_memoria(monkeypatch, InMemoryModelInfoRepository(models=[ModelInfo(model_name="vendor/a")]))

    with pytest.raises(ModelAlreadyRegisteredError):
        await startup.register_model(payload=ModelInfoInputDTO(model_name="vendor/a"))


async def test_edicao_usa_o_identificador_do_caminho(monkeypatch: pytest.MonkeyPatch) -> None:
    repositorio = InMemoryModelInfoRepository(models=[ModelInfo(model_name="vendor/a")])
    startup = _startup_em_memoria(monkeypatch, repositorio)

    await startup.update_model(model_name="vendor/a", payload=ModelInfoFieldsDTO(display_name="Vendor: A"))

    assert repositorio.models["vendor/a"].display_name == "Vendor: A"


async def test_remocao_apaga_do_repositorio(monkeypatch: pytest.MonkeyPatch) -> None:
    repositorio = InMemoryModelInfoRepository(models=[ModelInfo(model_name="vendor/a")])
    startup = _startup_em_memoria(monkeypatch, repositorio)

    await startup.delete_model(model_name="vendor/a")

    assert repositorio.models == {}
