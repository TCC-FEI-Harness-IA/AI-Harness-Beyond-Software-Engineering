from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class FinalAnswerPhase(BaseThinkingPhase):
    """Fase C.3 — Construção da resposta final."""

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.C3_FINAL_ANSWER`.
        """
        return ThinkingPhaseEnum.C3_FINAL_ANSWER
