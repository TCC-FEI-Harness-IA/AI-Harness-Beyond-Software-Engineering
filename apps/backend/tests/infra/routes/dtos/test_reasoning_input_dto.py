from src.infra.routes.v1.message.dtos.reasoning_input_dto import ReasoningInputDTO

_PAYLOAD = {
    "message": {"user_input": "pergunta do usuario"},
    "llm_model_config": {
        "provider": "open_router",
        "provider_config": {"model_name": "vendor/modelo"},
        "max_tokens": 1200,
        "temperature": 0.3,
    },
}


def test_carrega_a_mensagem_e_a_configuracao_do_modelo() -> None:
    dto = ReasoningInputDTO.model_validate(_PAYLOAD)

    assert dto.message.user_input == "pergunta do usuario"
    assert dto.llm_model_config.provider == "open_router"
    assert dto.llm_model_config.provider_config.model_name == "vendor/modelo"
    assert dto.llm_model_config.max_tokens == 1200
    assert dto.llm_model_config.temperature == 0.3
