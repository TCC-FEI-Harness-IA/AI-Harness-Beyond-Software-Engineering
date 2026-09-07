from src.domain.enums.model_provider_enum import ModelProviderEnum


def test_declara_exatamente_os_provedores_suportados() -> None:
    assert {member.value for member in ModelProviderEnum} == {"open_router"}


def test_valor_do_membro() -> None:
    assert ModelProviderEnum.OPEN_ROUTER == "open_router"


def test_e_uma_str_enum() -> None:
    assert isinstance(ModelProviderEnum.OPEN_ROUTER, str)
