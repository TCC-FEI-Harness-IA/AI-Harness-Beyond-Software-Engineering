from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class AdditionalPlanningPhase(BaseThinkingPhase):
    """Fase C.2 — Planejamento adicional."""

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING`.
        """
        return ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING
