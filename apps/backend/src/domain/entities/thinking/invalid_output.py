from dataclasses import dataclass


@dataclass(frozen=True)
class InvalidOutput:
    """Saída do modelo recusada pelo parser e posteriormente corrigida.

    Attributes:
        raw_output: Saída bruta recusada.
        reason: Motivo pelo qual o parser a recusou.
    """

    raw_output: str
    reason: str
