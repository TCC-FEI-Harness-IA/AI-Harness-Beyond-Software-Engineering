"""Nova fase de validação — 01: planejamento aprovado antes da execução (fluxo versão 2).

A.2 gera um plano candidato; A.3 o julga em janela nova, com o pedido, os critérios gerais e só esse
candidato. Reprovado, A.2 recebe o último candidato e o relatório e gera o próximo; aprovado, o plano é
confirmado na fila uma única vez e só então A.4 extrai os aprendizados do enunciado. Os testes usam o
parser, a fila, a memória, o recorder e o guardião reais, com completions roteirizadas: provam o protocolo,
não que um modelo real identificará todo plano ruim.
"""
import json
import logging

import pytest

from src.domain.entities.resilience.cost_budget import CostBudget
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.ralph_flow_version_enum import RalphFlowVersionEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum as Sub
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.config.settings import Settings
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_prompt_template_provider import FakePromptTemplateProvider
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import (
    anotacoes_do_enunciado,
    aprovado,
    criterios,
    global_aprovado,
    plano_aprovado,
    plano_reprovado,
    problema_do_plano,
    resolucao,
    resposta_final,
    tarefa_aprovada,
)

_TEMPERATURA = 0.3


def _tarefa(task_id: str, titulo: str, criterios: tuple[str, ...] = ("criterio",), **extra: object) -> dict:
    return {
        "id": task_id,
        "title": titulo,
        "description": f"descricao de {titulo}",
        "acceptance_criteria": [{"id": f"{task_id}-AC{i + 1}", "description": c} for i, c in enumerate(criterios)],
        **extra,
    }


def _plano(*tarefas: dict) -> str:
    return json.dumps({"tasks": list(tarefas)})


def _execucao(*ids: str) -> list[str]:
    roteiro: list[str] = []
    for task_id in ids:
        roteiro += tarefa_aprovada(task_id, f"resultado de {task_id}", f"fato de {task_id}")
    return [*roteiro, global_aprovado(), resposta_final()]


_C1_ANTECIPADO = _tarefa(
    "T1", "Mostrar que o resistor maior dissipa mais", ("Provar que o resistor de 12 ohms dissipa mais.",)
)
_C1_ABERTO = _tarefa("T1", "Comparar as potencias dissipadas", ("Determinar e justificar qual resistor dissipa mais.",))
_REPROVACAO_T1 = problema_do_plano(
    task_id="T1", criterion_id="T1-AC1", problem="PROBLEMA-UNICO: o criterio impoe a comparacao.",
    adjustment="AJUSTE-UNICO: pedir a comparacao mantendo o resultado em aberto.",
)


def _cenario(responses: list[str], **kwargs) -> RalphScenario:
    return RalphScenario(responses=responses, temperature=_TEMPERATURA, **kwargs)


def _fases_invocadas(cenario: RalphScenario) -> list[Phase]:
    return [invocation.phase for invocation in cenario.session.invocations]


def _real_provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=Settings(), logger=logging.getLogger("teste.templates"))


# ── 1. Primeiro candidato aprovado ──────────────────────────────────────────

