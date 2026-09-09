from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class GeneralCriteriaPhase(BaseThinkingPhase):
    """Fase A.1 — Definição dos critérios de aceite gerais."""

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.A1_GENERAL_CRITERIA`.
        """
        raise NotImplementedError
