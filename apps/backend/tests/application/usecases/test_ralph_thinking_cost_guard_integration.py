"""O fluxo completo sob o `CostGuardAdapter` real.

Aqui nenhum veredito é programado: os limites vêm de um `CostBudget` e o guardião decide sozinho.
Os testes provam que cada limite interrompe o fluxo na fase certa, com a causa certa, sem nenhuma
chamada ao modelo depois do bloqueio e sem promover material não aprovado.
"""
import json
import logging

import httpx
import pytest

from src.domain.entities.resilience.cost_budget import CostBudget
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.budget_exceeded_error import BudgetExceededError
from src.domain.errors.execution_interrupted_error import ExecutionInterruptedError
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.infra.adapters.llm_completions_adapter import LLMCompletionsAdapter
from src.infra.services.openrouter_service import OpenRouterService
from tests.doubles.fake_model_catalog import FakeModelCatalog
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import (
    anotacoes_do_enunciado,
    criterios,
    global_aprovado,
    global_reprovado,
    resolucao,
    resposta_final,
    roteiro_feliz,
    tarefa_aprovada,
    tarefas,
)

_FASE = ThinkingPhaseEnum
_TIPO = ThinkingEventTypeEnum
_SUB = ThinkingEventSubtypeEnum
_TOKENS_POR_CHAMADA = 15


def _orcamento(**overrides: int) -> CostBudget:
    limites = {
        "max_task_attempts": 3,
        "max_additional_planning_rounds": 2,
        "max_tasks_per_session": 12,
        "max_llm_calls_per_session": 60,
        "session_token_budget": 10_000,
        "final_answer_token_reserve": 1_000,
        "session_timeout_seconds": 600,
    }
    return CostBudget(**(limites | overrides))


def _roteiro_minimo() -> list[str]:
    """Oito respostas válidas: A.1, A.2, A.3, B.1, B.2, B.4, C.1 e C.3 com uma única tarefa."""
    return [
        criterios(),
        tarefas("T1"),
        anotacoes_do_enunciado(),
        *tarefa_aprovada("T1", "2 e primo", "fato"),
        global_aprovado(),
        resposta_final(),
    ]


async def _executar(cenario: RalphScenario, excecao: type[Exception]) -> list:
    eventos = []
    with pytest.raises(excecao):
        async for evento in cenario.stream():
            eventos.append(evento)
    return eventos


# ── Reserva e orçamento de trabalho ──────────────────────────────────────────


async def test_orcamento_de_trabalho_esgotado_antes_da_proxima_tarefa_encerra_sem_nova_inferencia() -> None:
    """Orçamento 115, reserva 25 e 90 tokens consumidos: a tarefa seguinte não começa."""
    cenario = RalphScenario(
        responses=[
            criterios(),
            tarefas("T1", "T2"),
            anotacoes_do_enunciado(),
            *tarefa_aprovada("T1", "2 e primo", "fato"),
        ],
        budget=_orcamento(session_token_budget=115, final_answer_token_reserve=25),
        max_tokens=5,
    )

    eventos = await _executar(cenario, ExecutionInterruptedError)

    assert cenario.llm.call_count == 6
    assert cenario.session.totals.total_tokens == 6 * _TOKENS_POR_CHAMADA == 90
    assert eventos[-1].type is _TIPO.ERROR
    assert [e.task for e in eventos if e.subtype is _SUB.RESET] == ["T1"]
    falha = cenario.session.failure
    assert falha.reason is SessionFailureReasonEnum.RESOURCE_LIMIT
    assert falha.limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET
    assert falha.phase is _FASE.B1_TASK_RESOLUTION
    assert "Orçamento de trabalho esgotado" in falha.description
    assert "`T2`" in falha.description
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.final_answer is None


async def test_a_reserva_continua_intacta_mas_nao_forca_a_sintese() -> None:
    cenario = RalphScenario(
        responses=[
            criterios(),
            tarefas("T1", "T2"),
            anotacoes_do_enunciado(),
            *tarefa_aprovada("T1", "2 e primo", "fato"),
        ],
        budget=_orcamento(session_token_budget=115, final_answer_token_reserve=25),
        max_tokens=5,
    )

    eventos = await _executar(cenario, ExecutionInterruptedError)

    assert cenario.cost_guard.authorize(phase=_FASE.C3_FINAL_ANSWER, reserved_output_tokens=5).authorized is True
    assert not [e for e in eventos if e.phase in (_FASE.C1_GLOBAL_VERIFICATION, _FASE.C3_FINAL_ANSWER)]


