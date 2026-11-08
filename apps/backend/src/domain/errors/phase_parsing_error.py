from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.length_interruption_enum import LengthInterruptionEnum
from src.domain.enums.output_defect_enum import OutputDefectEnum
from src.domain.enums.output_syntax_status_enum import OutputSyntaxStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.ralph_error import RalphError


class PhaseParsingError(RalphError):
    """Levantado quando a saída do modelo não é JSON válido para a fase ou viola o seu contrato.

    Attributes:
        phase: Fase de thinking em que o parsing falhou.
        raw_output: Saída bruta devolvida pelo modelo.
        reason: Motivo da falha de parsing.
        limit: Limite operacional que motivou a recusa, quando a saída é válida mas excede um limite.
        defect: Tipo de defeito da saída, que decide a correção pedida ao modelo.
        diagnostic: Diagnóstico estruturado da recusa (sintaxe, contrato, código do problema e corte por
            comprimento), quando o parser o produz; `None` não presume nenhuma classificação.
    """

    def __init__(
        self,
        phase: ThinkingPhaseEnum,
        raw_output: str,
        reason: str,
        limit: BudgetLimitEnum | None = None,
        defect: OutputDefectEnum = OutputDefectEnum.CONTRACT,
        diagnostic: OutputDiagnostic | None = None,
    ) -> None:
        """Inicializa o erro.

        Args:
            phase: Fase de thinking em que o parsing falhou.
            raw_output: Saída bruta devolvida pelo modelo.
            reason: Motivo da falha de parsing.
            limit: Limite operacional que motivou a recusa, quando houver.
            defect: Tipo de defeito da saída; por padrão, violação do contrato da fase.
            diagnostic: Diagnóstico estruturado da recusa, quando houver.
        """
        self.phase = phase
        self.raw_output = raw_output
        self.reason = reason
        self.limit = limit
        if diagnostic is not None and diagnostic.syntax_status is OutputSyntaxStatusEnum.INVALID:
            defect = (
                OutputDefectEnum.TRUNCATED
                if diagnostic.length_interruption is LengthInterruptionEnum.CONFIRMED
                else OutputDefectEnum.SYNTAX
            )
        self.defect = defect
        self.diagnostic = diagnostic
        super().__init__(f"Falha ao parsear a saída da fase '{phase.value}': {reason}")
