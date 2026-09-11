import dataclasses

import pytest

from src.domain.entities.thinking.criterion_evaluation import CriterionEvaluation
from src.domain.entities.thinking.verification_report import VerificationReport
from src.domain.enums.verification_decision_enum import VerificationDecisionEnum

_AVALIACAO = CriterionEvaluation(criterion_id="c1", met=True, justification="ok")


def test_carrega_os_campos_informados() -> None:
    relatorio = VerificationReport(
        decision=VerificationDecisionEnum.APPROVED,
        evaluations=(_AVALIACAO,),
        unmet_criteria_ids=(),
    )

    assert relatorio.decision is VerificationDecisionEnum.APPROVED
    assert relatorio.evaluations == (_AVALIACAO,)
    assert relatorio.unmet_criteria_ids == ()


def test_e_imutavel() -> None:
    relatorio = VerificationReport(
        decision=VerificationDecisionEnum.APPROVED,
        evaluations=(_AVALIACAO,),
        unmet_criteria_ids=(),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        relatorio.decision = VerificationDecisionEnum.REPROVED


def test_aprovado_reflete_a_decisao() -> None:
    aprovado = VerificationReport(
        decision=VerificationDecisionEnum.APPROVED,
        evaluations=(),
        unmet_criteria_ids=(),
    )
    reprovado = VerificationReport(
        decision=VerificationDecisionEnum.REPROVED,
        evaluations=(),
        unmet_criteria_ids=("AC1",),
    )

    assert aprovado.approved is True
    assert reprovado.approved is False
