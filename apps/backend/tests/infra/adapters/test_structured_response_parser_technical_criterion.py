"""Contrato do critério técnico reservado `<task_id>-TECH` no parser (nova fase de validação — 02).

O parser recusa o identificador reservado quando o planejador o emite (A.2/C.2) e confere a cobertura
e a coerência dos relatórios de B.2 contra os critérios efetivos que a chamada informou. Ele não decide
se a justificativa é verdadeira, não corrige vereditos e não fabrica avaliações: `TECH: false` num
relatório coerente é uma reprovação semântica válida.
"""
import json
import logging
from typing import Any

import pytest

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum as Code
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter

_A2 = ThinkingPhaseEnum.A2_TASK_DECOMPOSITION
_B2 = ThinkingPhaseEnum.B2_TASK_VERIFICATION
_C2 = ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING
_C2_CONTEXTO = ValidationContext(
    max_tasks=5,
    known_task_ids=frozenset({"T1", "T2", "T3"}),
    reviewable_task_ids=frozenset({"T1", "T2", "T3"}),
    dependable_task_ids=frozenset({"T1", "T2", "T3"}),
)
_ESPERADOS = ("T2-AC1", "T2-TECH")
_ESPERADOS_REVISORA = ("T4-AC1", "T4-TECH", "T4-REV")


def _parser() -> StructuredResponseParserAdapter:
    return StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser.tech"))


def _tarefa(task_id: str, *criterios: str, **extra: Any) -> dict[str, Any]:
    ids = criterios or (f"{task_id}-AC1",)
    return {"id": task_id, "title": "t", "description": "d",
            "acceptance_criteria": [{"id": criterio, "description": "c"} for criterio in ids], **extra}


def _lote(*tarefas: dict[str, Any]) -> str:
    return json.dumps({"tasks": list(tarefas)})


def _avaliacao(criterion_id: str, met: bool, justification: str = "conferido") -> dict[str, Any]:
    return {"criterion_id": criterion_id, "met": met, "justification": justification}


def _relatorio(avaliacoes: list[dict[str, Any]], unmet: list[str] | None = None, decision: str | None = None) -> str:
    falhas = [avaliacao["criterion_id"] for avaliacao in avaliacoes if not avaliacao["met"]]
    return json.dumps({
        "criteria_evaluation": avaliacoes,
        "unmet_criteria_ids": falhas if unmet is None else unmet,
        "decision": decision or ("reproved" if falhas else "approved"),
    })


def _verificar(raw: str, esperados: tuple[str, ...] = _ESPERADOS) -> dict[str, Any]:
    return _parser().parse_output(
        raw_output=raw, phase=_B2, validation=ValidationContext(expected_criteria_ids=esperados)
    ).parsed


def _recusa(raw: str, phase: ThinkingPhaseEnum, validation: ValidationContext | None) -> PhaseParsingError:
    with pytest.raises(PhaseParsingError) as erro:
        _parser().parse_output(raw_output=raw, phase=phase, validation=validation)
    return erro.value


# ── Planejamento: identificador reservado ──────────────────────────────────


@pytest.mark.parametrize(("phase", "validation", "lote"), [
    (_A2, ValidationContext(max_tasks=5), _lote(_tarefa("T1", "T1-AC1", "T1-TECH"))),
    (_A2, ValidationContext(max_tasks=5), _lote(_tarefa("T1"), _tarefa("T2", "T2-TECH"))),
    (_A2, None, _lote(_tarefa("T1", "T1-TECH"))),
    (_C2, _C2_CONTEXTO, _lote(_tarefa("T4", "T4-TECH"))),
    (_C2, _C2_CONTEXTO, _lote(_tarefa("T4", "T4-AC1", "T4-TECH", depends_on=["T1"]))),
    (_C2, _C2_CONTEXTO, _lote(_tarefa("T4", "T4-TECH", review={"task_ids": ["T3"], "reason": "r"}))),
], ids=["a2_comum", "a2_segunda_tarefa", "a2_sem_contexto", "c2_comum", "c2_com_dependencia", "c2_revisora"])
def test_planejador_nao_pode_emitir_o_identificador_tecnico_reservado(
    phase: ThinkingPhaseEnum, validation: ValidationContext | None, lote: str,
) -> None:
    erro = _recusa(lote, phase, validation)

    assert erro.diagnostic.problem.code is Code.INVALID_VALUE
    assert erro.diagnostic.contract_status is OutputContractStatusEnum.INVALID
    assert "reserved" in erro.reason and "technical" in erro.reason
    assert len(erro.diagnostic.problem.affected_ids) == 1
    assert erro.diagnostic.problem.affected_ids[0].endswith("-TECH")
    assert erro.diagnostic.problem.field == "tasks[].acceptance_criteria[].id"


def test_recusa_nao_remove_o_criterio_silenciosamente() -> None:
    raw = _lote(_tarefa("T1", "T1-AC1", "T1-TECH"))

    erro = _recusa(raw, _A2, ValidationContext(max_tasks=5))

    assert erro.raw_output == raw


def test_identificador_tech_de_outra_tarefa_nao_colide_e_rev_comum_segue_a_regra_anterior() -> None:
    tarefas = _parser().parse_output(
        raw_output=_lote(_tarefa("T1", "T2-TECH"), _tarefa("T2", "T2-AC1", "T2-REV")),
        phase=_A2, validation=ValidationContext(max_tasks=5),
    ).parsed["tasks"]

    assert [c["id"] for c in tarefas[0]["acceptance_criteria"]] == ["T2-TECH"]
    assert [c["id"] for c in tarefas[1]["acceptance_criteria"]] == ["T2-AC1", "T2-REV"]


