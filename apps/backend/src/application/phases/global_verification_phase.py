from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class GlobalVerificationPhase(BaseThinkingPhase):
    """Fase C.1 — Compilação e verificação dos critérios gerais."""

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION`.
        """
        return ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION
