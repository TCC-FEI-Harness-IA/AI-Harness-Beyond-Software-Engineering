from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class DecompositionValidationPhase(BaseThinkingPhase):
    """Fase A.3 — Task Decomposition Validator.

    Julga um único plano candidato de A.2 contra a rubrica fixa do template, com o pedido original e
    os critérios gerais, numa janela nova. Não resolve a pergunta nem devolve um plano substituto.
    """

    @property
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: `ThinkingPhaseEnum.A3_DECOMPOSITION_VALIDATION`.
        """
        return ThinkingPhaseEnum.A3_DECOMPOSITION_VALIDATION
