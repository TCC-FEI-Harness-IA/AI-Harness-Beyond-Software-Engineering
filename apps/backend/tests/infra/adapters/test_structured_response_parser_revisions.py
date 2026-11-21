"""Contrato das referências estruturadas de revisão e dependência (thinking 05).

O parser só aceita referências que a sessão pode honrar: revisão de resultados armazenados que ainda
podem ser revisados, dependência de tarefas anteriores do lote ou de resultados vigentes. Uma recusa
traz o diagnóstico de contrato e não altera nada; a ausência dos campos opcionais mantém o contrato antigo.
"""
import json
import logging
from typing import Any

import pytest

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum as Code
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter

_A2 = ThinkingPhaseEnum.A2_TASK_DECOMPOSITION
_B1 = ThinkingPhaseEnum.B1_TASK_RESOLUTION
_C2 = ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING
_C2_CONTEXTO = ValidationContext(
    max_tasks=5,
    known_task_ids=frozenset({"T1", "T2", "T3", "T4"}),
    reviewable_task_ids=frozenset({"T1", "T2", "T3"}),
    dependable_task_ids=frozenset({"T1", "T2"}),
)
_B1_REVISORA = ValidationContext(review_target_ids=("T3", "T2"))


def _parser() -> StructuredResponseParserAdapter:
    return StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser.revisao"))


def _tarefa(task_id: str, **extra: Any) -> dict[str, Any]:
    return {"id": task_id, "title": "t", "description": "d",
            "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": "c"}], **extra}


def _lote(*tarefas: dict[str, Any]) -> str:
    return json.dumps({"tasks": list(tarefas)})


def _resolucao(**extra: Any) -> str:
    return json.dumps({"task_id": "T5", "result": "r", "conclusion": "c", **extra})


def _veredito(task_id: str, verdict: str = "superseded", justification: str = "erro demonstrado") -> dict:
    return {"task_id": task_id, "verdict": verdict, "justification": justification}


def _recusa(raw: str, phase: ThinkingPhaseEnum, validation: ValidationContext | None) -> PhaseParsingError:
    with pytest.raises(PhaseParsingError) as erro:
        _parser().parse_output(raw_output=raw, phase=phase, validation=validation)
    return erro.value


# ── Planejamento: campos opcionais ausentes e válidos ──────────────────────


@pytest.mark.parametrize("extra", [{}, {"review": None, "depends_on": []}, {"depends_on": None}])
def test_campos_opcionais_ausentes_ou_nulos_mantem_o_contrato_antigo(extra: dict) -> None:
    saida = _parser().parse_output(raw_output=_lote(_tarefa("T5", **extra)), phase=_C2, validation=_C2_CONTEXTO)

    assert saida.parsed["tasks"][0]["id"] == "T5"


def test_c2_aceita_revisao_de_resultado_armazenado_e_dependencias_validas() -> None:
    lote = _lote(
        _tarefa("T5", review={"task_ids": ["T3"], "reason": "T3 contradiz T1 e T2."}, depends_on=["T1"]),
        _tarefa("T6", depends_on=["T5", "T2"]),
        _tarefa("T7", review={"task_ids": ["T2"], "reason": "Cálculo de T2 sem fundamentação."}),
    )

    tarefas = _parser().parse_output(raw_output=lote, phase=_C2, validation=_C2_CONTEXTO).parsed["tasks"]

    assert tarefas[0]["review"] == {"task_ids": ["T3"], "reason": "T3 contradiz T1 e T2."}
    assert tarefas[1]["depends_on"] == ["T5", "T2"]


def test_a2_aceita_dependencia_de_tarefa_anterior_do_mesmo_lote() -> None:
    lote = _lote(_tarefa("T1"), _tarefa("T2", depends_on=["T1"]))

    tarefas = _parser().parse_output(raw_output=lote, phase=_A2, validation=ValidationContext(max_tasks=5)).parsed

    assert tarefas["tasks"][1]["depends_on"] == ["T1"]


