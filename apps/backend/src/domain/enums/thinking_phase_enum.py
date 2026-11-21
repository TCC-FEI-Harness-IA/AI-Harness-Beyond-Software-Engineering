from enum import StrEnum


class ThinkingPhaseEnum(StrEnum):
    """Enum das etapas do fluxo de thinking descrito no paper, com as extensões do harness.

    Cada valor persistido aponta um único membro, sem aliases. O significado de `A3` depende da
    versão do fluxo da sessão (`RalphFlowVersionEnum`): no fluxo atual (versão 2) é a validação da
    decomposição, e a extração dos aprendizados do enunciado passou a ser `A4`; nas sessões
    gravadas antes da validação (versão 1), `A3` registrou a extração dos aprendizados do enunciado.
    O histórico dessas sessões não é reescrito: a versão persistida é quem diz como lê-lo.
    """

    A1_GENERAL_CRITERIA = "A1"
    A2_TASK_DECOMPOSITION = "A2"
    A3_DECOMPOSITION_VALIDATION = "A3"
    A4_PLANNING_LEARNINGS = "A4"
    B1_TASK_RESOLUTION = "B1"
    B2_TASK_VERIFICATION = "B2"
    B3_RESULT_STORAGE = "B3"
    B4_LEARNINGS_EXTRACTION = "B4"
    C1_GLOBAL_VERIFICATION = "C1"
    C2_ADDITIONAL_PLANNING = "C2"
    C3_FINAL_ANSWER = "C3"
    DIRECT_INFERENCE = "DIRECT"
