from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class TaskVerificationPhase(BaseThinkingPhase):
    """Fase B.2 — Verificação dos critérios de aceite da tarefa."""

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.B2_TASK_VERIFICATION`.
        """
        raise NotImplementedError
