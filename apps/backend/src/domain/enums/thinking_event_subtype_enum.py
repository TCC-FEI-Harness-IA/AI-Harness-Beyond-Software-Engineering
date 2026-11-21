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
    # Planejamento validado (fluxo versão 2): o plano de A.2 é só candidato até A.3 aprová-lo. A
    # confirmação na fila continua sendo `tasks`, emitida uma única vez, depois da aprovação.
    PLAN_CANDIDATE = "plan_candidate"
    PLAN_APPROVED = "plan_approved"
    PLAN_REJECTED = "plan_rejected"
