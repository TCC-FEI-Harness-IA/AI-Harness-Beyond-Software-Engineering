"""Nova fase de validação — 02: validade técnica obrigatória das tarefas (`<task_id>-TECH`).

B.1 e B.2 recebem o mesmo conjunto efetivo de critérios — os planejados, o critério técnico fixo
`<task_id>-TECH` e, numa revisora, `<task_id>-REV` —, e o parser exige exatamente esses identificadores.
B.2 recebe ainda a tarefa (identificação, título e descrição) numa área própria. Templates, parser, fila,
memória, livro de resultados, recorder e guardião são reais; as saídas do modelo são roteirizadas. Os
testes provam o protocolo — transporte, isolamento, contratos, tentativas e estado —, não que um modelo real
detectará uma premissa inventada ou aceitará uma aproximação legítima.
"""
import json
import logging
import re
from pathlib import Path
from typing import Any

import pytest

from src.domain.entities.resilience.cost_budget import CostBudget
from src.domain.entities.thinking.harness_criteria import technical_criterion
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.result_status_enum import ResultStatusEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum as Sub
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.domain.errors.execution_interrupted_error import ExecutionInterruptedError
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import (
    anotacoes_do_enunciado,
    aprendizados,
    aprovado,
    criterios,
    global_aprovado,
    global_reprovado,
    plano_aprovado,
    plano_reprovado,
    problema_do_plano,
    reprovado_tecnico,
    resposta_final,
)

_TEMPERATURA = 0.3
_PERGUNTA = "Misturam-se 200 g de agua a 80 C com 100 g de agua a 20 C. Qual a temperatura de equilibrio?"
_NOTA = "Dados: 200 g a 80 C e 100 g a 20 C; calor especifico da agua 1 cal/(g C)."
_DESCRICAO = "DESCRICAO-T1: determine a temperatura de equilibrio pelo balanco de calor, com os dados do enunciado."
_R1 = "RESULTADO-1: com o recipiente de cobre de 50 cal/C, T = 54,3 C."
_R2 = "RESULTADO-2: sem perdas, 200(80 - T) = 100(T - 20), logo T = 60 C."
_FEEDBACK = ("FEEDBACK-TECH: a capacidade termica do recipiente nao foi fornecida e muda o balanco; "
             "investigar o balanco so com os dados dados ou justificar a hipotese.")
_FATO = "A temperatura de equilibrio da mistura sem perdas e 60 C: 200(80 - T) = 100(T - 20)."
_MATRIX = json.loads((Path(__file__).parents[2] / "fixtures/technical_validation_v1.json").read_text())


# ── Roteiros ───────────────────────────────────────────────────────────────


