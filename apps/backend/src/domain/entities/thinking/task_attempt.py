from dataclasses import dataclass

from src.domain.entities.thinking.verification_report import VerificationReport


@dataclass(frozen=True)
class TaskAttempt:
    """Representa uma tentativa de resolução de tarefa (B.1) e seu veredito (B.2).

    Attributes:
        number: Número sequencial da tentativa, começando em 1.
        output: Saída produzida por B.1 nessa tentativa.
        report: Relatório de verificação de B.2, ou `None` antes de verificar.
    """

    number: int
    output: str
    report: VerificationReport | None
