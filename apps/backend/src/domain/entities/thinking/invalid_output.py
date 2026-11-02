from dataclasses import dataclass

from src.domain.enums.output_defect_enum import OutputDefectEnum


@dataclass(frozen=True)
class InvalidOutput:
    """Saída do modelo recusada pelo parser e posteriormente corrigida.

    Attributes:
        raw_output: Saída bruta recusada.
        reason: Motivo pelo qual o parser a recusou.
        defect: Tipo de defeito que motivou a recusa.
    """

    raw_output: str
    reason: str
    defect: OutputDefectEnum = OutputDefectEnum.CONTRACT
