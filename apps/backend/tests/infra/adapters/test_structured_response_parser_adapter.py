import json
import logging
from typing import Any

import pytest

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter

_FASE_A1 = ThinkingPhaseEnum.A1_GENERAL_CRITERIA
_FASE_B4 = ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION
_FASE_A3 = ThinkingPhaseEnum.A3_PLANNING_LEARNINGS

_CRITERIOS_VALIDOS: dict[str, Any] = {
    "general_acceptance_criteria": [{"id": "AC1", "description": "responder em portugues"}]
}
_TAREFA_VALIDA: dict[str, Any] = {
    "id": "T1",
    "title": "titulo",
    "description": "descricao",
    "acceptance_criteria": [{"id": "T1-AC1", "description": "criterio"}],
}
_VERIFICACAO_VALIDA: dict[str, Any] = {
    "decision": "approved",
    "criteria_evaluation": [{"criterion_id": "T1-AC1", "met": True, "justification": "atende"}],
    "unmet_criteria_ids": [],
}


def _parser() -> StructuredResponseParserAdapter:
    return StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser"))


def _parse(raw_output: str, phase: ThinkingPhaseEnum = _FASE_A1) -> dict[str, Any]:
    return _parser().parse(raw_output=raw_output, phase=phase)


# ── Extração ─────────────────────────────────────────────────────────────────


def test_extrai_json_puro() -> None:
    assert _parse('{"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}') == {
        "general_acceptance_criteria": [{"id": "AC1", "description": "d"}]
    }


def test_extrai_json_de_cerca_com_linguagem() -> None:
    bruto = '```json\n{"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}\n```'

    assert _parse(bruto)["general_acceptance_criteria"][0]["id"] == "AC1"


def test_extrai_json_de_cerca_sem_linguagem() -> None:
    bruto = '```\n{"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}\n```'

    assert _parse(bruto)["general_acceptance_criteria"][0]["id"] == "AC1"


def test_extrai_json_cercado_por_texto_solto() -> None:
    bruto = (
        "Claro! Segue a resposta:\n"
        '{"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}\n'
        "Espero ter ajudado."
    )

    assert _parse(bruto)["general_acceptance_criteria"][0]["id"] == "AC1"


def test_texto_sem_nenhum_json_e_recusado() -> None:
    with pytest.raises(PhaseParsingError):
        _parse("nao ha nenhum objeto json nesta resposta")


def test_json_sintaticamente_invalido_e_recusado() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('{"general_acceptance_criteria": [')


def test_string_vazia_e_recusada() -> None:
    with pytest.raises(PhaseParsingError):
        _parse("")


def test_json_que_e_lista_e_recusado() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('[{"general_acceptance_criteria": []}]')


def test_erro_de_parsing_carrega_fase_motivo_e_saida_truncada() -> None:
    bruto = "x" * 900

    with pytest.raises(PhaseParsingError) as erro:
        _parse(bruto, phase=_FASE_B4)

    assert erro.value.phase is _FASE_B4
    assert erro.value.reason
    assert len(erro.value.raw_output) < len(bruto)


def test_fase_sem_saida_estruturada_e_recusada() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('{"result": "x"}', phase=ThinkingPhaseEnum.B3_RESULT_STORAGE)


# ── Schema A.1 ───────────────────────────────────────────────────────────────


def _parse_a1(payload: dict[str, Any]) -> dict[str, Any]:
    return _parser().parse(raw_output=json.dumps(payload), phase=_FASE_A1)


def test_a1_valido() -> None:
    assert _parse_a1(_CRITERIOS_VALIDOS) == _CRITERIOS_VALIDOS


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"general_acceptance_criteria": "AC1"},
        {"general_acceptance_criteria": []},
        {"general_acceptance_criteria": ["AC1"]},
        {"general_acceptance_criteria": [{"description": "d"}]},
        {"general_acceptance_criteria": [{"id": "AC1"}]},
        {"general_acceptance_criteria": [{"id": "", "description": "d"}]},
        {"general_acceptance_criteria": [{"id": "AC1", "description": "   "}]},
        {"general_acceptance_criteria": [{"id": 1, "description": "d"}]},
    ],
)
def test_a1_invalido_e_recusado(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parse_a1(payload)


# ── Schema A.2 / C.2 ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "fase",
    [ThinkingPhaseEnum.A2_TASK_DECOMPOSITION, ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING],
)
def test_decomposicao_valida(fase: ThinkingPhaseEnum) -> None:
    payload = {"tasks": [_TAREFA_VALIDA]}

    assert _parser().parse(raw_output=json.dumps(payload), phase=fase) == payload


