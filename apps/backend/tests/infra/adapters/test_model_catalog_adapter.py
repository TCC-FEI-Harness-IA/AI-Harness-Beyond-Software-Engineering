import logging

import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.model_info import ModelInfo
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.adapters.model_catalog_adapter import ModelCatalogAdapter
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.in_memory_model_info_repository import InMemoryModelInfoRepository


def _build_adapter(**overrides: object) -> ModelCatalogAdapter:
    return ModelCatalogAdapter(
        settings=FakeSettings(**overrides),
        logger=logging.getLogger("teste"),
    )


def test_resolve_devolve_o_modelo_quando_nome_e_provedor_estao_liberados() -> None:
    adapter = _build_adapter(
        genai_available_models=["vendor/modelo"],
        genai_available_providers=["open_router"],
    )

    modelo = adapter.resolve(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER)

    assert modelo == GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER)


def test_resolve_preserva_a_caixa_original_do_nome_informado() -> None:
    adapter = _build_adapter(genai_available_models=["vendor/modelo"])

    modelo = adapter.resolve(model_name="Vendor/Modelo", model_provider=ModelProviderEnum.OPEN_ROUTER)

    assert modelo.model_name == "Vendor/Modelo"


def test_resolve_recusa_modelo_fora_da_allowlist() -> None:
    adapter = _build_adapter(genai_available_models=["vendor/permitido"])

    with pytest.raises(ValueError, match="vendor/negado"):
        adapter.resolve(model_name="vendor/negado", model_provider=ModelProviderEnum.OPEN_ROUTER)


def test_resolve_recusa_provedor_fora_da_allowlist() -> None:
    adapter = _build_adapter(
        genai_available_models=["vendor/modelo"],
        genai_available_providers=[],
    )

    with pytest.raises(ValueError, match="open_router"):
        adapter.resolve(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER)


def test_allowlist_de_modelos_vazia_recusa_qualquer_modelo() -> None:
    adapter = _build_adapter(genai_available_models=[])

    assert adapter.is_model_available(model_name="qualquer/coisa") is False


def test_comparacao_de_modelo_e_case_insensitive() -> None:
    adapter = _build_adapter(genai_available_models=["meta/llama"])

    assert adapter.is_model_available(model_name="Meta/Llama") is True


def test_comparacao_de_provedor_e_case_insensitive() -> None:
    adapter = _build_adapter(genai_available_providers=["OPEN_ROUTER"])

    assert adapter.is_provider_available(model_provider=ModelProviderEnum.OPEN_ROUTER) is True


def test_modelo_fora_da_allowlist_nao_esta_disponivel() -> None:
    adapter = _build_adapter(genai_available_models=["meta/llama"])

    assert adapter.is_model_available(model_name="outro/modelo") is False


def test_provedor_fora_da_allowlist_nao_esta_disponivel() -> None:
    adapter = _build_adapter(genai_available_providers=["outro_provedor"])

    assert adapter.is_provider_available(model_provider=ModelProviderEnum.OPEN_ROUTER) is False


def test_nome_em_branco_nao_esta_disponivel() -> None:
    adapter = _build_adapter(genai_available_models=["meta/llama"])

    assert adapter.is_model_available(model_name="   ") is False


def _build_adapter_com_cadastro(repositorio: InMemoryModelInfoRepository) -> ModelCatalogAdapter:
    return ModelCatalogAdapter(
        settings=FakeSettings(genai_available_models=["vendor/da-allowlist"]),
        logger=logging.getLogger("teste"),
        model_repository=repositorio,
    )


async def test_modelo_cadastrado_fica_liberado_depois_de_carregado() -> None:
    adapter = _build_adapter_com_cadastro(InMemoryModelInfoRepository(models=[ModelInfo(model_name="vendor/novo")]))

    await adapter.load_model_info(model_name="vendor/novo")

    modelo = adapter.resolve(model_name="vendor/novo", model_provider=ModelProviderEnum.OPEN_ROUTER)
    assert modelo.model_name == "vendor/novo"


async def test_modelo_nao_cadastrado_segue_recusado() -> None:
    adapter = _build_adapter_com_cadastro(InMemoryModelInfoRepository())

    await adapter.load_model_info(model_name="vendor/fantasma")

    with pytest.raises(ValueError, match="vendor/fantasma"):
        adapter.resolve(model_name="vendor/fantasma", model_provider=ModelProviderEnum.OPEN_ROUTER)


async def test_resolve_leva_o_contexto_do_cadastro_inclusive_para_modelo_da_allowlist() -> None:
    repositorio = InMemoryModelInfoRepository(
        models=[ModelInfo(model_name="vendor/da-allowlist", context_length=131072)]
    )
    adapter = _build_adapter_com_cadastro(repositorio)

    await adapter.load_model_info(model_name="vendor/da-allowlist")

    modelo = adapter.resolve(model_name="vendor/da-allowlist", model_provider=ModelProviderEnum.OPEN_ROUTER)
    assert repositorio.find_calls == ["vendor/da-allowlist"]
    assert modelo.context_length == 131072


async def test_modelo_sem_cadastro_resolve_sem_contexto() -> None:
    adapter = _build_adapter_com_cadastro(InMemoryModelInfoRepository())

    await adapter.load_model_info(model_name="vendor/da-allowlist")

    modelo = adapter.resolve(model_name="vendor/da-allowlist", model_provider=ModelProviderEnum.OPEN_ROUTER)
    assert modelo.context_length is None


async def test_falha_do_repositorio_nao_propaga_e_mantem_a_allowlist() -> None:
    adapter = _build_adapter_com_cadastro(InMemoryModelInfoRepository(error=RuntimeError("mongo fora do ar")))

    await adapter.load_model_info(model_name="vendor/novo")
    await adapter.load_model_info(model_name="vendor/da-allowlist")

    assert adapter.is_model_available(model_name="vendor/novo") is False
    assert adapter.is_model_available(model_name="vendor/da-allowlist") is True


async def test_sem_repositorio_load_model_info_nao_faz_nada() -> None:
    adapter = _build_adapter(genai_available_models=[])

    await adapter.load_model_info(model_name="vendor/novo")

    assert adapter.is_model_available(model_name="vendor/novo") is False
