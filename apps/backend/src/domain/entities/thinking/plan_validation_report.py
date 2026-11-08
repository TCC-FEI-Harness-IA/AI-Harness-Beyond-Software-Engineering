from dataclasses import dataclass

from src.domain.entities.thinking.plan_validation_issue import PlanValidationIssue


@dataclass(frozen=True)
class PlanValidationReport:
    """Relatório da validação da decomposição (A.3) sobre um único plano candidato.

    É um contrato próprio, separado do `VerificationReport` de B.2/C.1: a decisão é um booleano real e
    os problemas apontam tarefas e critérios do candidato julgado. Uma reprovação coerente é um
    resultado semântico normal; o relatório nunca é ajustado automaticamente.

    Attributes:
        approved: `True` quando o plano pode ser confirmado na fila.
        issues: Problemas impeditivos; vazio exatamente quando aprovado.
    """

    approved: bool
    issues: tuple[PlanValidationIssue, ...]

    def __post_init__(self) -> None:
        """Recusa combinações incoerentes entre a decisão e os problemas.

        Raises:
            ValueError: Quando uma aprovação traz problemas pendentes ou uma reprovação não traz nenhum.
        """
        if self.approved and self.issues:
            raise ValueError("Um plano aprovado não pode ter problemas impeditivos pendentes.")
        if not self.approved and not self.issues:
            raise ValueError("Um plano reprovado precisa de ao menos um problema concreto.")
