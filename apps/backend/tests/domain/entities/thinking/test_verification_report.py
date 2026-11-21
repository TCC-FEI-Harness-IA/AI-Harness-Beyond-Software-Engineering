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


_REPROVADA = CriterionEvaluation(criterion_id="c2", met=False, justification="falhou")


def test_aprovado_reflete_a_decisao() -> None:
    aprovado = VerificationReport(
        decision=VerificationDecisionEnum.APPROVED,
        evaluations=(_AVALIACAO,),
        unmet_criteria_ids=(),
    )
    reprovado = VerificationReport(
        decision=VerificationDecisionEnum.REPROVED,
        evaluations=(_AVALIACAO, _REPROVADA),
        unmet_criteria_ids=("c2",),
    )

    assert aprovado.approved is True
    assert reprovado.approved is False


def test_recusa_relatorio_sem_nenhuma_avaliacao() -> None:
    with pytest.raises(ValueError, match="avaliação"):
        VerificationReport(decision=VerificationDecisionEnum.APPROVED, evaluations=(), unmet_criteria_ids=())


def test_recusa_avaliacoes_repetidas_para_o_mesmo_criterio() -> None:
    with pytest.raises(ValueError, match="avaliado mais de uma vez"):
        VerificationReport(
            decision=VerificationDecisionEnum.APPROVED,
            evaluations=(_AVALIACAO, _AVALIACAO),
            unmet_criteria_ids=(),
        )


def test_recusa_aprovacao_com_criterio_nao_atendido() -> None:
    with pytest.raises(ValueError, match="aprovad"):
        VerificationReport(
            decision=VerificationDecisionEnum.APPROVED,
            evaluations=(_AVALIACAO, _REPROVADA),
            unmet_criteria_ids=("c2",),
        )


def test_recusa_reprovacao_sem_criterio_nao_atendido() -> None:
    with pytest.raises(ValueError, match="reprovad"):
        VerificationReport(
            decision=VerificationDecisionEnum.REPROVED,
            evaluations=(_AVALIACAO,),
            unmet_criteria_ids=(),
        )


def test_recusa_pendencias_que_nao_correspondem_as_avaliacoes_falsas() -> None:
    with pytest.raises(ValueError, match="pendências"):
        VerificationReport(
            decision=VerificationDecisionEnum.REPROVED,
            evaluations=(_AVALIACAO, _REPROVADA),
            unmet_criteria_ids=("c1",),
        )


def test_recusa_pendencias_repetidas() -> None:
    with pytest.raises(ValueError, match="repet"):
        VerificationReport(
            decision=VerificationDecisionEnum.REPROVED,
            evaluations=(_AVALIACAO, _REPROVADA),
            unmet_criteria_ids=("c2", "c2"),
        )
