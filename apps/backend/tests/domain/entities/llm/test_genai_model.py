import dataclasses

import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.enums.model_provider_enum import ModelProviderEnum


def test_carrega_nome_e_provedor() -> None:
    modelo = GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER)

    assert modelo.model_name == "vendor/modelo"
    assert modelo.model_provider is ModelProviderEnum.OPEN_ROUTER


def test_e_imutavel() -> None:
    modelo = GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER)

    with pytest.raises(dataclasses.FrozenInstanceError):
        modelo.model_name = "outro"


def test_instancias_com_os_mesmos_dados_sao_iguais() -> None:
    primeiro = GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER)
    segundo = GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER)

    assert primeiro == segundo


def test_nao_depende_de_configuracao() -> None:
    campos = {campo.name for campo in dataclasses.fields(GenaiModel)}

    assert campos == {"model_name", "model_provider"}
