"""Entidades do protocolo de revisão auditável (thinking 05).

As referências estruturadas são a única via de mudança de estado: nada aqui interpreta texto livre.
"""
from datetime import UTC, datetime

import pytest

from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.criterion_evaluation import CriterionEvaluation
from src.domain.entities.thinking.result_revision import ResultRevision
from src.domain.entities.thinking.review_request import ReviewRequest
from src.domain.entities.thinking.revision_verdict import RevisionVerdict
from src.domain.entities.thinking.task import Task
from src.domain.entities.thinking.task_attempt import TaskAttempt
from src.domain.entities.thinking.verification_report import VerificationReport
from src.domain.enums.revision_verdict_enum import RevisionVerdictEnum
from src.domain.enums.task_status_enum import TaskStatusEnum
from src.domain.enums.verification_decision_enum import VerificationDecisionEnum

_CRITERIO = AcceptanceCriterion(id="T4-AC1", description="Investigação explicada.")
_INSTANTE = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def _aprovado(*ids: str) -> VerificationReport:
    return VerificationReport(
        decision=VerificationDecisionEnum.APPROVED,
        evaluations=tuple(CriterionEvaluation(criterion_id=i, met=True, justification=f"ok {i}") for i in ids),
        unmet_criteria_ids=(),
    )


def _revisora(**extra: object) -> Task:
    campos: dict = {"acceptance_criteria": (_CRITERIO,), **extra}
    return Task(
        id="T4", title="Investigar T3", description="Investigue a força e a dissipação.",
        review=ReviewRequest(task_ids=("T3",), reason="T3 contradiz T1 e T2."), **campos,
    )


def _veredito(task_id: str = "T3", verdict: RevisionVerdictEnum = RevisionVerdictEnum.SUPERSEDED) -> RevisionVerdict:
    return RevisionVerdict(task_id=task_id, verdict=verdict, justification="O impulso foi trocado.")


# ── Pedido de revisão planejado em C.2 ──────────────────────────────────────


def test_pedido_de_revisao_guarda_alvos_e_motivo() -> None:
    pedido = ReviewRequest(task_ids=("T3", "T2"), reason="Afirmações incompatíveis.")

    assert pedido.task_ids == ("T3", "T2")
    assert pedido.reason == "Afirmações incompatíveis."


@pytest.mark.parametrize(("task_ids", "reason"), [
    ((), "motivo"),
    (("T3", "T3"), "motivo"),
    (("T3", " "), "motivo"),
    (("T3",), "  "),
])
def test_pedido_de_revisao_recusa_alvos_vazios_repetidos_ou_sem_motivo(task_ids: tuple[str, ...], reason: str) -> None:
    with pytest.raises(ValueError):
        ReviewRequest(task_ids=task_ids, reason=reason)


# ── Tarefa: revisão e dependências explícitas ───────────────────────────────


def test_tarefa_normal_nao_tem_criterio_de_revisao_e_mantem_os_criterios_planejados() -> None:
    tarefa = Task(id="T1", title="t", description="d", acceptance_criteria=(_CRITERIO,))

    assert tarefa.review is None
    assert tarefa.depends_on == ()
    assert tarefa.revision_criterion is None
    # Desde a nova fase de validação — 02, toda tarefa também recebe o critério técnico fixo.
    assert tarefa.verification_criteria() == (_CRITERIO, tarefa.technical_criterion)


def test_tarefa_revisora_acrescenta_criterio_de_revisao_sem_reescrever_os_planejados() -> None:
    tarefa = _revisora()

    criterio = tarefa.revision_criterion
    assert criterio is not None and criterio.id == "T4-REV"
    assert "confirmed or superseded" in criterio.description
    assert tarefa.acceptance_criteria == (_CRITERIO,)
    assert tarefa.verification_criteria() == (_CRITERIO, tarefa.technical_criterion, criterio)


@pytest.mark.parametrize("extra", [
    {"depends_on": ("T1", "T1")},
    {"depends_on": ("T4",)},
    {"depends_on": (" ",)},
    {"depends_on": ("T3",)},
])
def test_tarefa_recusa_dependencia_repetida_autorreferente_vazia_ou_sobre_o_proprio_alvo(extra: dict) -> None:
    with pytest.raises(ValueError):
        _revisora(**extra)


