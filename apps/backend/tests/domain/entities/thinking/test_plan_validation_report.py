import dataclasses

import pytest

from src.domain.entities.thinking.plan_validation_issue import PlanValidationIssue
from src.domain.entities.thinking.plan_validation_report import PlanValidationReport


def _problema(task_id: str | None = "T2", criterion_id: str | None = "T2-AC1") -> PlanValidationIssue:
    return PlanValidationIssue(
        task_id=task_id,
        criterion_id=criterion_id,
        problem="The criterion requires an unestablished conclusion.",
        adjustment="Ask for an investigation that keeps the conclusion open.",
    )


def test_aprovacao_valida_nao_tem_problemas() -> None:
    relatorio = PlanValidationReport(approved=True, issues=())

    assert relatorio.approved is True
    assert relatorio.issues == ()


def test_reprovacao_valida_tem_ao_menos_um_problema_concreto() -> None:
    relatorio = PlanValidationReport(approved=False, issues=(_problema(),))

    assert relatorio.approved is False
    assert relatorio.issues[0].task_id == "T2"
    assert relatorio.issues[0].criterion_id == "T2-AC1"


def test_aprovacao_com_problema_pendente_e_incoerente() -> None:
    with pytest.raises(ValueError):
        PlanValidationReport(approved=True, issues=(_problema(),))


def test_reprovacao_sem_problema_e_incoerente() -> None:
    with pytest.raises(ValueError):
        PlanValidationReport(approved=False, issues=())


@pytest.mark.parametrize("task_id, criterion_id", [(None, None), ("T1", None), ("T1", "T1-AC2")])
def test_escopos_validos_do_problema(task_id: str | None, criterion_id: str | None) -> None:
    problema = _problema(task_id=task_id, criterion_id=criterion_id)

    assert problema.scope_task_id == task_id
    assert problema.is_plan_wide is (task_id is None)


def test_criterio_sem_tarefa_e_recusado() -> None:
    with pytest.raises(ValueError):
        _problema(task_id=None, criterion_id="T1-AC1")


@pytest.mark.parametrize("campo", ["problem", "adjustment"])
@pytest.mark.parametrize("valor", ["", "   "])
def test_problema_e_ajuste_precisam_de_texto(campo: str, valor: str) -> None:
    argumentos = dataclasses.asdict(_problema()) | {campo: valor}

    with pytest.raises(ValueError):
        PlanValidationIssue(**argumentos)


def test_e_imutavel() -> None:
    relatorio = PlanValidationReport(approved=True, issues=())

    with pytest.raises(dataclasses.FrozenInstanceError):
        relatorio.approved = False  # type: ignore[misc]