def test_planejamento_sem_contexto_ainda_valida_referencias_internas_ao_lote() -> None:
    erro = _recusa(_lote(_tarefa("T1", depends_on=["T2"]), _tarefa("T2")), _A2, None)

    assert erro.diagnostic.problem.code is Code.TASK_REFERENCES


# ── Planejamento: referências recusadas sem mutação ────────────────────────


@pytest.mark.parametrize(("lote", "code", "trecho", "afetados"), [
    (_lote(_tarefa("T5", depends_on=["T9"])), Code.TASK_REFERENCES, "does not exist", ("T9",)),
    (_lote(_tarefa("T5", depends_on=["T5"])), Code.TASK_REFERENCES, "cannot depend on itself", ("T5",)),
    (_lote(_tarefa("T5", depends_on=["T6"]), _tarefa("T6")), Code.TASK_REFERENCES, "later task", ("T6",)),
    (_lote(_tarefa("T5", depends_on=["T3"])), Code.TASK_REFERENCES, "not a current result", ("T3",)),
    (_lote(_tarefa("T5", depends_on=["T1", "T1"])), Code.DUPLICATE_ID, "is repeated", ("T1",)),
    (_lote(_tarefa("T5", depends_on="T1")), Code.SCHEMA_TYPE, "must be a list", ("T5",)),
    (_lote(_tarefa("T5", depends_on=[3])), Code.SCHEMA_TYPE, "non-empty string", ("T5",)),
    (_lote(_tarefa("T5", review="T3")), Code.SCHEMA_TYPE, "must be an object", ("T5",)),
    (_lote(_tarefa("T5", review={"reason": "r"})), Code.MISSING_FIELD, "must be a list", ("T5",)),
    (_lote(_tarefa("T5", review={"task_ids": [], "reason": "r"})), Code.EMPTY_VALUE, "empty list", ("T5",)),
    (_lote(_tarefa("T5", review={"task_ids": ["T3"]})), Code.MISSING_FIELD, "non-empty string", ("T5",)),
    (_lote(_tarefa("T5", review={"task_ids": ["T3", "T3"], "reason": "r"})), Code.DUPLICATE_ID, "repeated", ("T3",)),
    (_lote(_tarefa("T5", review={"task_ids": ["T9"], "reason": "r"})), Code.TASK_REFERENCES, "does not exist", ("T9",)),
    (_lote(_tarefa("T5", review={"task_ids": ["T4"], "reason": "r"})), Code.TASK_REFERENCES, "cannot be reviewed",
     ("T4",)),
    (_lote(_tarefa("T5", review={"task_ids": ["T5"], "reason": "r"})), Code.TASK_REFERENCES, "cannot review itself",
     ("T5",)),
    (_lote(_tarefa("T5"), _tarefa("T6", review={"task_ids": ["T5"], "reason": "r"})), Code.TASK_REFERENCES,
     "not been executed", ("T5",)),
    (_lote(_tarefa("T5", review={"task_ids": ["T3"], "reason": "r"}),
           _tarefa("T6", review={"task_ids": ["T3"], "reason": "r"})), Code.DUPLICATE_ID, "more than one task",
     ("T3",)),
    (_lote(_tarefa("T5", review={"task_ids": ["T1"], "reason": "r"}, depends_on=["T1"])), Code.TASK_REFERENCES,
     "cannot depend on a result it reviews", ("T1",)),
    (_lote(_tarefa("T5", review={"task_ids": ["T3"], "reason": "r"},
                   acceptance_criteria=[{"id": "T5-REV", "description": "c"}])), Code.INVALID_VALUE, "reserved",
     ("T5-REV",)),
], ids=[
    "dependencia_inexistente", "autodependencia", "dependencia_futura_ou_ciclo", "dependencia_nao_vigente",
    "dependencia_repetida", "dependencias_nao_lista", "dependencia_nao_texto", "revisao_nao_objeto",
    "revisao_sem_alvos", "revisao_com_alvos_vazios", "revisao_sem_motivo", "alvo_repetido", "alvo_inexistente",
    "alvo_fora_do_escopo", "autorrevisao", "alvo_ainda_nao_executado", "alvo_revisado_por_duas_tarefas",
    "depende_do_proprio_alvo", "criterio_reservado",
])
def test_c2_recusa_referencias_invalidas_com_diagnostico_de_contrato(
    lote: str, code: Code, trecho: str, afetados: tuple[str, ...],
) -> None:
    erro = _recusa(lote, _C2, _C2_CONTEXTO)

    assert erro.diagnostic.problem.code is code
    assert trecho in erro.reason
    assert erro.diagnostic.problem.affected_ids == afetados


