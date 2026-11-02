from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.ralph_error import RalphError


class PhaseParsingError(RalphError):
    """Levantado quando a saída do modelo não é JSON válido para a fase ou viola o seu contrato.

    Attributes:
        phase: Fase de thinking em que o parsing falhou.
        raw_output: Saída bruta devolvida pelo modelo.
        reason: Motivo da falha de parsing.
        limit: Limite operacional que motivou a recusa, quando a saída é válida mas excede um limite.
        diagnostic: Diagnóstico estruturado da recusa (sintaxe, contrato, código do problema e corte por
            comprimento), quando o parser o produz; `None` não presume nenhuma classificação.
    """

    def __init__(
        self,
        phase: ThinkingPhaseEnum,
        raw_output: str,
        reason: str,
        limit: BudgetLimitEnum | None = None,
        diagnostic: OutputDiagnostic | None = None,
    ) -> None:
        """Inicializa o erro.

        Args:
            phase: Fase de thinking em que o parsing falhou.
            raw_output: Saída bruta devolvida pelo modelo.
            reason: Motivo da falha de parsing.
            limit: Limite operacional que motivou a recusa, quando houver.
            diagnostic: Diagnóstico estruturado da recusa, quando houver.
        """
        self.phase = phase
        self.raw_output = raw_output
        self.reason = reason
        self.limit = limit
        self.diagnostic = diagnostic
        super().__init__(f"Falha ao parsear a saída da fase '{phase.value}': {reason}")
