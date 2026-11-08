from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class PlanningLearningsPhase(BaseThinkingPhase):
    """Fase A.4 — Salvar aprendizados pontuais do enunciado.

    Era a A.3 do fluxo versão 1; desde a validação da decomposição, roda depois da aprovação do plano.
    """

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.A4_PLANNING_LEARNINGS`.
        """
        return ThinkingPhaseEnum.A4_PLANNING_LEARNINGS
