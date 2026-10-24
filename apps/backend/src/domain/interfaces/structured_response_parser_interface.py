from abc import ABC, abstractmethod
from typing import Any

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class IStructuredResponseParser(ABC):
    """Contrato de extração e validação do JSON estruturado produzido pelo modelo."""

    @abstractmethod
    def parse(
        self,
        raw_output: str,
        phase: ThinkingPhaseEnum,
        validation: ValidationContext | None = None,
    ) -> dict[str, Any]:
        """Extrai e valida o JSON produzido pelo modelo para a fase informada.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.
            validation: Dados esperados pela chamada. É obrigatório nas fases de verificação
                (B.2 e C.1), que precisam avaliar exatamente os critérios informados; nas fases
                de planejamento, restringe o tamanho e os identificadores do lote.

        Returns:
            dict[str, Any]: Estrutura JSON já validada contra o schema da fase.

        Raises:
            PhaseParsingError: Quando não há JSON válido, o schema não confere ou a saída
                contradiz o contexto de validação.
            ValueError: Quando uma fase de verificação é chamada sem os critérios esperados.
        """
        raise NotImplementedError