async def test_a_saida_maxima_pedida_impede_iniciar_uma_chamada_que_poderia_estourar_o_teto() -> None:
    cenario = RalphScenario(
        responses=[criterios()],
        budget=_orcamento(session_token_budget=100, final_answer_token_reserve=25),
        max_tokens=80,
    )

    await _executar(cenario, BudgetExceededError)

    assert cenario.llm.call_count == 0
    assert cenario.session.invocations == []
    assert cenario.session.totals.total_llm_calls == 0
    assert cenario.session.failure.phase is _FASE.A1_GENERAL_CRITERIA
    assert cenario.session.failure.limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET


# ── Limite de chamadas em cada fase ──────────────────────────────────────────


@pytest.mark.parametrize(
    ("teto", "fase", "tarefa"),
    [
        (1, _FASE.A2_TASK_DECOMPOSITION, None),
        (2, _FASE.A3_PLANNING_LEARNINGS, None),
        (3, _FASE.B1_TASK_RESOLUTION, None),
        (4, _FASE.B2_TASK_VERIFICATION, "T1"),
        (5, _FASE.B4_LEARNINGS_EXTRACTION, "T1"),
        (6, _FASE.C1_GLOBAL_VERIFICATION, None),
        (7, _FASE.C3_FINAL_ANSWER, None),
    ],
)
async def test_teto_de_chamadas_interrompe_na_fase_que_pediria_a_chamada_excedente(
    teto: int, fase: ThinkingPhaseEnum, tarefa: str | None
) -> None:
    cenario = RalphScenario(
        responses=_roteiro_minimo(), budget=_orcamento(max_llm_calls_per_session=teto), max_tokens=5
    )

    eventos = await _executar(cenario, ExecutionInterruptedError)

    assert cenario.llm.call_count == teto
    assert len(cenario.session.invocations) == teto
    assert eventos[-1].type is _TIPO.ERROR
    assert eventos[-1].phase is fase
    falha = cenario.session.failure
    assert falha.limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION
    assert falha.phase is fase
    assert falha.task_id == tarefa
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.final_answer is None
    assert not [e for e in eventos if e.type is _TIPO.RESULT]


async def test_interrupcao_em_c3_depois_da_aprovacao_global_nao_gera_sucesso() -> None:
    cenario = RalphScenario(
        responses=roteiro_feliz(), budget=_orcamento(max_llm_calls_per_session=13), max_tokens=5
    )

    eventos = await _executar(cenario, BudgetExceededError)

    assert [e.phase.value for e in eventos if e.phase is _FASE.C1_GLOBAL_VERIFICATION] == ["C1"]
    assert eventos[-1].phase is _FASE.C3_FINAL_ANSWER
    assert cenario.session.final_answer is None


# ── Tempo ────────────────────────────────────────────────────────────────────


async def test_tempo_esgotado_interrompe_sem_nenhuma_chamada_depois_do_bloqueio() -> None:
    cenario = RalphScenario(
        responses=_roteiro_minimo(),
        budget=_orcamento(session_timeout_seconds=1),
        clock_step_ms=400,
        max_tokens=5,
    )

    eventos = await _executar(cenario, BudgetExceededError)

    assert cenario.llm.call_count == 1
    assert eventos[-1].phase is _FASE.A2_TASK_DECOMPOSITION
    assert cenario.session.failure.limit is BudgetLimitEnum.SESSION_TIMEOUT
    assert len([e for e in eventos if e.type is _TIPO.ERROR]) == 1


# ── Planejamento adicional ───────────────────────────────────────────────────


async def test_rodadas_de_planejamento_esgotadas_encerram_sem_sintese_e_registram_as_pendencias() -> None:
    cenario = RalphScenario(
        responses=[
            criterios(),
            tarefas("T1"),
            anotacoes_do_enunciado(),
            *tarefa_aprovada("T1", "2 e primo", "fato"),
            global_reprovado("AC2"),
            tarefas("T4"),
            *tarefa_aprovada("T4", "4 e par", "fato"),
            global_reprovado("AC2"),
        ],
        budget=_orcamento(max_additional_planning_rounds=1),
        max_tokens=5,
    )

    eventos = await _executar(cenario, ExecutionInterruptedError)

    assert [e.subtype.value for e in eventos if e.subtype is _SUB.REPLAN] == ["replan"]
    assert eventos[-1].phase is _FASE.C2_ADDITIONAL_PLANNING
    falha = cenario.session.failure
    assert falha.limit is BudgetLimitEnum.ADDITIONAL_PLANNING_ROUNDS
    assert falha.pending_criteria_ids == ("AC2",)
    assert cenario.session.final_answer is None
    assert not cenario.template_provider.variables_of(_FASE.C3_FINAL_ANSWER)


