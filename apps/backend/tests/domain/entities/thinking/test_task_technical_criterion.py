"""Critério técnico obrigatório `<task_id>-TECH` (nova fase de validação — 02).

O harness acrescenta a toda tarefa um critério fixo de validade técnica, separado dos critérios de
autoria do planejador. Os testes provam a composição determinística do conjunto verificado e a
recusa do identificador reservado; não provam que um modelo real julga bem a validade técnica.
"""
import pytest

from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.harness_criteria import (
    REVISION_CRITERION_SUFFIX,
    TECHNICAL_CRITERION_SUFFIX,
    revision_criterion,
    revision_criterion_id,
    technical_criterion,
    technical_criterion_id,
)
from src.domain.entities.thinking.review_request import ReviewRequest
from src.domain.entities.thinking.task import Task
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_AC1 = AcceptanceCriterion(id="T2-AC1", description="Apresenta as etapas pedidas.")
_AC2 = AcceptanceCriterion(id="T2-AC2", description="Explica a conclusão.")


def _tarefa(task_id: str = "T2", **extra: object) -> Task:
    campos: dict = {"acceptance_criteria": (_AC1, _AC2), **extra}
    return Task(id=task_id, title="titulo", description="descricao", **campos)


def _revisora(**extra: object) -> Task:
    return _tarefa(review=ReviewRequest(task_ids=("T1",), reason="T1 contradiz um dado."), **extra)


# ── Definição única ─────────────────────────────────────────────────────────


def test_identificadores_reservados_usam_os_sufixos_fixos() -> None:
    assert TECHNICAL_CRITERION_SUFFIX == "-TECH"
    assert REVISION_CRITERION_SUFFIX == "-REV"
    assert technical_criterion_id("T2") == "T2-TECH"
    assert revision_criterion_id("T7") == "T7-REV"


def test_criterio_tecnico_e_construido_por_uma_unica_definicao_igual_para_toda_tarefa() -> None:
    t2, t9 = technical_criterion("T2"), technical_criterion("T9")

    assert t2 == AcceptanceCriterion(id="T2-TECH", description=t2.description)
    assert t9.id == "T9-TECH"
    assert t2.description == t9.description
    assert _tarefa().technical_criterion == t2
    assert _tarefa(task_id="T9", acceptance_criteria=(AcceptanceCriterion(id="T9-AC1", description="x"),)
                   ).technical_criterion == t9


def test_descricao_tecnica_exige_fundamento_do_objetivo_da_propria_tarefa() -> None:
    descricao = " ".join(technical_criterion("T1").description.split())

    for exigencia in (
        "this task's own objective",
        "data, methods and conditions",
        "premise",
        "hypothesis is not presented as an established fact",
        "referents, units, conditions and temporal stage",
        "method applies",
        "contributions and conditions relevant",
        "actually supports the conclusion",
        "presence of an explanation",
        "calculation, text and conclusion are consistent",
        "approximation, hypothesis or best-fit choice",
    ):
        assert exigencia in descricao, exigencia


def test_descricao_tecnica_nao_cobra_o_que_esta_fora_da_tarefa_nem_exatidao_universal() -> None:
    descricao = " ".join(technical_criterion("T1").description.split())

    for limite in ("other tasks", "final answer format", "external justification", "supported estimate"):
        assert limite in descricao, limite


def test_descricao_tecnica_nao_depende_de_disciplina_formato_de_alternativas_ou_calculo() -> None:
    descricao = technical_criterion("T1").description.lower()

    for termo in ("option", "alternative", "physics", "chemistry", "biology", "letter", "a)", "%"):
        assert termo not in descricao, termo


def test_criterio_de_revisao_continua_com_sua_definicao() -> None:
    criterio = revision_criterion("T4")

    assert criterio.id == "T4-REV"
    assert "confirmed or superseded" in criterio.description
    assert _revisora().revision_criterion == revision_criterion("T2")


# ── Composição do conjunto verificado ───────────────────────────────────────


def test_tarefa_comum_recebe_tech_uma_vez_depois_dos_criterios_planejados() -> None:
    tarefa = _tarefa()

    assert tarefa.verification_criteria() == (_AC1, _AC2, technical_criterion("T2"))
    assert tarefa.harness_criteria() == (technical_criterion("T2"),)
    assert tarefa.acceptance_criteria == (_AC1, _AC2)


def test_tarefa_revisora_recebe_tech_e_rev_uma_vez_cada_e_os_planejados_continuam_identificaveis() -> None:
    tarefa = _revisora()

    assert tarefa.verification_criteria() == (_AC1, _AC2, technical_criterion("T2"), revision_criterion("T2"))
    assert tarefa.harness_criteria() == (technical_criterion("T2"), revision_criterion("T2"))
    assert tarefa.acceptance_criteria == (_AC1, _AC2)


@pytest.mark.parametrize("origem", [ThinkingPhaseEnum.A2_TASK_DECOMPOSITION, ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING])
def test_tarefa_de_a2_ou_c2_tem_o_mesmo_conjunto_efetivo(origem: ThinkingPhaseEnum) -> None:
    assert _tarefa(origin_phase=origem).verification_criteria()[-1] == technical_criterion("T2")


def test_composicao_e_deterministica_e_nao_acumula_em_chamadas_repetidas() -> None:
    tarefa = _revisora()

    primeira = tarefa.verification_criteria()
    segunda = tarefa.verification_criteria()

    assert primeira == segunda
    ids = [criterio.id for criterio in segunda]
    assert ids.count("T2-TECH") == 1 and ids.count("T2-REV") == 1
    assert tarefa.acceptance_criteria == (_AC1, _AC2)


# ── Identificador reservado ─────────────────────────────────────────────────


def test_tarefa_comum_recusa_criterio_planejado_com_o_identificador_tecnico() -> None:
    with pytest.raises(ValueError, match="T2-TECH"):
        _tarefa(acceptance_criteria=(_AC1, AcceptanceCriterion(id="T2-TECH", description="x")))


def test_tarefa_revisora_recusa_criterio_planejado_com_o_identificador_tecnico() -> None:
    with pytest.raises(ValueError, match="T2-TECH"):
        _revisora(acceptance_criteria=(AcceptanceCriterion(id="T2-TECH", description="x"),))


def test_tarefa_comum_sem_dependencias_nem_revisao_tambem_e_conferida() -> None:
    # O retorno antecipado de `review is None` não pode pular a checagem do identificador técnico.
    with pytest.raises(ValueError, match="reservado"):
        Task(id="T1", title="t", description="d",
             acceptance_criteria=(AcceptanceCriterion(id="T1-TECH", description="x"),))


def test_identificador_tecnico_de_outra_tarefa_nao_e_reservado_aqui() -> None:
    tarefa = _tarefa(acceptance_criteria=(AcceptanceCriterion(id="T1-TECH", description="x"),))

    assert [criterio.id for criterio in tarefa.verification_criteria()] == ["T1-TECH", "T2-TECH"]


def test_regras_de_rev_e_dependencias_continuam_valendo() -> None:
    with pytest.raises(ValueError, match="T2-REV"):
        _revisora(acceptance_criteria=(AcceptanceCriterion(id="T2-REV", description="x"),))
    with pytest.raises(ValueError):
        _revisora(depends_on=("T1",))
    with pytest.raises(ValueError):
        _tarefa(depends_on=("T2",))
    # Numa tarefa comum, `-REV` não é reservado (regra anterior preservada).
    assert _tarefa(acceptance_criteria=(AcceptanceCriterion(id="T2-REV", description="x"),)).revision_criterion is None
