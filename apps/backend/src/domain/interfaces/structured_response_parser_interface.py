from abc import ABC, abstractmethod
from typing import Any

from src.domain.entities.thinking.parsed_output import ParsedOutput
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class IStructuredResponseParser(ABC):
    """Contrato de extração e validação do JSON estruturado produzido pelo modelo."""

    @abstractmethod
    def parse_output(
        self,
        raw_output: str,
        phase: ThinkingPhaseEnum,
        validation: ValidationContext | None = None,
        finish_reason: str | None = None,
    ) -> ParsedOutput:
        """Extrai e valida o JSON produzido pelo modelo, devolvendo também o diagnóstico da saída.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.
            validation: Dados esperados pela chamada. É obrigatório nas fases de verificação
                (B.2 e C.1), que precisam avaliar exatamente os critérios informados; nas fases
                de planejamento, restringe o tamanho e os identificadores do lote.
            finish_reason: Motivo de término informado pelo provedor, quando há. Um JSON que só
                deixou de fechar as últimas chaves ou colchetes é reparado, exceto quando a
                saída foi cortada pelo limite de tokens (`"length"`): aí o que falta pode ser
                conteúdo, e não apenas fechamentos. O motivo original vai para o diagnóstico.

        Returns:
            ParsedOutput: Estrutura validada contra o schema da fase e diagnóstico de aceite
                (sintaxe válida ou válida após reparo, contrato válido, corte por comprimento).

        Raises:
            PhaseParsingError: Quando não há JSON válido, o schema não confere ou a saída
                contradiz o contexto de validação; o erro carrega o diagnóstico da recusa.
            ValueError: Quando uma fase de verificação é chamada sem os critérios esperados.
        """
        raise NotImplementedError

    def parse(
        self,
        raw_output: str,
        phase: ThinkingPhaseEnum,
        validation: ValidationContext | None = None,
        finish_reason: str | None = None,
    ) -> dict[str, Any]:
        """Extrai e valida o JSON produzido pelo modelo, devolvendo só a estrutura validada.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.
            validation: Dados esperados pela chamada, como em `parse_output`.
            finish_reason: Motivo de término informado pelo provedor, quando há.

        Returns:
            dict[str, Any]: Estrutura JSON já validada contra o schema da fase.

        Raises:
            PhaseParsingError: Nas mesmas situações de `parse_output`.
            ValueError: Quando uma fase de verificação é chamada sem os critérios esperados.
        """
        return self.parse_output(
            raw_output=raw_output, phase=phase, validation=validation, finish_reason=finish_reason
        ).parsed