def _json(**value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _tarefa(task_id: str, descricao: str = _DESCRICAO, criterios_: tuple[str, ...] = ("Apresenta o balanco.",),
            titulo: str | None = None, **extra: object) -> dict[str, Any]:
    return {"id": task_id, "title": titulo or f"Balanco {task_id}", "description": descricao,
            "acceptance_criteria": [{"id": f"{task_id}-AC{i + 1}", "description": c} for i, c in enumerate(criterios_)],
            **extra}


def _plano(*tarefas: dict[str, Any]) -> str:
    return _json(tasks=list(tarefas))


def _resolucao(task_id: str, texto: str, *vereditos: tuple[str, str, str]) -> str:
    extra = {"revision": [{"task_id": alvo, "verdict": verdict, "justification": justificativa}
                          for alvo, verdict, justificativa in vereditos]} if vereditos else {}
    return _json(task_id=task_id, result=texto, conclusion=texto, **extra)


def _relatorio(*avaliacoes: tuple[str, bool, str], unmet: list[str] | None = None,
               decision: str | None = None) -> str:
    falhas = [criterion_id for criterion_id, met, _ in avaliacoes if not met]
    return _json(
        criteria_evaluation=[{"criterion_id": criterion_id, "met": met, "justification": justificativa}
                             for criterion_id, met, justificativa in avaliacoes],
        unmet_criteria_ids=falhas if unmet is None else unmet,
        decision=decision or ("reproved" if falhas else "approved"),
    )


def _inicio(*tarefas: dict[str, Any]) -> list[str]:
    return [criterios(), _plano(*(tarefas or (_tarefa("T1"),))), plano_aprovado(), anotacoes_do_enunciado(_NOTA)]


def _final() -> list[str]:
    return [global_aprovado(), resposta_final("60 C")]


def _cenario(responses: list[str], **kwargs: Any) -> RalphScenario:
    settings = kwargs.pop("settings", None) or FakeSettings()
    provider = FilePromptTemplateProvider(settings=settings, logger=logging.getLogger("teste.tech.templates"))
    return RalphScenario(responses=responses, settings=settings, template_provider=provider,
                         temperature=_TEMPERATURA, **kwargs)


def _orcamento(**overrides: int) -> CostBudget:
    limites = {"max_task_attempts": 5, "max_planning_attempts": 5, "max_additional_planning_rounds": 2,
               "max_tasks_per_session": 12, "max_llm_calls_per_session": 200, "session_token_budget": 1_000_000,
               "final_answer_token_reserve": 1_000, "session_timeout_seconds": 600}
    return CostBudget(**(limites | overrides))


def _espiar_parser(cenario: RalphScenario) -> list[tuple[Phase, ValidationContext | None]]:
    """Registra a fase e o contexto de validação de cada saída que o parser real recebe."""
    chamadas: list[tuple[Phase, ValidationContext | None]] = []
    original = cenario.parser.parse_output

    def espiao(raw_output: str, phase: Phase, validation: ValidationContext | None = None,
               finish_reason: str | None = None):
        chamadas.append((phase, validation))
        return original(raw_output=raw_output, phase=phase, validation=validation, finish_reason=finish_reason)

    cenario.parser.parse_output = espiao  # type: ignore[method-assign]
    return chamadas


def _invocacoes(cenario: RalphScenario, fase: Phase, recuperacoes: bool = False) -> list[int]:
    return [indice for indice, invocation in enumerate(cenario.session.invocations)
            if invocation.phase is fase and (recuperacoes or invocation.recovers_invocation_id is None)]


def _prompts(cenario: RalphScenario, fase: Phase) -> list[str]:
    return [cenario.llm.texts_of(indice)[0] for indice in _invocacoes(cenario, fase)]


def _area(prompt: str, titulo: str) -> str:
    conteudo = prompt.split(f"## {titulo}\n", 1)[1]
    return re.split(r"\n## (?!T\d+\b)", conteudo, maxsplit=1)[0].strip()


def _fases(cenario: RalphScenario) -> list[Phase]:
    return [invocation.phase for invocation in cenario.session.invocations]


def _temperaturas(cenario: RalphScenario, fase: Phase) -> list[float | None]:
    return [cenario.session.invocations[indice].temperature for indice in _invocacoes(cenario, fase)]


async def _executar_ate_falhar(cenario: RalphScenario, excecao: type[Exception]) -> list:
    eventos = []
    with pytest.raises(excecao):
        async for evento in cenario.stream(question=_PERGUNTA):
            eventos.append(evento)
    return eventos


_TECH_T1 = technical_criterion("T1")
_APROVA_T1 = _relatorio(("T1-AC1", True, "O balanco 200(80 - T) = 100(T - 20) esta substituido."),
                        ("T1-TECH", True, "Usa so as massas e temperaturas dadas; o balanco sustenta T = 60 C."))
_REPROVA_T1 = _relatorio(("T1-AC1", True, "As etapas do balanco estao presentes."), ("T1-TECH", False, _FEEDBACK))
_PLANEJAMENTO = [Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION,
                 Phase.A4_PLANNING_LEARNINGS]
_CICLO = [Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION]


# ── 1 e 3. Composição única e entradas reais ────────────────────────────────


async def test_b1_b2_e_parser_recebem_o_mesmo_conjunto_efetivo_com_tech_uma_vez() -> None:
    plano = _tarefa("T1", criterios_=("Apresenta o balanco com substituicao.", "Justifica cada termo."))
    cenario = _cenario([*_inicio(plano), _resolucao("T1", _R2),
                        _relatorio(("T1-AC1", True, "ok"), ("T1-AC2", True, "ok"), ("T1-TECH", True, "ok")),
                        aprendizados(_FATO), *_final()])
    validacoes = _espiar_parser(cenario)

    await cenario.run(question=_PERGUNTA)

    [b1] = _prompts(cenario, Phase.B1_TASK_RESOLUTION)
    [b2] = _prompts(cenario, Phase.B2_TASK_VERIFICATION)
    lista = ("- `T1-AC1`: Apresenta o balanco com substituicao.\n- `T1-AC2`: Justifica cada termo.\n"
             f"- `T1-TECH`: {_TECH_T1.description}")
    assert _area(b1, "Acceptance criteria for this task").endswith(lista)
    assert _area(b2, "Acceptance criteria for this task").endswith(lista)
    assert b1.count("`T1-TECH`:") == 1 and b2.count("`T1-TECH`:") == 1
    [b2_validacao] = [validation for phase, validation in validacoes if phase is Phase.B2_TASK_VERIFICATION]
    assert b2_validacao is not None and b2_validacao.expected_criteria_ids == ("T1-AC1", "T1-AC2", "T1-TECH")
    [b1_validacao] = [validation for phase, validation in validacoes if phase is Phase.B1_TASK_RESOLUTION]
    assert b1_validacao is not None and b1_validacao.expected_criteria_ids is None
    # A.2/A.3 continuam vendo só os critérios de autoria do planejador.
    confirmado = next(m for m in cenario.session.messages if m.subtype is Sub.TASKS)
    assert "T1-TECH" not in confirmado.content
    assert "T1-TECH" not in _prompts(cenario, Phase.A3_DECOMPOSITION_VALIDATION)[0]


async def test_b2_recebe_tarefa_resultado_criterios_e_aprendizados_em_areas_separadas_em_janela_nova() -> None:
    cenario = _cenario([*_inicio(), _resolucao("T1", _R2), _APROVA_T1, aprendizados(_FATO), *_final()])

    await cenario.run(question=_PERGUNTA)

    [indice] = _invocacoes(cenario, Phase.B2_TASK_VERIFICATION)
    conversa = cenario.llm.texts_of(indice)
    assert len(conversa) == 1, "B.2 roda em contexto novo, sem a conversa de B.1"
    b2 = conversa[0]
    tarefa = _area(b2, "Task")
    assert tarefa.endswith(f"### T1 — Balanco T1\n\n{_DESCRICAO}")
    assert _R2 not in tarefa and "T1-AC1" not in tarefa
    assert _area(b2, "Preliminary result").endswith(_R2)
    criterios_ = _area(b2, "Acceptance criteria for this task")
    assert _R2 not in criterios_ and _DESCRICAO not in criterios_ and _NOTA not in criterios_
    assert _NOTA in _area(b2, "Key Learnings") and "T1-TECH" not in _area(b2, "Key Learnings")
    assert _area(b2, "Proposed revision").endswith("None: this task does not review stored results.")
    # Nenhum histórico do planejamento chega a B.2.
    assert _PERGUNTA not in b2 and "Candidate plan" not in b2 and '"tasks"' not in b2


# ── 4 e 10. Falha técnica isolada, feedback e temperatura ───────────────────


async def test_falha_tecnica_isolada_reprova_e_b1_e_retentada_com_o_feedback_integral() -> None:
    cenario = _cenario([*_inicio(), _resolucao("T1", _R1), _REPROVA_T1, _resolucao("T1", _R2), _APROVA_T1,
                        aprendizados(_FATO), *_final()])
    validacoes = _espiar_parser(cenario)

    eventos = await cenario.run(question=_PERGUNTA)

    # Toda tentativa recebe o mesmo conjunto efetivo, com TECH uma única vez, em B.1, B.2 e no parser.
    for prompt in (*_prompts(cenario, Phase.B1_TASK_RESOLUTION), *_prompts(cenario, Phase.B2_TASK_VERIFICATION)):
        assert _area(prompt, "Acceptance criteria for this task").count("`T1-TECH`:") == 1
    assert [v.expected_criteria_ids for phase, v in validacoes if phase is Phase.B2_TASK_VERIFICATION] == [
        ("T1-AC1", "T1-TECH"), ("T1-AC1", "T1-TECH")]
    assert [e.subtype for e in eventos if e.task == "T1"] == [
        Sub.RESET, Sub.EXECUTE, Sub.REASONING, Sub.VERIFY_FAIL, Sub.REASONING, Sub.VERIFY_PASS, Sub.STORE, Sub.LEARN,
    ]
    falha = next(e for e in eventos if e.subtype is Sub.VERIFY_FAIL)
    assert "`T1-AC1` — met" in falha.content and f"`T1-TECH` — not met: {_FEEDBACK}" in falha.content
    # A nova B.1 recebe, em contexto novo, o resultado reprovado e o veredito de TECH na íntegra.
    primeira, segunda = _prompts(cenario, Phase.B1_TASK_RESOLUTION)
    anteriores = _area(segunda, "Previous attempts at this task")
    assert _R1 in anteriores and _FEEDBACK in anteriores
    assert "Criteria not met: `T1-TECH`." in anteriores
    assert _area(primeira, "Previous attempts at this task").endswith("None: this is the first attempt at this task.")
    assert len(cenario.llm.texts_of(_invocacoes(cenario, Phase.B1_TASK_RESOLUTION)[1])) == 1
    assert _temperaturas(cenario, Phase.B1_TASK_RESOLUTION) == [_TEMPERATURA, 1.0]
    assert _temperaturas(cenario, Phase.B2_TASK_VERIFICATION) == [_TEMPERATURA, _TEMPERATURA]
    # Só o resultado aprovado foi armazenado e extraído; o reprovado não virou fato vigente.
    assert cenario.results_ledger.get(task_id="T1").content == _R2
    assert _fases(cenario).count(Phase.B4_LEARNINGS_EXTRACTION) == 1
    assert [learning.content for learning in cenario.learnings_memory.all()] == [_NOTA, _FATO]
    assert cenario.session.totals.total_llm_calls == cenario.llm.call_count == len(cenario.session.invocations)
    assert cenario.session.status is SessionStatusEnum.COMPLETED


async def test_aprovacao_completa_armazena_e_extrai_sem_chamada_extra_de_verificacao() -> None:
    cenario = _cenario([*_inicio(), _resolucao("T1", _R2), _APROVA_T1, aprendizados(_FATO), *_final()])

    eventos = await cenario.run(question=_PERGUNTA)

    assert _fases(cenario) == [*_PLANEJAMENTO, *_CICLO, Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER]
    assert cenario.results_ledger.status_of(task_id="T1") is ResultStatusEnum.CURRENT
    assert eventos[-1].type is ThinkingEventTypeEnum.RESULT and eventos[-1].content == "60 C"


# ── 6. Relatórios inconsistentes: recuperação sem mudar vereditos ───────────


_INCONSISTENTES = {
    "tech_ausente": (_relatorio(("T1-AC1", True, "ok")), OutputProblemCodeEnum.CRITERIA_IDS),
    "tech_repetido": (_relatorio(("T1-AC1", True, "ok"), ("T1-TECH", True, "ok"), ("T1-TECH", True, "ok")),
                      OutputProblemCodeEnum.CRITERIA_IDS),
    "id_desconhecido": (_relatorio(("T1-AC1", True, "ok"), ("T1-TECH", True, "ok"), ("T1-AC7", True, "ok")),
                        OutputProblemCodeEnum.CRITERIA_IDS),
    "aprovado_com_tech_falso": (_relatorio(("T1-AC1", True, "ok"), ("T1-TECH", False, "falha"), unmet=[],
                                           decision="approved"), OutputProblemCodeEnum.DECISION_CONSISTENCY),
    "reprovado_sem_pendencias": (_relatorio(("T1-AC1", True, "ok"), ("T1-TECH", True, "ok"), decision="reproved"),
                                 OutputProblemCodeEnum.DECISION_CONSISTENCY),
    "pendencias_incompativeis": (_relatorio(("T1-AC1", True, "ok"), ("T1-TECH", False, "falha"), unmet=["T1-AC1"]),
                                 OutputProblemCodeEnum.DECISION_CONSISTENCY),
}


@pytest.mark.parametrize("nome", list(_INCONSISTENTES))
async def test_relatorio_inconsistente_e_recuperado_na_janela_de_b2_sem_mudar_vereditos(nome: str) -> None:
    invalido, codigo = _INCONSISTENTES[nome]
    cenario = _cenario([*_inicio(), _resolucao("T1", _R1), invalido, _REPROVA_T1, _resolucao("T1", _R2), _APROVA_T1,
                        aprendizados(_FATO), *_final()])

    eventos = await cenario.run(question=_PERGUNTA)

    recuperacao = next(i for i in cenario.session.invocations if i.recovers_invocation_id is not None)
    original = next(i for i in cenario.session.invocations if i.id == recuperacao.recovers_invocation_id)
    assert original.phase is recuperacao.phase is Phase.B2_TASK_VERIFICATION
    assert original.output_diagnostic.problem.code is codigo
    assert original.recovery.result is RecoveryResultEnum.RECOVERED
    assert recuperacao.context_id == original.context_id
    # O veredito aceito é o da saída corrigida, tal como o modelo a escreveu: reprovação por TECH.
    assert [e.subtype for e in eventos if e.subtype in (Sub.VERIFY_FAIL, Sub.VERIFY_PASS)] == [
        Sub.VERIFY_FAIL, Sub.VERIFY_PASS]
    assert cenario.cost_guard.attempts_by_task["T1"] == 2  # type: ignore[attr-defined]
    tarefa_primeira = cenario.session.messages
    assert any(_FEEDBACK in m.content for m in tarefa_primeira if m.subtype is Sub.VERIFY_FAIL)
    assert cenario.session.totals.total_llm_calls == cenario.llm.call_count


async def test_b2_que_nunca_avalia_tech_encerra_como_erro_tecnico_sem_armazenar_nem_sintetizar() -> None:
    sem_tech = _relatorio(("T1-AC1", True, "ok"))
    cenario = _cenario([*_inicio(), _resolucao("T1", _R2), sem_tech, sem_tech, sem_tech],
                       settings=FakeSettings(ralph_json_parse_max_retries=2))

    eventos = await _executar_ate_falhar(cenario, PhaseParsingError)

    assert not [e for e in eventos if e.subtype in (Sub.STORE, Sub.LEARN) and e.task == "T1"]
    assert cenario.results_ledger.current() == ()
    assert cenario.session.failure.reason is SessionFailureReasonEnum.TECHNICAL_ERROR
    assert cenario.session.failure.phase is Phase.B2_TASK_VERIFICATION
    assert cenario.session.final_answer is None
    assert cenario.session.totals.total_llm_calls == cenario.llm.call_count == 8


# ── 11. Cinco tentativas por tarefa ─────────────────────────────────────────


async def test_quatro_reprovacoes_tecnicas_e_aprovacao_na_quinta_concluem() -> None:
    reprovacoes = [item for n in range(4) for item in (_resolucao("T1", f"RESULTADO-RUIM-{n}"), _REPROVA_T1)]
    cenario = _cenario([*_inicio(), *reprovacoes, _resolucao("T1", _R2), _APROVA_T1, aprendizados(_FATO),
                        *_final()], budget=_orcamento())

    eventos = await cenario.run(question=_PERGUNTA)

    assert [e.subtype for e in eventos].count(Sub.VERIFY_FAIL) == 4
    assert _temperaturas(cenario, Phase.B1_TASK_RESOLUTION) == [_TEMPERATURA, 1.0, 1.0, 1.0, 1.0]
    assert _temperaturas(cenario, Phase.B2_TASK_VERIFICATION) == [_TEMPERATURA] * 5
    assert cenario.results_ledger.get(task_id="T1").content == _R2
    assert cenario.session.status is SessionStatusEnum.COMPLETED


async def test_cinco_reprovacoes_tecnicas_encerram_sem_sexta_tentativa_armazenamento_ou_sintese() -> None:
    reprovacoes = [item for n in range(5) for item in (_resolucao("T1", f"RESULTADO-RUIM-{n}"), _REPROVA_T1)]
    cenario = _cenario([*_inicio(), *reprovacoes, _resolucao("T1", "SEXTA"), _APROVA_T1], budget=_orcamento())

    eventos = await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert _fases(cenario).count(Phase.B1_TASK_RESOLUTION) == 5
    assert not [e for e in eventos if e.subtype in (Sub.STORE, Sub.LEARN) and e.task == "T1"]
    assert Phase.C1_GLOBAL_VERIFICATION not in _fases(cenario) and Phase.C3_FINAL_ANSWER not in _fases(cenario)
    assert cenario.results_ledger.current() == ()
    assert [learning.content for learning in cenario.learnings_memory.all()] == [_NOTA]
    falha = cenario.session.failure
    assert falha.limit is BudgetLimitEnum.TASK_ATTEMPTS and falha.task_id == "T1"
    assert cenario.session.final_answer is None
    assert len(cenario.llm.responses) == 2, "a sexta tentativa roteirizada nunca foi consumida"


async def test_orcamento_esgotado_depois_de_reprovacao_tecnica_nao_promove_o_resultado_reprovado() -> None:
    cenario = _cenario([*_inicio(), _resolucao("T1", _R1), _REPROVA_T1, _resolucao("T1", _R2), _APROVA_T1],
                       budget=_orcamento(max_llm_calls_per_session=6))

    await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert cenario.session.failure.limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION
    assert cenario.session.failure.phase is Phase.B1_TASK_RESOLUTION
    assert cenario.results_ledger.current() == ()
    assert cenario.session.totals.total_llm_calls == cenario.llm.call_count == 6


# ── 7. TECH e REV independentes ─────────────────────────────────────────────


_MOTIVO = "T2 contradiz T1 sobre a mesma temperatura de equilibrio."
_REVISAO = ("T2", "superseded", "T2 usou uma capacidade termica nao fornecida.")


def _ate_a_revisao() -> list[str]:
    return [
        *_inicio(_tarefa("T1"), _tarefa("T2", descricao="Confira o balanco por outro caminho.")),
        _resolucao("T1", _R2), aprovado("T1"), aprendizados(_FATO),
        _resolucao("T2", _R1), aprovado("T2"), aprendizados("T = 54,3 C com recipiente."),
        global_reprovado("AC1"),
        _plano(_tarefa("T3", descricao="Investigue qual balanco e sustentado pelos dados.",
                       review={"task_ids": ["T2"], "reason": _MOTIVO})),
        _resolucao("T3", "RESOLUCAO-T3: o recipiente nao foi dado; T = 60 C.", _REVISAO),
    ]


def _b2_revisora(tech: bool, rev: bool) -> str:
    return _relatorio(("T3-AC1", True, "ok"), ("T3-TECH", tech, "TECH" if tech else "FALHA-TECH"),
                      ("T3-REV", rev, "REV" if rev else "FALHA-REV"))


@pytest.mark.parametrize(("tech", "rev"), [(False, True), (True, False)], ids=["so_tech_falha", "so_rev_falha"])
async def test_tech_e_rev_sao_independentes_e_a_revisao_so_e_aplicada_com_os_dois(tech: bool, rev: bool) -> None:
    cenario = _cenario([
        *_ate_a_revisao(), _b2_revisora(tech, rev),
        _resolucao("T3", "RESOLUCAO-T3: o recipiente nao foi dado; T = 60 C.", _REVISAO), _b2_revisora(True, True),
        aprendizados(_FATO), global_aprovado(), resposta_final("60 C"),
    ])

    eventos = await cenario.run(question=_PERGUNTA)

    b2 = _prompts(cenario, Phase.B2_TASK_VERIFICATION)[-1]
    assert re.findall(r"^- `(T3-[A-Z0-9]+)`", _area(b2, "Acceptance criteria for this task"), flags=re.M) == [
        "T3-AC1", "T3-TECH", "T3-REV"]
    reprovacao = next(e for e in eventos if e.subtype is Sub.VERIFY_FAIL)
    armazenamentos = [i for i, e in enumerate(eventos) if e.subtype is Sub.STORE and e.task == "T3"]
    assert armazenamentos and eventos.index(reprovacao) < armazenamentos[0]
    assert len(cenario.session.result_revisions) == 1
    assert cenario.results_ledger.status_of(task_id="T2") is ResultStatusEnum.SUPERSEDED
    assert cenario.cost_guard.attempts_by_task["T3"] == 2  # type: ignore[attr-defined]


async def test_revisao_reprovada_em_todas_as_tentativas_por_tech_nao_e_aplicada() -> None:
    cenario = _cenario([*_ate_a_revisao(), _b2_revisora(False, True)], cost_guard=FakeCostGuard(max_task_attempts=1))

    await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert cenario.session.result_revisions == []
    assert cenario.results_ledger.status_of(task_id="T2") is ResultStatusEnum.CURRENT
    assert cenario.session.failure.limit is BudgetLimitEnum.TASK_ATTEMPTS


# ── 2. Planejador que emite o identificador reservado ──────────────────────


async def test_a2_que_emite_tech_e_corrigido_pela_recuperacao_estrutural_e_nao_por_a3() -> None:
    colidente = _plano(_tarefa("T1", criterios_=("Apresenta o balanco.",)) | {
        "acceptance_criteria": [{"id": "T1-AC1", "description": "a"}, {"id": "T1-TECH", "description": "b"}]})
    cost_guard = FakeCostGuard()
    cenario = _cenario([criterios(), colidente, _plano(_tarefa("T1")), plano_aprovado(), anotacoes_do_enunciado(_NOTA),
                        _resolucao("T1", _R2), _APROVA_T1, aprendizados(_FATO), *_final()], cost_guard=cost_guard)

    await cenario.run(question=_PERGUNTA)

    [original] = [i for i in cenario.session.invocations if i.recovery is not None]
    assert original.phase is Phase.A2_TASK_DECOMPOSITION
    assert original.output_diagnostic.problem.code is OutputProblemCodeEnum.INVALID_VALUE
    assert original.output_diagnostic.problem.affected_ids == ("T1-TECH",)
    assert cost_guard.planning_attempts == 1
    assert _fases(cenario).count(Phase.A3_DECOMPOSITION_VALIDATION) == 1
    [a3] = _prompts(cenario, Phase.A3_DECOMPOSITION_VALIDATION)
    assert "T1-TECH" not in a3
    assert cenario.session.status is SessionStatusEnum.COMPLETED


async def test_c2_que_emite_tech_e_corrigido_e_a_tarefa_adicional_recebe_tech_do_harness() -> None:
    colidente = _plano({**_tarefa("T2", descricao="Confira a conservacao de energia."),
                        "acceptance_criteria": [{"id": "T2-TECH", "description": "x"}]})
    cenario = _cenario([
        *_inicio(), _resolucao("T1", _R2), _APROVA_T1, aprendizados(_FATO), global_reprovado("AC1"),
        colidente, _plano(_tarefa("T2", descricao="Confira a conservacao de energia.")),
        _resolucao("T2", "A energia cedida e igual a recebida."), aprovado("T2"), aprendizados(),
        *_final(),
    ])
    validacoes = _espiar_parser(cenario)

    await cenario.run(question=_PERGUNTA)

    [original] = [i for i in cenario.session.invocations if i.recovery is not None]
    assert original.phase is Phase.C2_ADDITIONAL_PLANNING
    assert original.output_diagnostic.problem.affected_ids == ("T2-TECH",)
    assert _fases(cenario).count(Phase.A3_DECOMPOSITION_VALIDATION) == 1, "C.2 não ganhou nova avaliação"
    b2_esperados = [v.expected_criteria_ids for phase, v in validacoes if phase is Phase.B2_TASK_VERIFICATION]
    assert b2_esperados == [("T1-AC1", "T1-TECH"), ("T2-AC1", "T2-TECH")]


# ── C.1, C.3 e B.4 ──────────────────────────────────────────────────────────


async def test_c1_e_c3_nao_recebem_tech_e_b4_recebe_o_historico_sem_promover_vereditos() -> None:
    cenario = _cenario([*_inicio(), _resolucao("T1", _R1), _REPROVA_T1, _resolucao("T1", _R2), _APROVA_T1,
                        aprendizados(_FATO), *_final()])
    validacoes = _espiar_parser(cenario)

    await cenario.run(question=_PERGUNTA)

    [c1_validacao] = [v for phase, v in validacoes if phase is Phase.C1_GLOBAL_VERIFICATION]
    assert c1_validacao.expected_criteria_ids == ("AC1", "AC2")
    [c1] = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)
    [c3] = _prompts(cenario, Phase.C3_FINAL_ANSWER)
    assert "TECH" not in c1 and "TECH" not in c3
    assert _R2 in _area(c1, "Stored results") and _R1 not in _area(c1, "Stored results")
    assert _area(c1, "Stored results") == _area(c3, "Stored results")
    [b4] = _prompts(cenario, Phase.B4_LEARNINGS_EXTRACTION)
    assert "T1-TECH" not in _area(b4, "Task")
    historico = _area(b4, "Task history")
    assert _FEEDBACK in historico and "### Attempt 1 — rejected" in historico
    assert all("TECH" not in learning.content for learning in cenario.learnings_memory.all())