def test_tarefa_recusa_revisar_a_si_mesma() -> None:
    with pytest.raises(ValueError):
        Task(id="T4", title="t", description="d", acceptance_criteria=(_CRITERIO,),
             review=ReviewRequest(task_ids=("T4",), reason="motivo"))


def test_tarefa_recusa_criterio_planejado_com_o_identificador_reservado_da_revisao() -> None:
    with pytest.raises(ValueError):
        _revisora(acceptance_criteria=(AcceptanceCriterion(id="T4-REV", description="x"),))


def test_resultado_aprovado_da_revisora_leva_vereditos_e_dependencias() -> None:
    tarefa = _revisora(depends_on=("T1",))
    tarefa.attempts.append(TaskAttempt(number=1, output="saida", conclusion="conclusao",
                                       report=_aprovado("T4-AC1", "T4-REV"), revision_verdicts=(_veredito(),)))
    tarefa.status = TaskStatusEnum.APPROVED

    resultado = tarefa.approved_result()

    assert resultado.revision_verdicts == (_veredito(),)
    assert resultado.depends_on == ("T1",)
    assert tarefa.revision_approval_justification() == "ok T4-REV"


def test_resultado_aprovado_da_tarefa_normal_nao_tem_revisao() -> None:
    tarefa = Task(id="T1", title="t", description="d", acceptance_criteria=(_CRITERIO,))
    tarefa.attempts.append(TaskAttempt(number=1, output="o", conclusion="c", report=_aprovado("T4-AC1")))
    tarefa.status = TaskStatusEnum.APPROVED

    assert tarefa.approved_result().revision_verdicts == ()
    assert tarefa.revision_approval_justification() is None


@pytest.mark.parametrize("vereditos", [(), (_veredito("T2"),), (_veredito(), _veredito())])
def test_revisora_aprovada_sem_um_veredito_por_alvo_nao_entrega_resultado(vereditos: tuple) -> None:
    tarefa = _revisora()
    tarefa.attempts.append(TaskAttempt(number=1, output="o", conclusion="c",
                                       report=_aprovado("T4-AC1", "T4-REV"), revision_verdicts=vereditos))
    tarefa.status = TaskStatusEnum.APPROVED

    with pytest.raises(ValueError):
        tarefa.approved_result()


def test_tarefa_normal_com_veredito_de_revisao_nao_entrega_resultado() -> None:
    tarefa = Task(id="T1", title="t", description="d", acceptance_criteria=(_CRITERIO,))
    tarefa.attempts.append(TaskAttempt(number=1, output="o", conclusion="c", report=_aprovado("T4-AC1"),
                                       revision_verdicts=(_veredito(),)))
    tarefa.status = TaskStatusEnum.APPROVED

    with pytest.raises(ValueError):
        tarefa.approved_result()


# ── Registro de auditoria ───────────────────────────────────────────────────


def test_registro_de_revisao_separa_substituidos_de_confirmados() -> None:
    registro = ResultRevision(
        revising_task_id="T5", reason="Contradição entre T2 e T3.",
        verdicts=(_veredito("T3"), _veredito("T2", RevisionVerdictEnum.CONFIRMED)),
        approval_justification="A investigação sustenta os vereditos.",
        suspended_task_ids=("T4",), reinstated_task_ids=(), withdrawn_learnings=("fato de T3",),
        restored_learnings=(), current_task_ids=("T1", "T2", "T5"), occurred_at=_INSTANTE,
    )

    assert registro.superseded_task_ids == ("T3",)
    assert registro.confirmed_task_ids == ("T2",)


def test_registro_de_revisao_exige_ao_menos_um_veredito() -> None:
    with pytest.raises(ValueError):
        ResultRevision(
            revising_task_id="T5", reason="motivo", verdicts=(), approval_justification="ok",
            suspended_task_ids=(), reinstated_task_ids=(), withdrawn_learnings=(), restored_learnings=(),
            current_task_ids=(), occurred_at=_INSTANTE,
        )
