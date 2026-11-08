from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum


def test_declara_exatamente_os_tipos_suportados() -> None:
    assert {member.value for member in ThinkingEventTypeEnum} == {"thinking", "result", "degraded", "error"}


def test_valores_de_cada_membro() -> None:
    assert ThinkingEventTypeEnum.THINKING == "thinking"
    assert ThinkingEventTypeEnum.RESULT == "result"
    assert ThinkingEventTypeEnum.DEGRADED == "degraded"
    assert ThinkingEventTypeEnum.ERROR == "error"


def test_e_uma_str_enum() -> None:
    assert isinstance(ThinkingEventTypeEnum.THINKING, str)
