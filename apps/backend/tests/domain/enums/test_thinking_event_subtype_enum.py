from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum

_ESPERADOS = {
    "setup",
    "tasks",
    "execute",
    "reasoning",
    "verify_pass",
    "verify_fail",
    "store",
    "learn",
    "reset",
    "compile",
    "replan",
}


def test_declara_exatamente_os_subtipos_do_contrato() -> None:
    assert {member.value for member in ThinkingEventSubtypeEnum} == _ESPERADOS


def test_valores_de_cada_membro() -> None:
    assert ThinkingEventSubtypeEnum.SETUP == "setup"
    assert ThinkingEventSubtypeEnum.TASKS == "tasks"
    assert ThinkingEventSubtypeEnum.EXECUTE == "execute"
    assert ThinkingEventSubtypeEnum.REASONING == "reasoning"
    assert ThinkingEventSubtypeEnum.VERIFY_PASS == "verify_pass"
    assert ThinkingEventSubtypeEnum.VERIFY_FAIL == "verify_fail"
    assert ThinkingEventSubtypeEnum.STORE == "store"
    assert ThinkingEventSubtypeEnum.LEARN == "learn"
    assert ThinkingEventSubtypeEnum.RESET == "reset"
    assert ThinkingEventSubtypeEnum.COMPILE == "compile"
    assert ThinkingEventSubtypeEnum.REPLAN == "replan"


def test_e_uma_str_enum() -> None:
    assert isinstance(ThinkingEventSubtypeEnum.SETUP, str)