def test_a2_nao_pode_revisar_resultados_porque_nenhum_foi_armazenado() -> None:
    lote = _lote(_tarefa("T1"), _tarefa("T2", review={"task_ids": ["T1"], "reason": "r"}))

    erro = _recusa(lote, _A2, ValidationContext(max_tasks=5))

    assert erro.diagnostic.problem.code is Code.TASK_REFERENCES


# ── B.1: proposta de revisão ────────────────────────────────────────────────


@pytest.mark.parametrize("extra", [{}, {"revision": None}, {"revision": []}])
def test_b1_de_tarefa_normal_aceita_ausencia_de_revisao(extra: dict) -> None:
    saida = _parser().parse_output(raw_output=_resolucao(**extra), phase=_B1, validation=None)

    assert saida.parsed["conclusion"] == "c"


def test_b1_de_tarefa_normal_recusa_proposta_de_revisao() -> None:
    erro = _recusa(_resolucao(revision=[_veredito("T3")]), _B1, ValidationContext())

    assert erro.diagnostic.problem.code is Code.TASK_REFERENCES
    assert "does not review stored results" in erro.reason


def test_b1_de_tarefa_revisora_aceita_um_veredito_por_alvo() -> None:
    raw = _resolucao(revision=[_veredito("T2", "confirmed"), _veredito("T3")])

    saida = _parser().parse_output(raw_output=raw, phase=_B1, validation=_B1_REVISORA)

    assert [v["verdict"] for v in saida.parsed["revision"]] == ["confirmed", "superseded"]


@pytest.mark.parametrize(("extra", "code", "afetados"), [
    ({}, Code.MISSING_FIELD, ()),
    ({"revision": "T3"}, Code.SCHEMA_TYPE, ()),
    ({"revision": []}, Code.EMPTY_VALUE, ()),
    ({"revision": ["T3"]}, Code.SCHEMA_TYPE, ()),
    ({"revision": [{"verdict": "superseded", "justification": "j"}]}, Code.MISSING_FIELD, ()),
    ({"revision": [_veredito("T3", "replaced"), _veredito("T2")]}, Code.INVALID_VALUE, ("T3",)),
    ({"revision": [_veredito("T3", justification=" "), _veredito("T2")]}, Code.EMPTY_VALUE, ("T3",)),
    ({"revision": [_veredito("T3"), _veredito("T3")]}, Code.DUPLICATE_ID, ("T3",)),
    ({"revision": [_veredito("T3"), _veredito("T2"), _veredito("T1")]}, Code.TASK_REFERENCES, ("T1",)),
    ({"revision": [_veredito("T3")]}, Code.TASK_REFERENCES, ("T2",)),
], ids=[
    "ausente", "nao_lista", "vazia", "item_nao_objeto", "sem_alvo", "veredito_desconhecido", "sem_justificativa",
    "alvo_repetido", "alvo_fora_da_revisao", "alvo_sem_veredito",
])
def test_b1_de_tarefa_revisora_recusa_proposta_incompleta_ou_fora_do_escopo(
    extra: dict, code: Code, afetados: tuple[str, ...],
) -> None:
    erro = _recusa(_resolucao(**extra), _B1, _B1_REVISORA)

    assert erro.diagnostic.problem.code is code
    assert erro.diagnostic.problem.affected_ids == afetados