# ── 13 e 14. Integração das duas frentes e independência dos limites ───────


async def test_integracao_das_duas_frentes_do_plano_revisado_a_resposta_aprovada() -> None:
    antecipado = _tarefa("T1", descricao="Mostre que o recipiente absorve calor e que T = 54,3 C.",
                         titulo="Mostrar 54,3 C")
    aberto = _tarefa("T1", titulo="Determinar a temperatura de equilibrio")
    cenario = _cenario([
        criterios(), _plano(antecipado),
        plano_reprovado(problema_do_plano(task_id="T1", problem="Impoe o resultado.", adjustment="Manter em aberto.")),
        _plano(aberto), plano_aprovado(), anotacoes_do_enunciado(_NOTA),
        _resolucao("T1", _R1), _REPROVA_T1, _resolucao("T1", _R2), _APROVA_T1, aprendizados(_FATO),
        global_aprovado(), resposta_final("60 C"),
    ], budget=_orcamento())

    eventos = await cenario.run(question=_PERGUNTA)

    assert _fases(cenario) == [
        Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION,
        Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION, Phase.A4_PLANNING_LEARNINGS,
        Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION,
        Phase.B4_LEARNINGS_EXTRACTION, Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER,
    ]
    assert all(len(cenario.llm.texts_of(i)) == 1 for i in range(cenario.llm.call_count)), "toda fase em janela nova"
    confirmado = next(e for e in eventos if e.subtype is Sub.TASKS)
    assert "Determinar a temperatura de equilibrio" in confirmado.content and "54,3" not in confirmado.content
    assert cenario.task_queue.total_created() == 1
    for b in (*_prompts(cenario, Phase.B1_TASK_RESOLUTION), *_prompts(cenario, Phase.B2_TASK_VERIFICATION)):
        assert "Determinar a temperatura de equilibrio" in b and "Mostrar 54,3 C" not in b
        assert _NOTA in _area(b, "Key Learnings")
    assert [e.subtype for e in eventos].count(Sub.PLAN_REJECTED) == 1
    assert [e.phase for e in eventos if e.subtype is Sub.LEARN][0] is Phase.A4_PLANNING_LEARNINGS
    assert cenario.session.final_answer == "60 C" and cenario.session.status is SessionStatusEnum.COMPLETED
    assert cenario.session.totals.total_llm_calls == cenario.llm.call_count == 13


