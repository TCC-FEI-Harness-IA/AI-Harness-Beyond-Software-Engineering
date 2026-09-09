from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class TaskDecompositionPhase(BaseThinkingPhase):
    """Fase A.2 — Quebra em tarefas de objetivo único."""

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.A2_TASK_DECOMPOSITION`.
        """
        raise NotImplementedError