async def test_sem_slots_depois_do_plano_inicial_c2_nem_e_chamada_e_a_causa_e_o_limite_de_tarefas() -> None:
    cenario = RalphScenario(
        responses=[
            criterios(),
            tarefas("T1", "T2"),
            tarefas("T1"),
            anotacoes_do_enunciado(),
            *tarefa_aprovada("T1", "2 e primo", "fato"),
            global_reprovado("AC2"),
        ],
        budget=_orcamento(max_tasks_per_session=1),
        max_tokens=5,
    )

    await _executar(cenario, ExecutionInterruptedError)

    assert not cenario.template_provider.variables_of(_FASE.C2_ADDITIONAL_PLANNING)
    assert cenario.session.failure.limit is BudgetLimitEnum.TASKS_PER_SESSION
    assert cenario.llm.call_count == 8  # A.1, A.2 recusada, A.2 corrigida, A.3, B.1, B.2, B.4, C.1
    assert cenario.task_queue.total_created() == 1


async def test_plano_inicial_acima_do_teto_conta_a_chamada_de_correcao_do_planejador() -> None:
    cenario = RalphScenario(
        responses=[
            criterios(),
            tarefas("T1", "T2"),
            tarefas("T1"),
            anotacoes_do_enunciado(),
            *tarefa_aprovada("T1", "x", "f"),
            global_aprovado(),
            resposta_final(),
        ],
        budget=_orcamento(max_tasks_per_session=1),
        max_tokens=5,
    )

    await cenario.run()

    assert cenario.session.totals.total_llm_calls == 9
    assert cenario.cost_guard.remaining_task_slots() == 0
    assert cenario.session.status is SessionStatusEnum.COMPLETED


async def test_plano_que_nunca_cabe_no_teto_interrompe_pelo_limite_de_tarefas_sem_tocar_a_fila() -> None:
    cenario = RalphScenario(
        responses=[criterios(), tarefas("T1", "T2"), tarefas("T1", "T2"), tarefas("T1", "T2")],
        budget=_orcamento(max_tasks_per_session=1),
        settings=FakeSettings(ralph_json_parse_max_retries=2),
        max_tokens=5,
    )

    await _executar(cenario, PhaseParsingError)

    assert cenario.session.failure.limit is BudgetLimitEnum.TASKS_PER_SESSION
    assert cenario.task_queue.total_created() == 0
    assert cenario.cost_guard.remaining_task_slots() == 1


# ── Tentativas de tarefa ─────────────────────────────────────────────────────


async def test_tentativas_esgotadas_com_o_guardiao_real_nao_armazenam_nem_sintetizam() -> None:
    reprovado = json.dumps(
        {
            "decision": "reproved",
            "criteria_evaluation": [{"criterion_id": "T1-AC1", "met": False, "justification": "nao atende"}],
            "unmet_criteria_ids": ["T1-AC1"],
        }
    )
    cenario = RalphScenario(
        responses=[
            criterios(),
            tarefas("T1"),
            anotacoes_do_enunciado(),
            resolucao("ruim"),
            reprovado,
            resolucao("RESULTADO_REPROVADO"),
            reprovado,
        ],
        budget=_orcamento(max_task_attempts=2),
        max_tokens=5,
    )

    eventos = await _executar(cenario, ExecutionInterruptedError)

    assert cenario.session.failure.limit is BudgetLimitEnum.TASK_ATTEMPTS
    assert not [e for e in eventos if e.subtype is _SUB.STORE]
    assert cenario.llm.call_count == 7
    assert not cenario.template_provider.variables_of(_FASE.C1_GLOBAL_VERIFICATION)


# ── Contabilidade: sessão e guardião concordam ───────────────────────────────


async def test_sessao_e_guardiao_concordam_sobre_chamadas_e_tokens_consumidos() -> None:
    cenario = RalphScenario(
        responses=["isto nao e json", *roteiro_feliz()],
        budget=_orcamento(),
        settings=FakeSettings(ralph_json_parse_max_retries=2),
        max_tokens=5,
    )

    await cenario.run()

    consumidos_pelo_guardiao = (
        cenario.cost_guard.budget.session_token_budget
        - cenario.cost_guard.budget.final_answer_token_reserve
        - cenario.cost_guard.remaining_tokens()
    )
    assert cenario.session.totals.total_tokens == consumidos_pelo_guardiao == 15 * _TOKENS_POR_CHAMADA
    assert cenario.session.totals.total_llm_calls == 15


# ── HTTP simulado: completions vazias ────────────────────────────────────────