async def test_tentativas_do_planejamento_nao_reduzem_as_da_tarefa_e_b2_nao_reabre_o_planejamento() -> None:
    rejeicoes = [item for _ in range(4) for item in (_plano(_tarefa("T1")), plano_reprovado())]
    reprovacoes = [item for n in range(4) for item in (_resolucao("T1", f"RUIM-{n}"), _REPROVA_T1)]
    cenario = _cenario([
        criterios(), *rejeicoes, _plano(_tarefa("T1")), plano_aprovado(), anotacoes_do_enunciado(_NOTA),
        *reprovacoes, _resolucao("T1", _R2), _APROVA_T1, aprendizados(_FATO), *_final(),
    ], budget=_orcamento())

    await cenario.run(question=_PERGUNTA)

    fases = _fases(cenario)
    assert fases.count(Phase.A3_DECOMPOSITION_VALIDATION) == 5 and fases.count(Phase.B2_TASK_VERIFICATION) == 5
    ultima_a3 = max(i for i, fase in enumerate(fases) if fase is Phase.A3_DECOMPOSITION_VALIDATION)
    assert Phase.A2_TASK_DECOMPOSITION not in fases[ultima_a3:]
    assert cenario.session.status is SessionStatusEnum.COMPLETED


# ── 8 e 9. Matriz sintética: transporte, sem oráculo nas entradas ──────────


