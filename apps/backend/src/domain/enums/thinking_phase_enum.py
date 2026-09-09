from enum import StrEnum


class ThinkingPhaseEnum(StrEnum):
    """Enum das etapas do fluxo de thinking descrito no paper."""

    A1_GENERAL_CRITERIA = "A1"
    A2_TASK_DECOMPOSITION = "A2"
    B1_TASK_RESOLUTION = "B1"
    B2_TASK_VERIFICATION = "B2"
    B3_RESULT_STORAGE = "B3"
    B4_LEARNINGS_EXTRACTION = "B4"
    C1_GLOBAL_VERIFICATION = "C1"
    C2_ADDITIONAL_PLANNING = "C2"
    C3_FINAL_ANSWER = "C3"
    DIRECT_INFERENCE = "DIRECT"
