from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class TaskResolutionPhase(BaseThinkingPhase):
    """Fase B.1 — Seleção da tarefa e resolução."""

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.B1_TASK_RESOLUTION`.
        """
        raise NotImplementedError