async def test_primeiro_candidato_aprovado_confirma_uma_vez_e_segue_para_a4_b_e_c() -> None:
    cost_guard = FakeCostGuard()
    cenario = _cenario([
        criterios(), _plano(_C1_ABERTO, _tarefa("T2", "Integrar", depends_on=["T1"])), plano_aprovado(),
        anotacoes_do_enunciado("Resistores: 4 ohms e 12 ohms em paralelo a 6 V."),
        *_execucao("T1", "T2"),
    ], cost_guard=cost_guard)

    eventos = await cenario.run()

    assert [(e.phase, e.subtype) for e in eventos[:5]] == [
        (Phase.A1_GENERAL_CRITERIA, Sub.SETUP),
        (Phase.A2_TASK_DECOMPOSITION, Sub.PLAN_CANDIDATE),
        (Phase.A3_DECOMPOSITION_VALIDATION, Sub.PLAN_APPROVED),
        (Phase.A3_DECOMPOSITION_VALIDATION, Sub.TASKS),
        (Phase.A4_PLANNING_LEARNINGS, Sub.LEARN),
    ]
    assert [e.subtype for e in eventos].count(Sub.TASKS) == 1
    assert eventos[-1].type is ThinkingEventTypeEnum.RESULT
    assert cost_guard.tasks_created == [2]
    assert cost_guard.planning_attempts == 1
    assert [e.task for e in eventos if e.subtype is Sub.RESET] == ["T1", "T2"]
    assert _fases_invocadas(cenario)[:4] == [
        Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION,
        Phase.A3_DECOMPOSITION_VALIDATION, Phase.A4_PLANNING_LEARNINGS,
    ]
    assert cenario.session.status is SessionStatusEnum.COMPLETED
    assert cenario.session.flow_version is RalphFlowVersionEnum.VALIDATED_PLANNING
    assert all(e.flow_version is RalphFlowVersionEnum.VALIDATED_PLANNING for e in eventos)


async def test_o_plano_executado_e_exatamente_o_aprovado_e_a_dependencia_chega_a_fila() -> None:
    cenario = _cenario([
        criterios(), _plano(_C1_ABERTO, _tarefa("T2", "Integrar", depends_on=["T1"])), plano_aprovado(),
        anotacoes_do_enunciado(), *_execucao("T1", "T2"),
    ])

    eventos = await cenario.run()

    confirmacao = next(e for e in eventos if e.subtype is Sub.TASKS)
    candidato = next(e for e in eventos if e.subtype is Sub.PLAN_CANDIDATE)
    assert "### T1 — Comparar as potencias dissipadas" in confirmacao.content
    assert "**Depends on:** `T2`" not in confirmacao.content and "**Depends on:** `T1`" in confirmacao.content
    assert confirmacao.content.split("\n", 1)[1] == candidato.content.split("\n", 1)[1]
    assert cenario.task_queue.total_created() == 2


async def test_a3_recebe_pedido_criterios_gerais_e_o_candidato_com_dependencias() -> None:
    provider = FakePromptTemplateProvider()
    cenario = _cenario([
        criterios(), _plano(_C1_ABERTO, _tarefa("T2", "Integrar", depends_on=["T1"])), plano_aprovado(),
        anotacoes_do_enunciado(), *_execucao("T1", "T2"),
    ], template_provider=provider)

    await cenario.run(question="PERGUNTA-ORIGINAL")

    [variaveis] = provider.variables_of(Phase.A3_DECOMPOSITION_VALIDATION)
    assert set(variaveis) == {"user_question", "general_acceptance_criteria", "candidate_plan"}
    assert variaveis["user_question"] == "PERGUNTA-ORIGINAL"
    assert "`AC1`: responder em portugues" in variaveis["general_acceptance_criteria"]
    assert "### T1 — Comparar as potencias dissipadas" in variaveis["candidate_plan"]
    assert "`T1-AC1`: Determinar e justificar qual resistor dissipa mais." in variaveis["candidate_plan"]
    assert "**Depends on:** `T1`" in variaveis["candidate_plan"]
    assert provider.variables_of(Phase.A2_TASK_DECOMPOSITION)[0]["plan_revision"].startswith("None:")
    assert provider.variables_of(Phase.A4_PLANNING_LEARNINGS) == [{"user_question": "PERGUNTA-ORIGINAL"}]


# ── 2 e 3. Correção semântica e várias revisões ─────────────────────────────

