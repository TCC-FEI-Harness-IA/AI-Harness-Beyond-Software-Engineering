from dataclasses import dataclass
from typing import Any

from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic


@dataclass(frozen=True)
class ParsedOutput:
    """Saída aceita pelo parser, com a estrutura validada e o diagnóstico de aceite.

    Attributes:
        parsed: Estrutura JSON já validada contra o contrato da fase.
        diagnostic: Diagnóstico da saída: sintaxe (talvez após reparo), contrato e corte.
    """

    parsed: dict[str, Any]
    diagnostic: OutputDiagnostic

    def __post_init__(self) -> None:
        """Exige um diagnóstico de conteúdo aceito.

        Raises:
            ValueError: Quando o diagnóstico é de recusa.
        """
        if not self.diagnostic.content_accepted:
            raise ValueError("Uma saída parseada exige diagnóstico de conteúdo aceito.")
