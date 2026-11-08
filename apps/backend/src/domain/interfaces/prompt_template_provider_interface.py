from abc import ABC, abstractmethod

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class IPromptTemplateProvider(ABC):
    """Contrato de acesso aos templates de prompt de cada fase de thinking."""

    @abstractmethod
    def get(self, phase: ThinkingPhaseEnum) -> str:
        """Devolve o texto do template daquela fase.

        Args:
            phase: Fase de thinking cujo template deve ser carregado.

        Returns:
            str: Texto bruto do template.

        Raises:
            PromptTemplateNotFoundError: Quando o template não existe.
        """
        raise NotImplementedError

    @abstractmethod
    def render(self, phase: ThinkingPhaseEnum, variables: dict[str, str]) -> str:
        """Devolve o template da fase com os placeholders substituídos.

        Args:
            phase: Fase de thinking cujo template deve ser renderizado.
            variables: Mapa de placeholder para valor a substituir no template.

        Returns:
            str: Template renderizado.

        Raises:
            PromptTemplateNotFoundError: Quando o template não existe.
        """
        raise NotImplementedError
