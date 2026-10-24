from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class PlanningLearningsPhase(BaseThinkingPhase):
    """Fase A.3 — Salvar aprendizados pontuais do enunciado."""

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.A3_PLANNING_LEARNINGS`.
        """
        return ThinkingPhaseEnum.A3_PLANNING_LEARNINGS
