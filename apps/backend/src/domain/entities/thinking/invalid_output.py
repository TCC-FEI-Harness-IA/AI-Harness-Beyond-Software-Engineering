from dataclasses import dataclass

from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.enums.output_defect_enum import OutputDefectEnum


@dataclass(frozen=True)
class InvalidOutput:
    """Saída do modelo recusada pelo parser.

    Attributes:
        raw_output: Saída bruta recusada.
        reason: Motivo pelo qual o parser a recusou.
        defect: Tipo de defeito que motivou a recusa.
        invocation_id: Invocação que produziu a saída, quando conhecida.
        diagnostic: Diagnóstico estruturado da recusa, quando conhecido.
    """

    raw_output: str
    reason: str
    defect: OutputDefectEnum = OutputDefectEnum.CONTRACT
    invocation_id: str | None = None
    diagnostic: OutputDiagnostic | None = None
