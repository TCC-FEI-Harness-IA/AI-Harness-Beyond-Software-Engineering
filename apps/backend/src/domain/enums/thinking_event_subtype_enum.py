from enum import StrEnum


class ThinkingEventSubtypeEnum(StrEnum):
    """Enum dos subtipos de evento, mapeando 1:1 o contrato do WebSocket."""

    SETUP = "setup"
    TASKS = "tasks"
    EXECUTE = "execute"
    REASONING = "reasoning"
    VERIFY_PASS = "verify_pass"
    VERIFY_FAIL = "verify_fail"
    STORE = "store"
    LEARN = "learn"
    RESET = "reset"
    COMPILE = "compile"
    REPLAN = "replan"
