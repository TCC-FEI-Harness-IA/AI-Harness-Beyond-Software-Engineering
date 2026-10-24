from dataclasses import dataclass

from src.domain.entities.thinking.criterion_evaluation import CriterionEvaluation
from src.domain.enums.verification_decision_enum import VerificationDecisionEnum


@dataclass(frozen=True)
class VerificationReport:
    """Representa a saída de uma verificação de critérios (B.2 ou C.1).

    Attributes:
        decision: Decisão consolidada da verificação.
        evaluations: Veredito de cada critério avaliado.
        unmet_criteria_ids: Identificadores dos critérios não satisfeitos.
    """

    decision: VerificationDecisionEnum
    evaluations: tuple[CriterionEvaluation, ...]
    unmet_criteria_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Recusa combinações internamente contraditórias.

        A cobertura contra os critérios esperados da chamada não é verificada aqui: ela
        depende de dados externos ao relatório e fica a cargo do `ValidationContext`.

        Raises:
            ValueError: Quando não há avaliações, quando um critério é avaliado ou apontado
                como pendente mais de uma vez, quando as pendências não são exatamente os
                critérios com `met=False`, ou quando a decisão contradiz as avaliações.
        """
        if not self.evaluations:
            raise ValueError("Um relatório de verificação precisa ter ao menos uma avaliação.")

        evaluated_ids = [evaluation.criterion_id for evaluation in self.evaluations]
        if len(set(evaluated_ids)) != len(evaluated_ids):
            raise ValueError("Um critério não pode ser avaliado mais de uma vez no mesmo relatório.")

        if len(set(self.unmet_criteria_ids)) != len(self.unmet_criteria_ids):
            raise ValueError("Um critério não pode se repetir entre as pendências do relatório.")

        failed_ids = {evaluation.criterion_id for evaluation in self.evaluations if not evaluation.met}
        if set(self.unmet_criteria_ids) != failed_ids:
            raise ValueError("As pendências devem ser exatamente os critérios avaliados com met=False.")

        if self.decision is VerificationDecisionEnum.APPROVED and failed_ids:
            raise ValueError("Um relatório aprovado não pode ter critérios não atendidos.")

        if self.decision is VerificationDecisionEnum.REPROVED and not failed_ids:
            raise ValueError("Um relatório reprovado precisa ter ao menos um critério não atendido.")

    @property
    def approved(self) -> bool:
        """Informa se a verificação foi aprovada.

        Returns:
            bool: `True` quando a decisão é `VerificationDecisionEnum.APPROVED`.
        """
        return self.decision is VerificationDecisionEnum.APPROVED
