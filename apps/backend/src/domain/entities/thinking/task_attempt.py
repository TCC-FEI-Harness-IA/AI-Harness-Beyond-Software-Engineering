from dataclasses import dataclass

from src.domain.entities.thinking.invalid_output import InvalidOutput
from src.domain.entities.thinking.verification_report import VerificationReport


@dataclass(frozen=True)
class TaskAttempt:
    """Representa uma tentativa de resolução de tarefa (B.1) e seu veredito (B.2).

    É o registro de que o orquestrador monta as entradas explícitas das fases seguintes: o
    feedback da nova tentativa de B.1 e o histórico da tarefa entregue a B.4.

    Attributes:
        number: Número sequencial da tentativa, começando em 1.
        output: Saída produzida por B.1 nessa tentativa.
        report: Relatório de verificação de B.2, ou `None` antes de verificar.
        resolution_invalid_outputs: Saídas de B.1 recusadas pelo parser e corrigidas nessa tentativa.
        verification_invalid_outputs: Saídas de B.2 recusadas pelo parser e corrigidas nessa tentativa.
    """

    number: int
    output: str
    report: VerificationReport | None
    resolution_invalid_outputs: tuple[InvalidOutput, ...] = ()
    verification_invalid_outputs: tuple[InvalidOutput, ...] = ()