async def test_reprovacao_semantica_envia_a_a2_o_ultimo_candidato_e_o_relatorio_e_a3_julga_so_o_novo() -> None:
    provider = FakePromptTemplateProvider()
    cenario = _cenario([
        criterios(), _plano(_C1_ANTECIPADO), plano_reprovado(_REPROVACAO_T1),
        _plano(_C1_ABERTO), plano_aprovado(), anotacoes_do_enunciado(), *_execucao("T1"),
    ], template_provider=provider)

    eventos = await cenario.run()

    revisao = provider.variables_of(Phase.A2_TASK_DECOMPOSITION)[1]["plan_revision"]
    assert "Mostrar que o resistor maior dissipa mais" in revisao
    assert "PROBLEMA-UNICO" in revisao and "AJUSTE-UNICO" in revisao
    assert "<previous_candidate>" in revisao and "<validation_report>" in revisao
    segunda_a3 = provider.variables_of(Phase.A3_DECOMPOSITION_VALIDATION)[1]
    assert "Comparar as potencias dissipadas" in segunda_a3["candidate_plan"]
    for texto in segunda_a3.values():
        assert "Mostrar que o resistor maior" not in texto
        assert "PROBLEMA-UNICO" not in texto and "AJUSTE-UNICO" not in texto
    assert [e.subtype for e in eventos[1:6]] == [
        Sub.PLAN_CANDIDATE, Sub.PLAN_REJECTED, Sub.PLAN_CANDIDATE, Sub.PLAN_APPROVED, Sub.TASKS,
    ]
    rejeicao = eventos[2]
    assert "`rejected`" in rejeicao.content and "PROBLEMA-UNICO" in rejeicao.content
    assert "`T1` / `T1-AC1`" in rejeicao.content
    confirmacao = eventos[5]
    assert "Comparar as potencias dissipadas" in confirmacao.content
    assert "Mostrar que o resistor maior" not in confirmacao.content


async def test_varias_revisoes_cada_a2_recebe_so_a_ultima_versao_e_a_auditoria_guarda_todas() -> None:
    provider = FakePromptTemplateProvider()
    candidatos = [_tarefa("T1", f"VERSAO-{n}") for n in range(1, 4)]
    relatorios = [
        plano_reprovado(problema_do_plano(task_id="T1", problem=f"PROBLEMA-{n}", adjustment=f"AJUSTE-{n}"))
        for n in range(1, 3)
    ]
    cenario = _cenario([
        criterios(),
        _plano(candidatos[0]), relatorios[0],
        _plano(candidatos[1]), relatorios[1],
        _plano(candidatos[2]), plano_aprovado(),
        anotacoes_do_enunciado(), *_execucao("T1"),
    ], template_provider=provider)

    await cenario.run()

    revisoes = [v["plan_revision"] for v in provider.variables_of(Phase.A2_TASK_DECOMPOSITION)]
    assert revisoes[0].startswith("None:")
    assert "VERSAO-1" in revisoes[1] and "PROBLEMA-1" in revisoes[1]
    assert "VERSAO-2" in revisoes[2] and "PROBLEMA-2" in revisoes[2]
    assert "VERSAO-1" not in revisoes[2] and "PROBLEMA-1" not in revisoes[2]
    julgados = [v["candidate_plan"] for v in provider.variables_of(Phase.A3_DECOMPOSITION_VALIDATION)]
    assert [f"VERSAO-{n}" in julgado for n, julgado in enumerate(julgados, start=1)] == [True, True, True]
    assert "VERSAO-1" not in julgados[2] and "VERSAO-2" not in julgados[2]

    fases_de_planejamento = (Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION)
    planejamento = [m for m in cenario.session.messages if m.phase in fases_de_planejamento]
    assert [(m.phase, m.subtype) for m in planejamento] == [
        (Phase.A2_TASK_DECOMPOSITION, Sub.PLAN_CANDIDATE), (Phase.A3_DECOMPOSITION_VALIDATION, Sub.PLAN_REJECTED),
        (Phase.A2_TASK_DECOMPOSITION, Sub.PLAN_CANDIDATE), (Phase.A3_DECOMPOSITION_VALIDATION, Sub.PLAN_REJECTED),
        (Phase.A2_TASK_DECOMPOSITION, Sub.PLAN_CANDIDATE), (Phase.A3_DECOMPOSITION_VALIDATION, Sub.PLAN_APPROVED),
        (Phase.A3_DECOMPOSITION_VALIDATION, Sub.TASKS),
    ]
    assert [n for n in range(1, 4) if f"VERSAO-{n}" in planejamento[2 * (n - 1)].content] == [1, 2, 3]
    # Cada candidato e cada relatório ficam com a sua janela, o seu prompt e o seu consumo; nada é sobrescrito.
    modelo = [m for m in planejamento if m.source is not MessageSourceEnum.SYSTEM]
    assert len({m.context_id for m in modelo}) == 6
    assert all(m.prompt_input and m.tokens_input > 0 for m in modelo)
    assert planejamento[-1].source is MessageSourceEnum.SYSTEM and planejamento[-1].tokens_input == 0


