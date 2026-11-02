from dataclasses import dataclass

from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic


@dataclass(frozen=True)
class InvalidOutput:
    """Saída do modelo recusada pelo parser.

    Attributes:
        raw_output: Saída bruta recusada.
        reason: Motivo pelo qual o parser a recusou.
        invocation_id: Invocação que produziu a saída, quando conhecida.
        diagnostic: Diagnóstico estruturado da recusa, quando conhecido.
    """

    raw_output: str
    reason: str
    invocation_id: str | None = None
    diagnostic: OutputDiagnostic | None = None
