import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.llm_provider_message import LLMProviderMessage
from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.enums.model_provider_enum import ModelProviderEnum


def _build_request(temperature: float | str = 0.7) -> LLMProviderRequest:
    return LLMProviderRequest(
        llm_model=GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
        messages=[LLMProviderMessage(role="user", content="pergunta")],
        max_tokens=100,
        temperature=temperature,
    )


@pytest.mark.parametrize("temperature", [0, 0.5, 1])
def test_temperaturas_dentro_do_intervalo_sao_aceitas(temperature: float) -> None:
    assert _build_request(temperature=temperature).temperature == temperature


@pytest.mark.parametrize("temperature", [-0.1, 1.1])
def test_temperaturas_fora_do_intervalo_sao_recusadas(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature"):
        _build_request(temperature=temperature)


@pytest.mark.parametrize("temperature", [0, 0.25, 0.66])
def test_temperatura_e_preservada_sem_arredondamento(temperature: float) -> None:
    assert _build_request(temperature=temperature).temperature == temperature


def test_temperatura_em_texto_e_convertida_sem_arredondar() -> None:
    assert _build_request(temperature="0.65").temperature == 0.65


@pytest.mark.parametrize("temperature", [float("nan"), float("inf"), float("-inf")])
def test_temperatura_nao_finita_e_recusada(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature"):
        _build_request(temperature=temperature)


def test_metadata_default_e_um_dicionario_vazio() -> None:
    assert _build_request().metadata == {}


def test_metadata_nao_e_compartilhada_entre_instancias() -> None:
    primeiro = _build_request()
    segundo = _build_request()

    primeiro.metadata["chave"] = "valor"

    assert segundo.metadata == {}
