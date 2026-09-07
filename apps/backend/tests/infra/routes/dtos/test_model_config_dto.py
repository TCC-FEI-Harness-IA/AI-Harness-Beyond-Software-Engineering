import pytest

from src.infra.routes.v1.message.dtos.model_config_dto import ModelConfigDTO

_BASE = {
    "provider": "open_router",
    "provider_config": {"model_name": "vendor/modelo"},
    "max_tokens": 100,
}


def test_temperatura_informada_e_arredondada_para_uma_casa() -> None:
    dto = ModelConfigDTO.model_validate({**_BASE, "temperature": 0.66})

    assert dto.temperature == 0.7


def test_temperatura_ausente_assume_o_default() -> None:
    dto = ModelConfigDTO.model_validate(_BASE)

    assert dto.temperature == 0.7


@pytest.mark.parametrize("temperature", [0, None])
def test_temperatura_sem_valor_util_assume_o_default(temperature: float | None) -> None:
    dto = ModelConfigDTO.model_validate({**_BASE, "temperature": temperature})

    assert dto.temperature == 0.7


@pytest.mark.parametrize("temperature", [-0.1, 1.1])
def test_temperatura_fora_do_intervalo_e_recusada(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature deve estar entre 0 e 1"):
        ModelConfigDTO.model_validate({**_BASE, "temperature": temperature})


def test_endpoint_do_provedor_e_opcional() -> None:
    dto = ModelConfigDTO.model_validate(_BASE)

    assert dto.provider_config.endpoint is None
