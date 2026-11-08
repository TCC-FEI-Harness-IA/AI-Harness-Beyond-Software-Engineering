import logging

import pytest

from src.application.usecases.delete_model_usecase import DeleteModelUseCase
from src.application.usecases.register_model_usecase import RegisterModelUseCase
from src.application.usecases.update_model_usecase import UpdateModelUseCase
from src.domain.entities.llm.model_info import ModelInfo
from src.domain.errors.model_already_registered_error import ModelAlreadyRegisteredError
from src.domain.errors.model_not_found_error import ModelNotFoundError
from tests.doubles.in_memory_model_info_repository import InMemoryModelInfoRepository

_LOGGER = logging.getLogger("teste")


async def test_cadastro_grava_o_modelo_novo() -> None:
    repositorio = InMemoryModelInfoRepository()
    modelo = ModelInfo(model_name="vendor/novo", context_length=8192)

    resultado = await RegisterModelUseCase(repository=repositorio, logger=_LOGGER).execute(model=modelo)

    assert resultado == modelo
    assert repositorio.models == {"vendor/novo": modelo}


async def test_cadastro_recusa_modelo_repetido_sem_sobrescrever() -> None:
    original = ModelInfo(model_name="vendor/modelo", context_length=8192)
    repositorio = InMemoryModelInfoRepository(models=[original])

    with pytest.raises(ModelAlreadyRegisteredError, match="vendor/modelo"):
        await RegisterModelUseCase(repository=repositorio, logger=_LOGGER).execute(
            model=ModelInfo(model_name="vendor/modelo", context_length=1)
        )

    assert repositorio.models["vendor/modelo"] == original


async def test_edicao_substitui_as_informacoes() -> None:
    repositorio = InMemoryModelInfoRepository(models=[ModelInfo(model_name="vendor/modelo", context_length=8192)])
    novo = ModelInfo(model_name="vendor/modelo", display_name="Vendor: Modelo", context_length=16384)

    await UpdateModelUseCase(repository=repositorio, logger=_LOGGER).execute(model=novo)

    assert repositorio.models["vendor/modelo"] == novo


async def test_edicao_de_modelo_inexistente_nao_cria_cadastro() -> None:
    repositorio = InMemoryModelInfoRepository()

    with pytest.raises(ModelNotFoundError, match="vendor/fantasma"):
        await UpdateModelUseCase(repository=repositorio, logger=_LOGGER).execute(
            model=ModelInfo(model_name="vendor/fantasma")
        )

    assert repositorio.models == {}


async def test_remocao_apaga_o_modelo() -> None:
    repositorio = InMemoryModelInfoRepository(models=[ModelInfo(model_name="vendor/modelo")])

    await DeleteModelUseCase(repository=repositorio, logger=_LOGGER).execute(model_name="vendor/modelo")

    assert repositorio.models == {}


async def test_remocao_de_modelo_inexistente_levanta() -> None:
    with pytest.raises(ModelNotFoundError):
        await DeleteModelUseCase(repository=InMemoryModelInfoRepository(), logger=_LOGGER).execute(
            model_name="vendor/fantasma"
        )