async def test_cada_geracao_e_cada_avaliacao_abrem_janela_nova_sem_restaurar_conversa() -> None:
    cenario = _cenario([
        criterios(), _plano(_C1_ANTECIPADO), plano_reprovado(_REPROVACAO_T1),
        _plano(_C1_ABERTO), plano_aprovado(), anotacoes_do_enunciado(), *_execucao("T1"),
    ], template_provider=_real_provider())

    await cenario.run()

    # Chamadas: A1, A2, A3, A2, A3, A4 ... Cada uma vai com uma única mensagem: o template renderizado.
    for indice in range(1, 6):
        assert len(cenario.llm.conversations[indice]) == 1, indice
    segunda_a2 = cenario.llm.texts_of(3)[0]
    assert segunda_a2.startswith("# A.2")
    assert "<previous_candidate>" in segunda_a2 and "PROBLEMA-UNICO" in segunda_a2
    segunda_a3 = cenario.llm.texts_of(4)[0]
    assert segunda_a3.startswith("# A.3 — Task Decomposition Validator")
    assert "Comparar as potencias dissipadas" in segunda_a3
    assert "Mostrar que o resistor maior" not in segunda_a3 and "PROBLEMA-UNICO" not in segunda_a3
    assert cenario.llm.texts_of(5)[0].startswith("# A.4")


# ── 4. Fila isolada ─────────────────────────────────────────────────────────

async def test_candidatos_recusados_nao_consomem_slots_nem_reservam_ids_e_nada_executa_antes() -> None:
    orcamento = CostBudget(
        max_task_attempts=3, max_planning_attempts=5, max_additional_planning_rounds=2, max_tasks_per_session=3,
        max_llm_calls_per_session=60, session_token_budget=100_000, final_answer_token_reserve=1_000,
        session_timeout_seconds=600,
    )
    provider = FakePromptTemplateProvider()
    cenario = _cenario([
        criterios(),
        _plano(_tarefa("T1", "A"), _tarefa("T2", "B"), _tarefa("T3", "C")),
        plano_reprovado(problema_do_plano(task_id=None, problem="Tarefas redundantes.", adjustment="Unificar.")),
        _plano(_tarefa("T1", "Unica", depends_on=None), _tarefa("T2", "Final", depends_on=["T1"])),
        plano_aprovado(), anotacoes_do_enunciado(), *_execucao("T1", "T2"),
    ], budget=orcamento, template_provider=provider)

    await cenario.run()

    assert [v["max_tasks"] for v in provider.variables_of(Phase.A2_TASK_DECOMPOSITION)] == ["3", "3"]
    assert cenario.cost_guard.remaining_task_slots() == 1
    assert cenario.task_queue.total_created() == 2
    assert cenario.results_ledger.current_task_ids() == ("T1", "T2")
    fases = _fases_invocadas(cenario)
    assert fases.index(Phase.B1_TASK_RESOLUTION) > max(
        i for i, fase in enumerate(fases) if fase is Phase.A3_DECOMPOSITION_VALIDATION
    )
    assert cenario.session.status is SessionStatusEnum.COMPLETED