def test_lote_sem_tech_e_aceito_sem_que_o_parser_o_acrescente() -> None:
    tarefas = _parser().parse_output(
        raw_output=_lote(_tarefa("T1")), phase=_A2, validation=ValidationContext(max_tasks=5)
    ).parsed["tasks"]

    assert tarefas[0]["acceptance_criteria"] == [{"id": "T1-AC1", "description": "c"}]


# ── B.2: relatórios coerentes nos dois sentidos ────────────────────────────


def test_falha_tecnica_isolada_e_reprovacao_semantica_valida() -> None:
    raw = _relatorio([
        _avaliacao("T2-AC1", True, "The requested calculation steps are present."),
        _avaliacao("T2-TECH", False, "The rate is applied outside its stated interval."),
    ])

    parsed = _verificar(raw)

    assert parsed["decision"] == "reproved"
    assert parsed["unmet_criteria_ids"] == ["T2-TECH"]
    assert [a["met"] for a in parsed["criteria_evaluation"]] == [True, False]


def test_aprovacao_completa_com_tech_e_aceita() -> None:
    parsed = _verificar(_relatorio([_avaliacao("T2-AC1", True), _avaliacao("T2-TECH", True)]))

    assert parsed["decision"] == "approved" and parsed["unmet_criteria_ids"] == []


@pytest.mark.parametrize(("tech", "rev"), [(True, False), (False, True), (False, False), (True, True)])
def test_tech_e_rev_sao_avaliados_de_forma_independente(tech: bool, rev: bool) -> None:
    raw = _relatorio([_avaliacao("T4-AC1", True), _avaliacao("T4-TECH", tech), _avaliacao("T4-REV", rev)])

    parsed = _verificar(raw, esperados=_ESPERADOS_REVISORA)

    assert parsed["decision"] == ("approved" if tech and rev else "reproved")


# ── B.2: relatórios inconsistentes são defeitos de contrato ────────────────


@pytest.mark.parametrize(("raw", "code", "trecho", "afetados"), [
    (_relatorio([_avaliacao("T2-AC1", True)]), Code.CRITERIA_IDS, "missing", ("T2-TECH",)),
    (_relatorio([_avaliacao("T2-AC1", True), _avaliacao("T2-TECH", True), _avaliacao("T2-TECH", True)]),
     Code.CRITERIA_IDS, "more than once", ("T2-TECH",)),
    (_relatorio([_avaliacao("T2-AC1", True), _avaliacao("T2-TECH", True), _avaliacao("T2-AC9", True)]),
     Code.CRITERIA_IDS, "unknown", ("T2-AC9",)),
    (_relatorio([_avaliacao("T2-AC1", True), _avaliacao("T1-TECH", True)]), Code.CRITERIA_IDS, "unknown",
     ("T1-TECH",)),
    (_relatorio([_avaliacao("T2-AC1", True), _avaliacao("T2-TECH", False)], unmet=[], decision="approved"),
     Code.DECISION_CONSISTENCY, "inconsistent", ("T2-TECH",)),
    (_relatorio([_avaliacao("T2-AC1", True), _avaliacao("T2-TECH", False)], unmet=["T2-TECH"],
                decision="approved"), Code.DECISION_CONSISTENCY, "inconsistent", ("T2-TECH",)),
    (_relatorio([_avaliacao("T2-AC1", True), _avaliacao("T2-TECH", True)], unmet=[], decision="reproved"),
     Code.DECISION_CONSISTENCY, "at least one pending", ()),
    (_relatorio([_avaliacao("T2-AC1", False), _avaliacao("T2-TECH", False)], unmet=["T2-AC1"]),
     Code.DECISION_CONSISTENCY, "exactly the criteria", ("T2-TECH",)),
    (_relatorio([_avaliacao("T2-AC1", True), _avaliacao("T2-TECH", False)], unmet=["T2-AC1"]),
     Code.DECISION_CONSISTENCY, "exactly the criteria", ("T2-AC1", "T2-TECH")),
], ids=["tech_ausente", "tech_repetido", "id_desconhecido", "tech_de_outra_tarefa", "aprovado_com_tech_falso",
        "aprovado_com_tech_pendente", "reprovado_sem_pendencias", "pendencias_sem_tech", "pendencias_trocadas"])
def test_relatorio_inconsistente_com_tech_e_recusado_sem_mudar_vereditos(
    raw: str, code: Code, trecho: str, afetados: tuple[str, ...],
) -> None:
    erro = _recusa(raw, _B2, ValidationContext(expected_criteria_ids=_ESPERADOS))

    assert erro.diagnostic.problem.code is code
    assert trecho in erro.reason
    assert erro.diagnostic.problem.affected_ids == afetados
    assert erro.raw_output == raw


def test_relatorio_antigo_sem_tech_continua_valido_quando_a_chamada_nao_espera_tech() -> None:
    # A cobertura vale para os critérios que a chamada informou: o parser não exige um critério que
    # não existia (sessões antigas não são revalidadas; elas nem passam pelo parser na leitura).
    parsed = _verificar(_relatorio([_avaliacao("T2-AC1", True)]), esperados=("T2-AC1",))

    assert parsed["decision"] == "approved"
