import logging

from src.application.usecases.list_models_usecase import ListModelsUseCase
from src.domain.entities.llm.model_info import ModelInfo
from tests.doubles.in_memory_model_info_repository import InMemoryModelInfoRepository


async def test_devolve_os_modelos_cadastrados_em_ordem_alfabetica() -> None:
    repositorio = InMemoryModelInfoRepository(
        models=[ModelInfo(model_name="b/dois", context_length=1000), ModelInfo(model_name="a/um")]
    )
    usecase = ListModelsUseCase(repository=repositorio, logger=logging.getLogger("teste"))

    modelos = await usecase.execute()

    assert modelos == [ModelInfo(model_name="a/um"), ModelInfo(model_name="b/dois", context_length=1000)]
