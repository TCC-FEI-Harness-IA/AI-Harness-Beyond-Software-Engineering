import logging

from mongomock_motor import AsyncMongoMockClient

from src.domain.entities.llm.model_info import ModelInfo
from src.infra.repositories.mongo_model_info_repository import MongoModelInfoRepository


def _build_repository() -> MongoModelInfoRepository:
    colecao = AsyncMongoMockClient()["banco_de_teste"]["modelos_de_teste"]
    return MongoModelInfoRepository(collection=colecao, logger=logging.getLogger("teste"))


def _modelo(model_name: str = "vendor/modelo", **overrides: object) -> ModelInfo:
    campos: dict[str, object] = {
        "display_name": "Vendor: Modelo",
        "input_price_per_million_tokens": 0.0434,
        "output_price_per_million_tokens": 0.3,
        "context_length": 1_048_576,
        "throughput_tokens_per_second": 145.0,
    }
    return ModelInfo(model_name=model_name, **(campos | overrides))  # type: ignore[arg-type]


async def test_save_seguido_de_find_by_name_devolve_o_mesmo_modelo() -> None:
    repositorio = _build_repository()

    await repositorio.save(model=_modelo())

    assert await repositorio.find_by_name(model_name="vendor/modelo") == _modelo()


async def test_documento_usa_o_identificador_como_id() -> None:
    repositorio = _build_repository()

    await repositorio.save(model=_modelo())

    documento = await repositorio.collection.find_one({"_id": "vendor/modelo"})
    assert documento is not None
    assert documento["model_name"] == "vendor/modelo"


async def test_save_substitui_o_cadastro_existente() -> None:
    repositorio = _build_repository()
    await repositorio.save(model=_modelo())

    await repositorio.save(model=_modelo(context_length=8192))

    assert await repositorio.collection.count_documents({}) == 1
    encontrado = await repositorio.find_by_name(model_name="vendor/modelo")
    assert encontrado is not None and encontrado.context_length == 8192


async def test_find_by_name_de_modelo_inexistente_devolve_none() -> None:
    assert await _build_repository().find_by_name(model_name="vendor/fantasma") is None


async def test_list_all_ordena_pelo_identificador() -> None:
    repositorio = _build_repository()
    await repositorio.save(model=_modelo("b/dois"))
    await repositorio.save(model=_modelo("a/um", display_name=None, context_length=None))

    modelos = await repositorio.list_all()

    assert [modelo.model_name for modelo in modelos] == ["a/um", "b/dois"]
    assert modelos[0].context_length is None


async def test_delete_informa_se_havia_o_que_remover() -> None:
    repositorio = _build_repository()
    await repositorio.save(model=_modelo())

    assert await repositorio.delete(model_name="vendor/modelo") is True
    assert await repositorio.delete(model_name="vendor/modelo") is False
    assert await repositorio.find_by_name(model_name="vendor/modelo") is None
