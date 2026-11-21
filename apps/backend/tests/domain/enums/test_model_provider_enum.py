from src.domain.enums.model_provider_enum import ModelProviderEnum


def test_declara_exatamente_os_provedores_suportados() -> None:
    assert {member.value for member in ModelProviderEnum} == {"open_router", "azure_ai_foundry", "openai"}


def test_valor_dos_membros() -> None:
    assert ModelProviderEnum.OPEN_ROUTER == "open_router"
    assert ModelProviderEnum.AZURE_AI_FOUNDRY == "azure_ai_foundry"
    assert ModelProviderEnum.OPENAI == "openai"


def test_e_uma_str_enum() -> None:
    assert isinstance(ModelProviderEnum.OPEN_ROUTER, str)
