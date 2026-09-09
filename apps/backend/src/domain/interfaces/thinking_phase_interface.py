from abc import ABC, abstractmethod

from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.thinking.phase_outcome import PhaseOutcome
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class IThinkingPhase(ABC):
    """Contrato de uma etapa (Strategy) do fluxo de thinking."""

    @property
    @abstractmethod
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: Identificador da fase.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute(self, context: ContextWindow, variables: dict[str, str]) -> PhaseOutcome:
        """Executa a fase sobre a janela de contexto informada.

        Args:
            context: Janela de contexto em que a fase é executada.
            variables: Placeholders a substituir no template da fase.

        Returns:
            PhaseOutcome: Resultado da execução da fase.
        """
        raise NotImplementedError
