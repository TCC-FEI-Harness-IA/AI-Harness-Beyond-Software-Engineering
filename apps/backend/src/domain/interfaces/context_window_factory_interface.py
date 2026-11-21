from abc import ABC, abstractmethod

from src.domain.entities.llm.context_window import ContextWindow
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class IContextWindowFactory(ABC):
    """Contrato de criação de janelas de contexto novas (*Fresh Context*)."""

    @abstractmethod
    def create(self, phase: ThinkingPhaseEnum, task_id: str | None = None) -> ContextWindow:
        """Cria uma janela de contexto nova, com identidade própria.

        Args:
            phase: Fase de thinking que origina a janela.
            task_id: Tarefa associada, quando houver.

        Returns:
            ContextWindow: Janela de contexto recém-criada, vazia.
        """
        raise NotImplementedError
