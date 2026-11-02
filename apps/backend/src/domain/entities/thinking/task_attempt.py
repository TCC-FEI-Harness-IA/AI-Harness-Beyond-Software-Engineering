from dataclasses import dataclass

from src.domain.entities.thinking.invalid_output import InvalidOutput
from src.domain.entities.thinking.verification_report import VerificationReport


@dataclass(frozen=True)
class TaskAttempt:
    """Representa uma tentativa de resolução de tarefa (B.1) e seu veredito (B.2).

    Attributes:
        number: Número sequencial da tentativa, começando em 1.
        output: Saída produzida por B.1 nessa tentativa.
        report: Relatório de verificação de B.2, ou `None` antes de verificar.
        invalid_verifier_outputs: Saídas do validador recusadas pelo parser e corrigidas antes do
            relatório válido. Fazem parte do histórico da tarefa que B.4 recebe.
    """

    number: int
    output: str
    report: VerificationReport | None
    invalid_verifier_outputs: tuple[InvalidOutput, ...] = ()
