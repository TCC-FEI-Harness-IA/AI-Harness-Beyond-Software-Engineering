import logging

import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.adapters.model_catalog_adapter import ModelCatalogAdapter
from tests.doubles.fake_settings import FakeSettings


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
