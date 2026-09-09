from abc import ABC, abstractmethod
from typing import Any

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class IStructuredResponseParser(ABC):
    """Contrato de extração e validação do JSON estruturado produzido pelo modelo."""

    @abstractmethod
    def parse(self, raw_output: str, phase: ThinkingPhaseEnum) -> dict[str, Any]:
        """Extrai e valida o JSON produzido pelo modelo para a fase informada.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.

        Returns:
            dict[str, Any]: Estrutura JSON já validada contra o schema da fase.

        Raises:
            PhaseParsingError: Quando não há JSON válido ou o schema não confere.
        """
        raise NotImplementedError
