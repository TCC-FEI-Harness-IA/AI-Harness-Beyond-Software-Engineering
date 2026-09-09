from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_ESPERADOS = {
    "A1": "A1",
    "A2": "A2",
    "B1": "B1",
    "B2": "B2",
    "B3": "B3",
    "B4": "B4",
    "C1": "C1",
    "C2": "C2",
    "C3": "C3",
    "DIRECT": "DIRECT",
}


def test_declara_exatamente_as_fases_do_paper() -> None:
    assert {member.value for member in ThinkingPhaseEnum} == set(_ESPERADOS.values())


def test_valores_de_cada_membro() -> None:
    assert ThinkingPhaseEnum.A1_GENERAL_CRITERIA == "A1"
    assert ThinkingPhaseEnum.A2_TASK_DECOMPOSITION == "A2"
    assert ThinkingPhaseEnum.B1_TASK_RESOLUTION == "B1"
    assert ThinkingPhaseEnum.B2_TASK_VERIFICATION == "B2"
    assert ThinkingPhaseEnum.B3_RESULT_STORAGE == "B3"
    assert ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION == "B4"
    assert ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION == "C1"
    assert ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING == "C2"
    assert ThinkingPhaseEnum.C3_FINAL_ANSWER == "C3"
    assert ThinkingPhaseEnum.DIRECT_INFERENCE == "DIRECT"


def test_e_uma_str_enum() -> None:
    assert isinstance(ThinkingPhaseEnum.A1_GENERAL_CRITERIA, str)