async def test_o_espaco_de_tarefas_continua_valendo_para_cada_candidato() -> None:
    cost_guard = FakeCostGuard(task_slots=1)
    cenario = _cenario([
        criterios(),
        _plano(_tarefa("T1", "A"), _tarefa("T2", "B")),  # acima do teto: recusa estrutural, não candidato novo
        _plano(_tarefa("T1", "A")), plano_aprovado(), anotacoes_do_enunciado(), *_execucao("T1"),
    ], cost_guard=cost_guard)

    await cenario.run()

    assert cost_guard.planning_attempts == 1
    assert cost_guard.tasks_created == [1]


# ── 5. Cinco tentativas ─────────────────────────────────────────────────────

async def test_quinto_candidato_aprovado_conclui() -> None:
    roteiro = [criterios()]
    for _ in range(4):
        roteiro += [_plano(_C1_ANTECIPADO), plano_reprovado(_REPROVACAO_T1)]
    roteiro += [_plano(_C1_ABERTO), plano_aprovado(), anotacoes_do_enunciado(), *_execucao("T1")]
    cost_guard = FakeCostGuard()
    cenario = _cenario(roteiro, cost_guard=cost_guard)

    eventos = await cenario.run()

    assert cost_guard.planning_attempts == 5
    assert [e.subtype for e in eventos].count(Sub.PLAN_REJECTED) == 4
    assert cenario.session.status is SessionStatusEnum.COMPLETED


async def test_quinto_candidato_reprovado_encerra_sem_sexta_tentativa_a4_tarefas_ou_sintese() -> None:
    roteiro = [criterios()]
    for _ in range(5):
        roteiro += [_plano(_C1_ANTECIPADO), plano_reprovado(_REPROVACAO_T1)]
    cenario = _cenario(roteiro, cost_guard=FakeCostGuard())

    with pytest.raises(Exception) as erro:
        await cenario.run()

    assert "planning_attempts" in str(erro.value)
    fases = _fases_invocadas(cenario)
    assert fases.count(Phase.A2_TASK_DECOMPOSITION) == 5 and fases.count(Phase.A3_DECOMPOSITION_VALIDATION) == 5
    assert Phase.A4_PLANNING_LEARNINGS not in fases and Phase.B1_TASK_RESOLUTION not in fases
    assert cenario.llm.call_count == 11
    falha = cenario.session.failure
    assert falha.reason is SessionFailureReasonEnum.RESOURCE_LIMIT
    assert falha.limit is BudgetLimitEnum.PLANNING_ATTEMPTS
    assert falha.phase is Phase.A3_DECOMPOSITION_VALIDATION
    assert "5" in falha.description and "Tarefas descartadas" not in falha.description
    assert cenario.session.status is SessionStatusEnum.FAILED and cenario.session.final_answer is None
    assert cenario.task_queue.is_empty() and cenario.task_queue.total_created() == 0
    assert not [m for m in cenario.session.messages if m.subtype is Sub.TASKS]


async def test_limite_configurado_menor_encerra_no_proprio_limite() -> None:
    cenario = _cenario([
        criterios(), _plano(_C1_ANTECIPADO), plano_reprovado(_REPROVACAO_T1),
        _plano(_C1_ANTECIPADO), plano_reprovado(_REPROVACAO_T1),
    ], cost_guard=FakeCostGuard(max_planning_attempts=2))

    eventos = [e async for e in _coleta(cenario)]

    assert eventos[-1].type is ThinkingEventTypeEnum.ERROR
    assert eventos[-1].phase is Phase.A3_DECOMPOSITION_VALIDATION
    assert cenario.session.failure.limit is BudgetLimitEnum.PLANNING_ATTEMPTS
    assert "2" in cenario.session.failure.description


async def _coleta(cenario: RalphScenario):
    try:
        async for evento in cenario.stream():
            yield evento
    except Exception:
        return


# ── 6 e 8. Recuperação estrutural, contadores e temperaturas ────────────────

