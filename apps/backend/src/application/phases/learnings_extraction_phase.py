from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class LearningsExtractionPhase(BaseThinkingPhase):
    """Fase B.4 — Armazenamento dos aprendizados pontuais."""

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION`.
        """
        raise NotImplementedError
