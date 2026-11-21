from src.domain.entities.llm.llm_provider_response import LLMProviderResponse


def test_carrega_texto_e_consumo() -> None:
    response = LLMProviderResponse(output_text="resposta", input_tokens=3, output_tokens=5)

    assert response.output_text == "resposta"
    assert response.input_tokens == 3
    assert response.output_tokens == 5


def test_campos_opcionais_tem_defaults() -> None:
    response = LLMProviderResponse(output_text="", input_tokens=0, output_tokens=0)

    assert response.finish_reason is None
    assert response.raw_response == {}


def test_raw_response_nao_e_compartilhado_entre_instancias() -> None:
    primeiro = LLMProviderResponse(output_text="", input_tokens=0, output_tokens=0)
    segundo = LLMProviderResponse(output_text="", input_tokens=0, output_tokens=0)

    primeiro.raw_response["chave"] = "valor"

    assert segundo.raw_response == {}


def test_nao_ha_identificador_de_resposta_por_padrao() -> None:
    response = LLMProviderResponse(output_text="r", input_tokens=1, output_tokens=2)

    assert response.response_id is None


def test_cada_contador_pode_ser_desconhecido_de_forma_independente() -> None:
    response = LLMProviderResponse(
        output_text="r", input_tokens=5, output_tokens=None, response_id="resp-1"
    )

    assert response.input_tokens == 5
    assert response.output_tokens is None
    assert response.response_id == "resp-1"