def _corpo(texto: str | None, prompt_tokens: int = 10, completion_tokens: int = 5, finish_reason: str = "stop") -> dict:
    return {
        "id": f"gen-{texto or 'vazio'}"[:12],
        "choices": [{"message": {"content": texto}, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }


def _cenario_http(
    respostas: list[dict], enviadas: list[httpx.Request], budget: CostBudget, api_key: str = "chave-de-teste"
) -> RalphScenario:
    fila = list(respostas)

    def handler(request: httpx.Request) -> httpx.Response:
        enviadas.append(request)
        return httpx.Response(status_code=200, json=fila.pop(0))

    service = OpenRouterService(
        logger=logging.getLogger("teste.http"),
        settings=FakeSettings(openrouter_api_key=api_key),
        transport=httpx.MockTransport(handler),
    )
    adapter = LLMCompletionsAdapter(
        llm_services=[service],
        model_catalog=FakeModelCatalog(),
        logger=logging.getLogger("teste.adapter"),
        settings=FakeSettings(),
    )
    return RalphScenario(responses=[], llm=adapter, budget=budget, max_tokens=5)


def _respostas_http_validas() -> list[dict]:
    return [_corpo(texto) for texto in _roteiro_minimo()]


async def test_completion_vazia_via_http_registra_nove_chamadas_e_o_consumo_que_o_provedor_informou() -> None:
    vazia = _corpo(None, prompt_tokens=100, completion_tokens=40, finish_reason="length")
    enviadas: list[httpx.Request] = []
    cenario = _cenario_http([vazia, *_respostas_http_validas()], enviadas, _orcamento())

    eventos = await cenario.run()

    assert len(enviadas) == 9
    assert eventos[-1].type is _TIPO.RESULT
    assert cenario.session.status is SessionStatusEnum.COMPLETED
    assert cenario.session.totals.total_llm_calls == 9
    assert cenario.session.totals.total_tokens == 140 + 8 * _TOKENS_POR_CHAMADA == 260
    assert cenario.session.invocations[0].outcome is InvocationOutcomeEnum.EMPTY_COMPLETION
    assert cenario.session.invocations[0].finish_reason == "length"
    consumidos_pelo_guardiao = (
        cenario.cost_guard.budget.session_token_budget
        - cenario.cost_guard.budget.final_answer_token_reserve
        - cenario.cost_guard.remaining_tokens()
    )
    assert consumidos_pelo_guardiao == 260


async def test_completion_vazia_via_http_conta_para_o_teto_e_a_nona_chamada_nao_e_enviada() -> None:
    vazia = _corpo(None, prompt_tokens=100, completion_tokens=40, finish_reason="length")
    enviadas: list[httpx.Request] = []
    cenario = _cenario_http([vazia, *_respostas_http_validas()], enviadas, _orcamento(max_llm_calls_per_session=8))

    eventos = await _executar(cenario, BudgetExceededError)

    assert len(enviadas) == 8
    assert eventos[-1].type is _TIPO.ERROR
    assert eventos[-1].phase is _FASE.C3_FINAL_ANSWER
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.final_answer is None
    assert cenario.session.totals.total_llm_calls == 8
    assert cenario.session.totals.total_tokens == 140 + 7 * _TOKENS_POR_CHAMADA == 245


async def test_credencial_ausente_nao_envia_requisicao_nem_conta_chamada() -> None:
    enviadas: list[httpx.Request] = []
    cenario = _cenario_http(_respostas_http_validas(), enviadas, _orcamento(), api_key="")

    await _executar(cenario, ValueError)

    assert enviadas == []
    assert cenario.session.invocations == []
    assert cenario.session.totals.total_llm_calls == 0
    assert cenario.session.failure.reason is SessionFailureReasonEnum.TECHNICAL_ERROR
    assert cenario.session.failure.phase is _FASE.A1_GENERAL_CRITERIA
    assert "OPENROUTER_API_KEY" in cenario.session.failure.description
    assert cenario.cost_guard.remaining_tokens() == 10_000 - 1_000


async def test_uso_parcial_via_http_preserva_a_saida_como_desconhecida() -> None:
    enviadas: list[httpx.Request] = []
    corpos = [{**corpo, "usage": {"prompt_tokens": 10}} for corpo in _respostas_http_validas()]
    cenario = _cenario_http(corpos, enviadas, _orcamento())

    await cenario.run()

    assert all(
        (invocacao.tokens_input, invocacao.tokens_output) == (10, None) for invocacao in cenario.session.invocations
    )
    assert cenario.session.totals.tokens_input == 80
    assert cenario.session.totals.tokens_output == 0
