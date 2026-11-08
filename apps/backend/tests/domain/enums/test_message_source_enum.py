from src.domain.enums.message_source_enum import MessageSourceEnum


def test_declara_exatamente_as_origens_suportadas() -> None:
    assert {member.value for member in MessageSourceEnum} == {"user", "llm_agent", "system"}


def test_valores_de_cada_membro() -> None:
    assert MessageSourceEnum.USER == "user"
    assert MessageSourceEnum.LLM_AGENT == "llm_agent"
    assert MessageSourceEnum.SYSTEM == "system"


def test_e_uma_str_enum() -> None:
    assert isinstance(MessageSourceEnum.USER, str)