async def test_recuperacao_estrutural_nao_e_reprovacao_semantica_e_temperaturas_seguem_a_politica() -> None:
    cost_guard = FakeCostGuard()
    cenario = _cenario([
        criterios(),
        "isto nao e json",  # A.2: sintaxe → correção na mesma janela
        _plano(_C1_ANTECIPADO),
        json.dumps({"approved": "false", "issues": [_REPROVACAO_T1]}),  # A.3: contrato → correção
        plano_reprovado(_REPROVACAO_T1),
        _plano(_C1_ABERTO), plano_aprovado(),
        anotacoes_do_enunciado(), *_execucao("T1"),
    ], cost_guard=cost_guard, template_provider=_real_provider())

    await cenario.run()

    assert cost_guard.planning_attempts == 2
    assert cost_guard.attempts_by_task == {"T1": 1}
    temperaturas = [(i.phase, i.temperature) for i in cenario.session.invocations[:8]]
    assert temperaturas == [
        (Phase.A1_GENERAL_CRITERIA, _TEMPERATURA),
        (Phase.A2_TASK_DECOMPOSITION, _TEMPERATURA), (Phase.A2_TASK_DECOMPOSITION, 1.0),
        (Phase.A3_DECOMPOSITION_VALIDATION, _TEMPERATURA), (Phase.A3_DECOMPOSITION_VALIDATION, 1.0),
        (Phase.A2_TASK_DECOMPOSITION, 1.0),
        (Phase.A3_DECOMPOSITION_VALIDATION, _TEMPERATURA),
        (Phase.A4_PLANNING_LEARNINGS, _TEMPERATURA),
    ]
    # A correção de contrato de A.3 preserva a janela da própria execução: template uma vez, saída recusada
    # integral e a correção em inglês, sem repetir o template.
    correcao_a3 = cenario.llm.texts_of(4)
    assert len(correcao_a3) == 3
    assert correcao_a3[0].startswith("# A.3") and sum(t.startswith("# A.3") for t in correcao_a3) == 1
    assert correcao_a3[1] == json.dumps({"approved": "false", "issues": [_REPROVACAO_T1]})
    assert correcao_a3[2].startswith("## Phase contract correction") and "'approved'" in correcao_a3[2]
    invocacoes = cenario.session.invocations
    assert all(i.outcome is InvocationOutcomeEnum.SUCCESS for i in invocacoes)
    assert cenario.session.totals.total_llm_calls == len(invocacoes) == cenario.llm.call_count
    assert invocacoes[4].recovers_invocation_id == invocacoes[3].id


async def test_contrato_invalido_de_a3_esgotado_e_falha_tecnica_sem_promover_o_plano() -> None:
    invalido = json.dumps({"approved": True, "issues": [_REPROVACAO_T1]})
    cenario = _cenario([criterios(), _plano(_C1_ABERTO), invalido, invalido, invalido], cost_guard=FakeCostGuard())

    with pytest.raises(Exception):
        await cenario.run()

    falha = cenario.session.failure
    assert falha.reason is SessionFailureReasonEnum.TECHNICAL_ERROR
    assert falha.phase is Phase.A3_DECOMPOSITION_VALIDATION
    assert cenario.task_queue.total_created() == 0
    assert Phase.A4_PLANNING_LEARNINGS not in _fases_invocadas(cenario)


# ── 9. A.4 ──────────────────────────────────────────────────────────────────

async def test_a4_extrai_uma_vez_depois_da_aprovacao_e_as_notas_chegam_a_b() -> None:
    provider = FakePromptTemplateProvider()
    cenario = _cenario([
        criterios(), _plano(_C1_ANTECIPADO), plano_reprovado(_REPROVACAO_T1),
        _plano(_C1_ABERTO), plano_aprovado(),
        anotacoes_do_enunciado("NOTA-DO-ENUNCIADO: 6 V."), *_execucao("T1"),
    ], template_provider=provider)

    await cenario.run()

    assert len(provider.variables_of(Phase.A4_PLANNING_LEARNINGS)) == 1
    assert "NOTA-DO-ENUNCIADO: 6 V." in provider.variables_of(Phase.B1_TASK_RESOLUTION)[0]["learnings"]
    assert "NOTA-DO-ENUNCIADO: 6 V." in provider.variables_of(Phase.C3_FINAL_ANSWER)[0]["learnings"]
    a4 = [m for m in cenario.session.messages if m.phase is Phase.A4_PLANNING_LEARNINGS]
    assert len(a4) == 1 and a4[0].subtype is Sub.LEARN
    assert a4[0].context_id not in {m.context_id for m in cenario.session.messages if m is not a4[0]}


