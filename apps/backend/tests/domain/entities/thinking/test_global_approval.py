import dataclasses

import pytest

from src.domain.entities.thinking.criterion_evaluation import CriterionEvaluation
from src.domain.entities.thinking.global_approval import GlobalApproval
from src.domain.entities.thinking.verification_report import VerificationReport
from src.domain.enums.verification_decision_enum import VerificationDecisionEnum


def _relatorio(aprovado: bool) -> VerificationReport:
    if aprovado:
        return VerificationReport(
            decision=VerificationDecisionEnum.APPROVED,
            evaluations=(CriterionEvaluation(criterion_id="AC1", met=True, justification="ok"),),
            unmet_criteria_ids=(),
        )
    return VerificationReport(
        decision=VerificationDecisionEnum.REPROVED,
        evaluations=(CriterionEvaluation(criterion_id="AC1", met=False, justification="falta"),),
        unmet_criteria_ids=("AC1",),
    )


def test_carrega_o_relatorio_e_o_conjunto_de_resultados_avaliado() -> None:
    relatorio = _relatorio(aprovado=True)

    aprovacao = GlobalApproval(report=relatorio, stored_results="## T1\n\nresultado", task_ids=("T1",))

    assert aprovacao.report is relatorio
    assert aprovacao.stored_results == "## T1\n\nresultado"
    assert aprovacao.task_ids == ("T1",)


def test_so_existe_para_um_relatorio_aprovado() -> None:
    with pytest.raises(ValueError, match="aprovado"):
        GlobalApproval(report=_relatorio(aprovado=False), stored_results="r", task_ids=("T1",))


def test_e_imutavel() -> None:
    aprovacao = GlobalApproval(report=_relatorio(aprovado=True), stored_results="r", task_ids=("T1",))

    with pytest.raises(dataclasses.FrozenInstanceError):
        aprovacao.stored_results = "outro"