def test_decomposicao_com_entrada_e_saida_ainda_e_aceita() -> None:
    # Os campos deixaram de ser pedidos, mas um modelo que ainda os envie não tem o lote recusado.
    payload = {"tasks": [{**_TAREFA_VALIDA, "expected_input": "entrada", "expected_output": "saida"}]}

    assert _parser().parse(raw_output=json.dumps(payload), phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"tasks": {}},
        {"tasks": []},
        {"tasks": ["T1"]},
        {"tasks": [{**_TAREFA_VALIDA, "title": ""}]},
        {"tasks": [{k: v for k, v in _TAREFA_VALIDA.items() if k != "description"}]},
        {"tasks": [{**_TAREFA_VALIDA, "acceptance_criteria": []}]},
        {"tasks": [{**_TAREFA_VALIDA, "acceptance_criteria": "criterio"}]},
        {"tasks": [{**_TAREFA_VALIDA, "acceptance_criteria": [{"id": "T1-AC1"}]}]},
    ],
)
def test_decomposicao_invalida_e_recusada(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parser().parse(
            raw_output=json.dumps(payload),
            phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
        )


def _planejar(
    tarefas: list[dict[str, Any]],
    validation: ValidationContext | None = None,
    fase: ThinkingPhaseEnum = ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
) -> dict[str, Any]:
    return _parser().parse(raw_output=json.dumps({"tasks": tarefas}), phase=fase, validation=validation)


def _tarefa_com_id(task_id: str) -> dict[str, Any]:
    return {**_TAREFA_VALIDA, "id": task_id, "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": "c"}]}


def test_a1_com_ids_de_criterio_repetidos_e_recusado() -> None:
    payload = {
        "general_acceptance_criteria": [
            {"id": "AC1", "description": "um"},
            {"id": "AC1", "description": "dois"},
        ]
    }

    with pytest.raises(PhaseParsingError, match="AC1"):
        _parse_a1(payload)


def test_decomposicao_com_ids_de_tarefa_repetidos_no_lote_e_recusada() -> None:
    with pytest.raises(PhaseParsingError, match="T1"):
        _planejar([_tarefa_com_id("T1"), _tarefa_com_id("T1")])


def test_decomposicao_com_ids_de_criterio_repetidos_na_tarefa_e_recusada() -> None:
    tarefa = {
        **_TAREFA_VALIDA,
        "acceptance_criteria": [{"id": "T1-AC1", "description": "a"}, {"id": "T1-AC1", "description": "b"}],
    }

    with pytest.raises(PhaseParsingError, match="T1-AC1"):
        _planejar([tarefa])


def test_decomposicao_que_reusa_id_de_tarefa_ja_criada_e_recusada() -> None:
    contexto = ValidationContext(known_task_ids=frozenset({"T1"}))

    with pytest.raises(PhaseParsingError, match="T1"):
        _planejar([_tarefa_com_id("T1")], validation=contexto, fase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING)


def test_decomposicao_dentro_do_teto_e_aceita() -> None:
    contexto = ValidationContext(max_tasks=2, known_task_ids=frozenset({"T1"}))

    resultado = _planejar([_tarefa_com_id("T2"), _tarefa_com_id("T3")], validation=contexto)

    assert [tarefa["id"] for tarefa in resultado["tasks"]] == ["T2", "T3"]


def test_decomposicao_acima_do_teto_e_recusada_apontando_o_limite_de_tarefas() -> None:
    contexto = ValidationContext(max_tasks=1)

    with pytest.raises(PhaseParsingError, match="no máximo 1") as erro:
        _planejar([_tarefa_com_id("T1"), _tarefa_com_id("T2")], validation=contexto)

    assert erro.value.limit is BudgetLimitEnum.TASKS_PER_SESSION


def test_recusas_estruturais_nao_apontam_limite() -> None:
    with pytest.raises(PhaseParsingError) as erro:
        _planejar([])

    assert erro.value.limit is None


# ── Schema B.1 ───────────────────────────────────────────────────────────────


def test_b1_valido() -> None:
    payload = {"task_id": "T1", "result": "markdown da resolucao"}

    assert _parser().parse(
        raw_output=json.dumps(payload),
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
    ) == payload


