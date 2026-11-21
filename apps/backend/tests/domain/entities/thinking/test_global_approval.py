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


def _aprovacao(task_ids: tuple[str, ...] = ("T1",)) -> GlobalApproval:
    return GlobalApproval(
        report=_relatorio(aprovado=True), stored_results="r", task_ids=task_ids, learnings="- fato"
    )


def test_carrega_o_relatorio_o_conjunto_de_resultados_e_a_memoria_avaliados() -> None:
    relatorio = _relatorio(aprovado=True)

    aprovacao = GlobalApproval(
        report=relatorio, stored_results="## T1\n\nresultado", task_ids=("T1",), learnings="- fato vigente"
    )

    assert aprovacao.report is relatorio
    assert aprovacao.stored_results == "## T1\n\nresultado"
    assert aprovacao.task_ids == ("T1",)
    assert aprovacao.learnings == "- fato vigente"


def test_aceita_a_sintese_enquanto_os_resultados_vigentes_sao_os_aprovados() -> None:
    _aprovacao(task_ids=("T1", "T4")).ensure_current(current_task_ids=("T1", "T4"))


@pytest.mark.parametrize("vigentes", [("T1",), ("T1", "T4", "T5"), ("T4", "T1"), ()])
def test_recusa_a_sintese_quando_os_resultados_vigentes_mudaram_depois_da_aprovacao(
    vigentes: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="nova verificação global"):
        _aprovacao(task_ids=("T1", "T4")).ensure_current(current_task_ids=vigentes)


def test_so_existe_para_um_relatorio_aprovado() -> None:
    with pytest.raises(ValueError, match="aprovado"):
        GlobalApproval(report=_relatorio(aprovado=False), stored_results="r", task_ids=("T1",), learnings="")


def test_e_imutavel() -> None:
    aprovacao = _aprovacao()

    with pytest.raises(dataclasses.FrozenInstanceError):
        aprovacao.stored_results = "outro"
