from typing import Any

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.structured_response_parser_interface import IStructuredResponseParser


class FakeStructuredParser(IStructuredResponseParser):
    """Dublê de `IStructuredResponseParser` com resultados programados em sequência.

    Cada item da fila é devolvido como saída parseada ou, quando é uma exceção,
    levantado — o que permite programar falhas de parsing e a recuperação delas.
    """

    def __init__(self, outcomes: list[dict[str, Any] | Exception] | None = None) -> None:
        """Configura o dublê.

        Args:
            outcomes: Fila de resultados, um por chamada de `parse`.
        """
        self.outcomes = list(outcomes) if outcomes else []
        self.parsed: list[tuple[str, ThinkingPhaseEnum]] = []
        self.validations: list[ValidationContext | None] = []
        self.finish_reasons: list[str | None] = []

    def parse(
        self,
        raw_output: str,
        phase: ThinkingPhaseEnum,
        validation: ValidationContext | None = None,
        finish_reason: str | None = None,
    ) -> dict[str, Any]:
        """Registra a chamada e devolve, ou levanta, o próximo resultado programado.

        Raises:
            Exception: Quando o próximo resultado programado é uma exceção.
            AssertionError: Quando a fila de resultados programados se esgota.
        """
        self.parsed.append((raw_output, phase))
        self.validations.append(validation)
        self.finish_reasons.append(finish_reason)

        if not self.outcomes:
            raise AssertionError(f"Parsing nº {len(self.parsed)} sem resultado programado.")

        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