@pytest.mark.parametrize("caso", _MATRIX["cases"], ids=lambda caso: caso["name"])
async def test_matriz_tecnica_transporta_cada_caso_pelo_fluxo(caso: dict[str, Any]) -> None:
    tarefa = caso["task"]
    plano = {"id": tarefa["id"], "title": tarefa["title"], "description": tarefa["description"],
             "acceptance_criteria": caso["criteria"]}
    referencia = caso["reference"]
    avaliacoes = [(criterion_id, met, referencia["rationale"] if not met else "conferido")
                  for criterion_id, met in referencia["met"].items()]
    aprovacao = [(criterion_id, True, "conferido") for criterion_id in referencia["met"]]
    corrigido = "RESOLUCAO-CORRIGIDA: refeita a partir do defeito apontado."
    roteiro = [criterios(), _plano(plano), plano_aprovado(), anotacoes_do_enunciado(*caso["learnings"]),
               _resolucao(tarefa["id"], caso["preliminary_result"]), _relatorio(*avaliacoes)]
    if referencia["decision"] == "reproved":
        roteiro += [_resolucao(tarefa["id"], corrigido), _relatorio(*aprovacao)]
    cenario = _cenario([*roteiro, aprendizados(), *_final()])

    await cenario.run(question=tarefa["description"])

    b2 = _prompts(cenario, Phase.B2_TASK_VERIFICATION)[0]
    assert tarefa["description"] in _area(b2, "Task")
    assert _area(b2, "Preliminary result").endswith(caso["preliminary_result"])
    assert f"`{tarefa['id']}-TECH`" in _area(b2, "Acceptance criteria for this task")
    for prompt in (*_prompts(cenario, Phase.A2_TASK_DECOMPOSITION), b2, _prompts(cenario, Phase.B1_TASK_RESOLUTION)[0]):
        assert referencia["rationale"] not in prompt
        assert all(check not in prompt for check in caso["review_checks"])
    if referencia["decision"] == "reproved":
        assert referencia["rationale"] in _area(_prompts(cenario, Phase.B1_TASK_RESOLUTION)[1],
                                                "Previous attempts at this task")
        assert cenario.results_ledger.get(task_id=tarefa["id"]).content == corrigido
    else:
        assert cenario.results_ledger.get(task_id=tarefa["id"]).content == caso["preliminary_result"]


async def test_reprovacao_so_por_tech_com_roteiro_auxiliar_mantem_os_planejados_atendidos() -> None:
    cenario = _cenario([*_inicio(), _resolucao("T1", _R1), reprovado_tecnico("T1", _FEEDBACK),
                        _resolucao("T1", _R2), aprovado("T1"), aprendizados(_FATO), *_final()])

    eventos = await cenario.run(question=_PERGUNTA)

    assert cenario.task_queue.is_empty()
    falha = next(e for e in eventos if e.subtype is Sub.VERIFY_FAIL)
    assert "`T1-AC1` — met" in falha.content and "`T1-TECH` — not met" in falha.content
