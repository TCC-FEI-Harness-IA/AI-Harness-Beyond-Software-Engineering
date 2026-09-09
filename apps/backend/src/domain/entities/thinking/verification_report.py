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

    @property
    def approved(self) -> bool:
        """Informa se a verificação foi aprovada.

        Returns:
            bool: `True` quando a decisão é `VerificationDecisionEnum.APPROVED`.
        """
        raise NotImplementedError
