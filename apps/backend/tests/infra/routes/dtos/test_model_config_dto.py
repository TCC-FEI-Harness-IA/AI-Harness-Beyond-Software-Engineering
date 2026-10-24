import pytest
from pydantic import ValidationError

from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.routes.v1.message.dtos.model_config_dto import ModelConfigDTO

_BASE = {
    "provider": "open_router",
    "provider_config": {"model_name": "vendor/modelo"},
    "max_tokens": 100,
}


@pytest.mark.parametrize("temperature", [0, 0.0, 0.25, 0.66, 1])
def test_temperatura_informada_e_preservada_sem_arredondamento(temperature: float) -> None:
    dto = ModelConfigDTO.model_validate({**_BASE, "temperature": temperature})

    assert dto.temperature == temperature


def test_temperatura_zero_nao_e_trocada_pelo_default() -> None:
    dto = ModelConfigDTO.model_validate({**_BASE, "temperature": 0})

    assert dto.temperature == 0.0
    assert dto.temperature != 0.7


def test_temperatura_ausente_assume_o_default() -> None:
    dto = ModelConfigDTO.model_validate(_BASE)

    assert dto.temperature == 0.7


def test_temperatura_nula_assume_o_default() -> None:
    dto = ModelConfigDTO.model_validate({**_BASE, "temperature": None})

    assert dto.temperature == 0.7


@pytest.mark.parametrize("temperature", [float("nan"), float("inf"), float("-inf")])
def test_temperatura_nao_finita_e_recusada(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature deve estar entre 0 e 1"):
        ModelConfigDTO.model_validate({**_BASE, "temperature": temperature})


def test_temperatura_que_nao_e_numero_e_recusada() -> None:
    with pytest.raises(ValidationError):
        ModelConfigDTO.model_validate({**_BASE, "temperature": "quente"})


@pytest.mark.parametrize("temperature", [-0.1, 1.1])
def test_temperatura_fora_do_intervalo_e_recusada(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature deve estar entre 0 e 1"):
        ModelConfigDTO.model_validate({**_BASE, "temperature": temperature})


def test_endpoint_do_provedor_e_opcional() -> None:
    dto = ModelConfigDTO.model_validate(_BASE)

    assert dto.provider_config.endpoint is None


@pytest.mark.parametrize("max_tokens", [0, -1])
def test_max_tokens_nao_positivo_e_recusado(max_tokens: int) -> None:
    with pytest.raises(ValidationError):
        ModelConfigDTO.model_validate({**_BASE, "max_tokens": max_tokens})


def test_provider_invalido_e_recusado() -> None:
    with pytest.raises(ValidationError):
        ModelConfigDTO.model_validate({**_BASE, "provider": "invalido"})


@pytest.mark.parametrize("provider", list(ModelProviderEnum))
def test_aceita_todos_os_provedores_implementados(provider: ModelProviderEnum) -> None:
    dto = ModelConfigDTO.model_validate({**_BASE, "provider": provider.value})

    assert dto.provider is provider


def test_provider_local_deixou_de_ser_aceito() -> None:
    """Nunca houve serviço por trás de "local": o contrato agora recusa o valor."""
    with pytest.raises(ValidationError):
        ModelConfigDTO.model_validate({**_BASE, "provider": "local"})