@pytest.mark.parametrize("payload", [{}, {"result": ""}, {"result": "   "}, {"result": ["x"]}])
def test_b1_invalido_e_recusado(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parser().parse(
            raw_output=json.dumps(payload),
            phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        )


# ── Schema B.2 / C.1 ─────────────────────────────────────────────────────────

_FASES_DE_VERIFICACAO = [ThinkingPhaseEnum.B2_TASK_VERIFICATION, ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION]


def _esperando(*ids: str) -> ValidationContext:
    return ValidationContext(expected_criteria_ids=tuple(ids))


def _avaliacao(criterion_id: str, met: bool = True) -> dict[str, Any]:
    return {"criterion_id": criterion_id, "met": met, "justification": "porque sim"}


def _relatorio(
    *avaliacoes: dict[str, Any], decision: str | None = None, unmet: list[str] | None = None
) -> dict[str, Any]:
    falhas = [a["criterion_id"] for a in avaliacoes if not a["met"]]
    return {
        "decision": decision or ("reproved" if falhas else "approved"),
        "criteria_evaluation": list(avaliacoes),
        "unmet_criteria_ids": falhas if unmet is None else unmet,
    }


def _verificar(
    payload: dict[str, Any],
    esperados: tuple[str, ...] = ("T1-AC1",),
    fase: ThinkingPhaseEnum = ThinkingPhaseEnum.B2_TASK_VERIFICATION,
) -> dict[str, Any]:
    return _parser().parse(raw_output=json.dumps(payload), phase=fase, validation=_esperando(*esperados))


@pytest.mark.parametrize("fase", _FASES_DE_VERIFICACAO)
def test_verificacao_valida(fase: ThinkingPhaseEnum) -> None:
    assert _verificar(_VERIFICACAO_VALIDA, fase=fase) == _VERIFICACAO_VALIDA


def test_verificacao_reprovada_valida() -> None:
    payload = _relatorio(_avaliacao("T1-AC1", met=False))

    assert _verificar(payload) == payload


def test_verificacao_aceita_avaliacoes_em_ordem_diferente_da_dos_criterios() -> None:
    payload = _relatorio(_avaliacao("AC2"), _avaliacao("AC1"), _avaliacao("AC3", met=False))

    assert _verificar(payload, esperados=("AC1", "AC2", "AC3")) == payload


@pytest.mark.parametrize("fase", _FASES_DE_VERIFICACAO)
def test_verificacao_exige_o_contexto_de_validacao(fase: ThinkingPhaseEnum) -> None:
    with pytest.raises(ValueError, match="contexto de validação"):
        _parser().parse(raw_output=json.dumps(_VERIFICACAO_VALIDA), phase=fase)


@pytest.mark.parametrize("fase", _FASES_DE_VERIFICACAO)
def test_verificacao_exige_os_criterios_esperados_no_contexto(fase: ThinkingPhaseEnum) -> None:
    with pytest.raises(ValueError, match="contexto de validação"):
        _parser().parse(raw_output=json.dumps(_VERIFICACAO_VALIDA), phase=fase, validation=ValidationContext())


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {**_VERIFICACAO_VALIDA, "decision": "talvez"},
        {**_VERIFICACAO_VALIDA, "criteria_evaluation": "tudo certo"},
        {**_VERIFICACAO_VALIDA, "criteria_evaluation": ["T1-AC1"]},
        {**_VERIFICACAO_VALIDA, "criteria_evaluation": [{"met": True, "justification": "j"}]},
        {
            **_VERIFICACAO_VALIDA,
            "criteria_evaluation": [{"criterion_id": "T1-AC1", "met": "sim", "justification": "j"}],
        },
        {**_VERIFICACAO_VALIDA, "criteria_evaluation": [{"criterion_id": "T1-AC1", "met": True}]},
        {**_VERIFICACAO_VALIDA, "unmet_criteria_ids": "T1-AC1"},
        {**_VERIFICACAO_VALIDA, "decision": "reproved", "unmet_criteria_ids": [1]},
    ],
)
def test_verificacao_invalida_e_recusada(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _verificar(payload)


def test_relatorio_sem_avaliacoes_e_recusado_mesmo_aprovado() -> None:
    payload = {"decision": "approved", "criteria_evaluation": [], "unmet_criteria_ids": []}

    with pytest.raises(PhaseParsingError, match="T1-AC1"):
        _verificar(payload)


def test_avaliacao_faltante_e_recusada() -> None:
    payload = _relatorio(_avaliacao("AC1"))

    with pytest.raises(PhaseParsingError, match="AC2"):
        _verificar(payload, esperados=("AC1", "AC2"))


def test_avaliacao_repetida_e_recusada() -> None:
    payload = _relatorio(_avaliacao("AC1"), _avaliacao("AC1"))

    with pytest.raises(PhaseParsingError, match="mais de uma vez"):
        _verificar(payload, esperados=("AC1",))


def test_avaliacao_de_criterio_desconhecido_e_recusada() -> None:
    payload = _relatorio(_avaliacao("AC1"), _avaliacao("INEXISTENTE"))

    with pytest.raises(PhaseParsingError, match="INEXISTENTE"):
        _verificar(payload, esperados=("AC1",))


def test_aprovado_com_avaliacao_negativa_e_recusado() -> None:
    payload = _relatorio(_avaliacao("T1-AC1", met=False), decision="approved", unmet=[])

    with pytest.raises(PhaseParsingError, match="incoerente"):
        _verificar(payload)


def test_aprovado_com_pendencias_e_incoerente() -> None:
    payload = {**_VERIFICACAO_VALIDA, "unmet_criteria_ids": ["T1-AC1"]}

    with pytest.raises(PhaseParsingError, match="incoerente"):
        _verificar(payload)


def test_reprovado_sem_pendencias_e_incoerente() -> None:
    payload = {**_VERIFICACAO_VALIDA, "decision": "reproved"}

    with pytest.raises(PhaseParsingError, match="incoerente"):
        _verificar(payload, fase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION)


def test_reprovado_com_todas_as_avaliacoes_positivas_e_recusado() -> None:
    payload = _relatorio(_avaliacao("T1-AC1"), decision="reproved", unmet=["T1-AC1"])

    with pytest.raises(PhaseParsingError, match="pendências"):
        _verificar(payload)


def test_pendencia_desconhecida_e_recusada() -> None:
    payload = _relatorio(_avaliacao("AC1", met=False), decision="reproved", unmet=["AC1", "DESCONHECIDO"])

    with pytest.raises(PhaseParsingError, match="pendências"):
        _verificar(payload, esperados=("AC1",))


def test_pendencia_repetida_e_recusada() -> None:
    payload = _relatorio(_avaliacao("AC1", met=False), decision="reproved", unmet=["AC1", "AC1"])

    with pytest.raises(PhaseParsingError, match="repet"):
        _verificar(payload, esperados=("AC1",))


def test_pendencias_que_nao_correspondem_as_avaliacoes_negativas_sao_recusadas() -> None:
    payload = _relatorio(_avaliacao("AC1"), _avaliacao("AC2", met=False), decision="reproved", unmet=["AC1"])

    with pytest.raises(PhaseParsingError, match="pendências"):
        _verificar(payload, esperados=("AC1", "AC2"))


# ── Schema B.4 ───────────────────────────────────────────────────────────────


def test_b4_valido() -> None:
    payload = {"learnings": ["fato seco 1", "fato seco 2"]}

    assert _parser().parse(raw_output=json.dumps(payload), phase=_FASE_B4) == payload


def test_b4_aceita_lista_de_aprendizados_vazia() -> None:
    payload: dict[str, Any] = {"learnings": []}

    assert _parser().parse(raw_output=json.dumps(payload), phase=_FASE_B4) == payload


@pytest.mark.parametrize("payload", [{}, {"learnings": "fato"}, {"learnings": [{"content": "fato"}]}])
def test_b4_invalido_e_recusado(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parser().parse(raw_output=json.dumps(payload), phase=_FASE_B4)


# ── Schema A.3 ───────────────────────────────────────────────────────────────


def test_a3_valido() -> None:
    payload = {"learnings": ["Alternativas: A) 2; B) 4", "Velocidade: 20 m/s"]}

    assert _parser().parse(raw_output=json.dumps(payload), phase=_FASE_A3) == payload


def test_a3_aceita_lista_de_aprendizados_vazia() -> None:
    payload: dict[str, Any] = {"learnings": []}

    assert _parser().parse(raw_output=json.dumps(payload), phase=_FASE_A3) == payload


@pytest.mark.parametrize("payload", [{}, {"learnings": "fato"}, {"learnings": [{"content": "fato"}]}])
def test_a3_invalido_e_recusado(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError) as erro:
        _parser().parse(raw_output=json.dumps(payload), phase=_FASE_A3)

    assert erro.value.phase is _FASE_A3


# ── Schema C.3 ───────────────────────────────────────────────────────────────


def test_c3_valido() -> None:
    payload = {"final_answer": "D) Nenhuma das anteriores"}

    assert _parser().parse(
        raw_output=json.dumps(payload),
        phase=ThinkingPhaseEnum.C3_FINAL_ANSWER,
    ) == payload


@pytest.mark.parametrize("payload", [{}, {"final_answer": ""}, {"final_answer": "  "}, {"final_answer": 42}])
def test_c3_invalido_e_recusado(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parser().parse(
            raw_output=json.dumps(payload),
            phase=ThinkingPhaseEnum.C3_FINAL_ANSWER,
        )


# ── Reparo de fechamentos ausentes ───────────────────────────────────────────
#
# Alguns modelos encerram a resposta (`finish_reason == "stop"`) um ou dois caracteres antes do
# fim, deixando de fechar as últimas chaves e colchetes de um JSON que, no resto, está completo.
# O parser acrescenta só esses fechamentos; a validação de schema da fase continua estrita.

_PAYLOAD_VALIDO_POR_FASE: dict[ThinkingPhaseEnum, dict[str, Any]] = {
    ThinkingPhaseEnum.A1_GENERAL_CRITERIA: _CRITERIOS_VALIDOS,
    ThinkingPhaseEnum.A2_TASK_DECOMPOSITION: {"tasks": [_TAREFA_VALIDA]},
    ThinkingPhaseEnum.A3_PLANNING_LEARNINGS: {"learnings": ["Velocidade: 20 m/s"]},
    ThinkingPhaseEnum.B1_TASK_RESOLUTION: {"task_id": "T1", "result": "markdown da resolucao"},
    ThinkingPhaseEnum.B2_TASK_VERIFICATION: _VERIFICACAO_VALIDA,
    ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION: {"learnings": ["fato seco"]},
    ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION: _VERIFICACAO_VALIDA,
    ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING: {"tasks": [_TAREFA_VALIDA]},
    ThinkingPhaseEnum.C3_FINAL_ANSWER: {"final_answer": "D) 450 N"},
}
_FASES_SEM_SAIDA_ESTRUTURADA = {ThinkingPhaseEnum.B3_RESULT_STORAGE, ThinkingPhaseEnum.DIRECT_INFERENCE}
_FASES_COM_SAIDA_ESTRUTURADA = [fase for fase in ThinkingPhaseEnum if fase not in _FASES_SEM_SAIDA_ESTRUTURADA]
_VALIDACAO_POR_FASE: dict[ThinkingPhaseEnum, ValidationContext] = {
    ThinkingPhaseEnum.B2_TASK_VERIFICATION: _esperando("T1-AC1"),
    ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION: _esperando("T1-AC1"),
}


def _sem_fechamentos_finais(payload: dict[str, Any]) -> str:
    """Serializa o payload e remove todas as chaves e colchetes do fim, como o modelo faz."""
    return json.dumps(payload, ensure_ascii=False).rstrip("]}")


def _parse_a1_com_motivo(raw_output: str, finish_reason: str | None) -> dict[str, Any]:
    return _parser().parse(raw_output=raw_output, phase=_FASE_A1, finish_reason=finish_reason)


def test_toda_fase_que_espera_json_tem_payload_de_reparo_coberto() -> None:
    # Uma fase nova que produza JSON precisa entrar neste mapa — e, com isso, nos testes de reparo.
    assert set(_PAYLOAD_VALIDO_POR_FASE) == set(_FASES_COM_SAIDA_ESTRUTURADA)


@pytest.mark.parametrize("fase", _FASES_COM_SAIDA_ESTRUTURADA)
def test_toda_fase_que_espera_json_repara_os_fechamentos_ausentes(fase: ThinkingPhaseEnum) -> None:
    payload = _PAYLOAD_VALIDO_POR_FASE[fase]

    parsed = _parser().parse(
        raw_output=_sem_fechamentos_finais(payload),
        phase=fase,
        validation=_VALIDACAO_POR_FASE.get(fase),
        finish_reason="stop",
    )

    assert parsed == payload


@pytest.mark.parametrize("cortados", [1, 2, 3])
def test_repara_qualquer_quantidade_de_fechamentos_ausentes_no_fim(cortados: int) -> None:
    payload = {"tasks": [_TAREFA_VALIDA]}
    bruto = json.dumps(payload)[:-cortados]

    assert _parser().parse(raw_output=bruto, phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION) == payload


def test_repara_a_saida_real_da_fase_a2_que_terminou_sem_fechar_a_lista_e_o_objeto() -> None:
    # Reprodução da sessão sess_5afb86331ce34ceda424347b21b9f3a6: o JSON termina em `}]}` e falta `]}`.
    payload = {
        "tasks": [
            {**_TAREFA_VALIDA, "id": "T1", "acceptance_criteria": [{"id": "T1-AC1", "description": "720 N"}]},
            {**_TAREFA_VALIDA, "id": "T2", "acceptance_criteria": [{"id": "T2-AC1", "description": "900 N"}]},
        ]
    }
    bruto = json.dumps(payload, ensure_ascii=False)[:-2]
    assert bruto.endswith('"}]}')

    assert _parser().parse(raw_output=bruto, phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION) == payload


def test_repara_json_precedido_por_texto_solto() -> None:
    bruto = "Segue a resposta:\n" + _sem_fechamentos_finais(_CRITERIOS_VALIDOS) + "\n"

    assert _parse(bruto) == _CRITERIOS_VALIDOS


def test_repara_json_dentro_de_cerca_de_codigo() -> None:
    bruto = "```json\n" + _sem_fechamentos_finais(_CRITERIOS_VALIDOS) + "\n```"

    assert _parse(bruto) == _CRITERIOS_VALIDOS


def test_repara_json_dentro_de_cerca_que_nao_foi_fechada() -> None:
    bruto = "```json\n" + _sem_fechamentos_finais(_CRITERIOS_VALIDOS)

    assert _parse(bruto) == _CRITERIOS_VALIDOS


def test_chaves_colchetes_e_aspas_escapadas_dentro_de_strings_nao_contam_como_estrutura() -> None:
    payload = {
        "task_id": "T1",
        "result": 'Use $\\frac{a}{b}$, o vetor [1, 2} e a "citação \\" com aspas" {[',
    }
    bruto = json.dumps(payload, ensure_ascii=False)[:-1]

    assert _parser().parse(raw_output=bruto, phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION) == payload


def test_motivo_de_termino_desconhecido_ainda_permite_o_reparo() -> None:
    assert _parse_a1_com_motivo(_sem_fechamentos_finais(_CRITERIOS_VALIDOS), finish_reason=None) == _CRITERIOS_VALIDOS


def test_saida_cortada_pelo_limite_de_tokens_nao_e_reparada() -> None:
    # Com `finish_reason == "length"` o que falta pode ser conteúdo — tarefas ou critérios inteiros —,
    # e não só fechamentos: completar a estrutura aceitaria um lote silenciosamente incompleto.
    with pytest.raises(PhaseParsingError):
        _parse_a1_com_motivo(_sem_fechamentos_finais(_CRITERIOS_VALIDOS), finish_reason="length")


def test_saida_cortada_pelo_limite_de_tokens_ainda_aceita_json_completo() -> None:
    assert _parse_a1_com_motivo(json.dumps(_CRITERIOS_VALIDOS), finish_reason="length") == _CRITERIOS_VALIDOS


def test_saida_que_termina_dentro_de_uma_string_nao_e_reparada() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('{"general_acceptance_criteria": [{"id": "AC1", "description": "responder em')


def test_saida_que_termina_em_virgula_pendente_nao_e_reparada() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('{"general_acceptance_criteria": [{"id": "AC1", "description": "d"},')


def test_fechamento_trocado_nao_e_reparado() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('{"general_acceptance_criteria": [{"id": "AC1", "description": "d"}}')


def test_fechamento_a_mais_nao_e_reparado() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('{"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}}')


def test_texto_depois_do_json_incompleto_nao_e_reparado() -> None:
    with pytest.raises(PhaseParsingError):
        _parse(_sem_fechamentos_finais(_CRITERIOS_VALIDOS) + "\nEspero ter ajudado.")


def test_json_reparado_continua_sujeito_ao_schema_da_fase() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('{"general_acceptance_criteria": [{"id": "AC1"')


def test_reparo_e_registrado_como_aviso_no_log(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="teste.parser"):
        _parse(json.dumps(_CRITERIOS_VALIDOS)[:-2])

    avisos = [registro.getMessage() for registro in caplog.records if registro.levelno == logging.WARNING]
    assert len(avisos) == 1
    assert "A1" in avisos[0]
    assert "]}" in avisos[0]


def test_json_completo_nao_gera_aviso_de_reparo(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="teste.parser"):
        _parse(json.dumps(_CRITERIOS_VALIDOS))

    assert not [registro for registro in caplog.records if registro.levelno == logging.WARNING]
