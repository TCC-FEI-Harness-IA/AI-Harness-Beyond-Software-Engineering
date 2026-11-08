import pytest

from src.domain.entities.llm.model_info import ModelInfo


def test_aceita_modelo_so_com_o_identificador() -> None:
    modelo = ModelInfo(model_name="vendor/modelo")

    assert modelo.display_name is None
    assert modelo.context_length is None


def test_aceita_preco_zero() -> None:
    modelo = ModelInfo(model_name="vendor/gratis", input_price_per_million_tokens=0, output_price_per_million_tokens=0)

    assert modelo.input_price_per_million_tokens == 0


def test_recusa_identificador_em_branco() -> None:
    with pytest.raises(ValueError, match="model_name"):
        ModelInfo(model_name="   ")


@pytest.mark.parametrize("campo", ["input_price_per_million_tokens", "output_price_per_million_tokens"])
def test_recusa_preco_negativo(campo: str) -> None:
    with pytest.raises(ValueError, match=campo):
        ModelInfo(model_name="vendor/modelo", **{campo: -0.01})


@pytest.mark.parametrize("campo", ["context_length", "throughput_tokens_per_second"])
def test_recusa_contexto_e_vazao_nao_positivos(campo: str) -> None:
    with pytest.raises(ValueError, match=campo):
        ModelInfo(model_name="vendor/modelo", **{campo: 0})