# ── 10. Orçamento, provedor e cancelamento ──────────────────────────────────

def _orcamento(chamadas: int) -> CostBudget:
    return CostBudget(
        max_task_attempts=3, max_planning_attempts=5, max_additional_planning_rounds=2, max_tasks_per_session=12,
        max_llm_calls_per_session=chamadas, session_token_budget=100_000, final_answer_token_reserve=1_000,
        session_timeout_seconds=600,
    )


@pytest.mark.parametrize("chamadas, fase_negada", [
    (2, Phase.A3_DECOMPOSITION_VALIDATION),  # A1, A2 — a avaliação é negada
    (3, Phase.A2_TASK_DECOMPOSITION),  # A1, A2, A3 reprova — a revisão é negada
    (5, Phase.A4_PLANNING_LEARNINGS),  # A1, A2, A3, A2, A3 aprova — confirmado, A.4 negada
])
async def test_limite_de_chamadas_interrompe_sem_promover_plano_recusado(chamadas: int, fase_negada: Phase) -> None:
    cenario = _cenario([
        criterios(), _plano(_C1_ANTECIPADO), plano_reprovado(_REPROVACAO_T1), _plano(_C1_ABERTO), plano_aprovado(),
    ], budget=_orcamento(chamadas))

    with pytest.raises(Exception):
        await cenario.run()

    falha = cenario.session.failure
    assert falha.limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION and falha.phase is fase_negada
    assert cenario.llm.call_count == chamadas == cenario.session.totals.total_llm_calls
    assert Phase.B1_TASK_RESOLUTION not in _fases_invocadas(cenario)
    confirmadas = [m for m in cenario.session.messages if m.subtype is Sub.TASKS]
    if fase_negada is Phase.A4_PLANNING_LEARNINGS:
        assert len(confirmadas) == 1 and "Comparar as potencias" in confirmadas[0].content
        assert "Tarefas descartadas: `T1`" in falha.description
    else:
        assert confirmadas == [] and cenario.task_queue.total_created() == 0
        assert "Tarefas descartadas" not in falha.description
    assert cenario.session.final_answer is None


async def test_falha_do_provedor_na_avaliacao_e_registrada_sem_confirmar_o_plano() -> None:
    cenario = _cenario([criterios(), _plano(_C1_ABERTO), RuntimeError("provedor fora do ar")])

    with pytest.raises(RuntimeError):
        await cenario.run()

    ultima = cenario.session.invocations[-1]
    assert ultima.phase is Phase.A3_DECOMPOSITION_VALIDATION
    assert ultima.outcome is InvocationOutcomeEnum.PROVIDER_ERROR
    assert cenario.session.failure.phase is Phase.A3_DECOMPOSITION_VALIDATION
    assert cenario.task_queue.total_created() == 0
    assert [m.subtype for m in cenario.session.messages if m.phase is Phase.A2_TASK_DECOMPOSITION] == [
        Sub.PLAN_CANDIDATE
    ]


async def test_a3_nao_e_usada_nos_lotes_de_c2() -> None:
    from tests.doubles.ralph_scripts import global_reprovado, tarefas

    cenario = _cenario([
        criterios(), _plano(_C1_ABERTO), plano_aprovado(), anotacoes_do_enunciado(),
        *tarefa_aprovada("T1", "r1", "f1"), global_reprovado("AC2"),
        tarefas("T2"), resolucao("r2"), aprovado("T2"), anotacoes_do_enunciado(),
        global_aprovado(), resposta_final(),
    ])

    await cenario.run()

    assert _fases_invocadas(cenario).count(Phase.A3_DECOMPOSITION_VALIDATION) == 1
    assert cenario.session.status is SessionStatusEnum.COMPLETED
