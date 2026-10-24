import pytest

from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.criterion_evaluation import CriterionEvaluation
from src.domain.entities.thinking.task import Task
from src.domain.entities.thinking.task_attempt import TaskAttempt
from src.domain.entities.thinking.task_result import TaskResult
from src.domain.entities.thinking.verification_report import VerificationReport
from src.domain.enums.task_status_enum import TaskStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.enums.verification_decision_enum import VerificationDecisionEnum

_CRITERIO = AcceptanceCriterion(id="c1", description="descricao do criterio")


def _nova_tarefa() -> Task:
    return Task(
        id="t1",
        title="titulo",
        description="descricao",
        expected_input="entrada esperada",
        expected_output="saida esperada",
        acceptance_criteria=(_CRITERIO,),
    )


def test_carrega_os_campos_obrigatorios() -> None:
    tarefa = _nova_tarefa()

    assert tarefa.id == "t1"
    assert tarefa.title == "titulo"
    assert tarefa.description == "descricao"
    assert tarefa.expected_input == "entrada esperada"
    assert tarefa.expected_output == "saida esperada"
    assert tarefa.acceptance_criteria == (_CRITERIO,)


def test_defaults_de_uma_tarefa_nova() -> None:
    tarefa = _nova_tarefa()

    assert tarefa.status is TaskStatusEnum.PENDING
    assert tarefa.origin_phase is ThinkingPhaseEnum.A2_TASK_DECOMPOSITION
    assert tarefa.attempts == []


def test_e_mutavel() -> None:
    tarefa = _nova_tarefa()

    tarefa.status = TaskStatusEnum.APPROVED

    assert tarefa.status is TaskStatusEnum.APPROVED


# ── Resultado aprovado (B.3) ─────────────────────────────────────────────────


def _relatorio(aprovado: bool) -> VerificationReport:
    if aprovado:
        return VerificationReport(
            decision=VerificationDecisionEnum.APPROVED,
            evaluations=(CriterionEvaluation(criterion_id="c1", met=True, justification="atende"),),
            unmet_criteria_ids=(),
        )
    return VerificationReport(
        decision=VerificationDecisionEnum.REPROVED,
        evaluations=(CriterionEvaluation(criterion_id="c1", met=False, justification="falhou"),),
        unmet_criteria_ids=("c1",),
    )


def _tarefa_com_tentativas(status: TaskStatusEnum, *relatorios: VerificationReport | None) -> Task:
    tarefa = _nova_tarefa()
    tarefa.status = status
    tarefa.attempts = [
        TaskAttempt(number=indice + 1, output=f"saida {indice + 1}", report=relatorio)
        for indice, relatorio in enumerate(relatorios)
    ]
    return tarefa


def test_resultado_aprovado_usa_apenas_a_ultima_tentativa() -> None:
    tarefa = _tarefa_com_tentativas(TaskStatusEnum.APPROVED, _relatorio(False), _relatorio(True))

    resultado = tarefa.approved_result()

    assert resultado == TaskResult(task_id="t1", task_title="titulo", content="saida 2")


def test_tarefa_nao_aprovada_nao_gera_resultado() -> None:
    tarefa = _tarefa_com_tentativas(TaskStatusEnum.FAILED, _relatorio(False))

    with pytest.raises(ValueError, match="não foi aprovada"):
        tarefa.approved_result()


def test_tarefa_sem_tentativas_nao_gera_resultado() -> None:
    tarefa = _tarefa_com_tentativas(TaskStatusEnum.APPROVED)

    with pytest.raises(ValueError, match="relatório aprovado"):
        tarefa.approved_result()


def test_tentativa_sem_relatorio_nao_gera_resultado() -> None:
    tarefa = _tarefa_com_tentativas(TaskStatusEnum.APPROVED, None)

    with pytest.raises(ValueError, match="relatório aprovado"):
        tarefa.approved_result()


def test_tarefa_marcada_aprovada_com_ultimo_relatorio_reprovado_nao_gera_resultado() -> None:
    tarefa = _tarefa_com_tentativas(TaskStatusEnum.APPROVED, _relatorio(True), _relatorio(False))

    with pytest.raises(ValueError, match="relatório aprovado"):
        tarefa.approved_result()
