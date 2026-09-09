import logging
from typing import Any

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.structured_response_parser_interface import IStructuredResponseParser


class StructuredResponseParserAdapter(IStructuredResponseParser):
    """Adapter de `IStructuredResponseParser` apoiado em `json.loads`."""

    def __init__(self, logger: logging.Logger) -> None:
        """Inicializa o adapter.

        Args:
            logger: Logger do módulo.
        """
        self.logger = logger

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
